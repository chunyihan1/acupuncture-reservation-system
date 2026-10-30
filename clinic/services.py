"""业务服务层：预约号源校验、状态流转、方案与记录归档、统计聚合。"""

from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import (
    Appointment,
    OperationLog,
    PlanAcupoint,
    Role,
    Schedule,
    TreatmentPlan,
    TreatmentRecord,
    User,
)


class BookingError(Exception):
    """预约业务异常，携带面向用户的中文提示。"""


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_action(request, action, target="", detail=""):
    OperationLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        target=target[:200],
        detail=detail,
        ip=client_ip(request),
    )


def slot_datetime(schedule):
    naive = datetime.combine(schedule.date, schedule.start_time)
    return timezone.make_aware(naive, timezone.get_current_timezone())


@transaction.atomic
def create_appointment(patient, schedule_id, chief_complaint=""):
    """创建预约：时段唯一占号 + 同一患者同时段不可重复预约。"""
    schedule = (
        Schedule.objects.select_for_update()
        .select_related("doctor")
        .filter(pk=schedule_id, is_active=True)
        .first()
    )
    if not schedule:
        raise BookingError("该排班时段不存在或已停用")

    if schedule.date < timezone.localdate():
        raise BookingError("该排班日期已过期，请选择其他时段")

    if schedule.remaining <= 0:
        raise BookingError("该时段号源已约满，请选择其他时段")

    exists = Appointment.objects.filter(
        patient=patient,
        schedule=schedule,
        status__in=Appointment.ACTIVE_STATUSES,
    ).exists()
    if exists:
        raise BookingError("您已预约该时段，请勿重复提交")

    return Appointment.objects.create(
        patient=patient,
        doctor=schedule.doctor,
        schedule=schedule,
        appoint_time=slot_datetime(schedule),
        status=Appointment.Status.PENDING,
        chief_complaint=chief_complaint,
    )


def transition_appointment(request, appointment, new_status, reason=""):
    if not appointment.can_transition_to(new_status):
        raise ValidationError(
            f"不允许从“{appointment.get_status_display()}”变更到目标状态"
        )
    old_label = appointment.get_status_display()
    appointment.transition_to(new_status, reason=reason)
    log_action(
        request,
        "预约状态变更",
        target=appointment.appointment_no,
        detail=f"{old_label} -> {appointment.get_status_display()}",
    )
    return appointment


def patient_cancel_appointment(request, appointment, reason=""):
    if not appointment.can_cancel:
        raise ValidationError("当前预约状态不允许取消")
    appointment.transition_to(Appointment.Status.CANCELLED, reason=reason)
    log_action(
        request, "取消预约", target=appointment.appointment_no, detail=reason
    )
    return appointment


@transaction.atomic
def save_treatment_plan(appointment, doctor, data, main_ids, adjunct_ids):
    """创建/更新治疗方案并同步主穴、配穴关联。"""
    plan = TreatmentPlan.objects.filter(appointment=appointment).first()
    if plan is None:
        plan = TreatmentPlan(appointment=appointment)

    plan.patient = appointment.patient
    plan.doctor = doctor
    plan.syndrome = data.get("syndrome", "").strip()
    plan.technique = data.get("technique", "").strip()
    plan.course_cycle = int(data.get("course_cycle") or 14)
    plan.frequency_per_week = int(data.get("frequency_per_week") or 3)
    plan.notes = data.get("notes", "").strip()
    plan.save()

    PlanAcupoint.objects.filter(plan=plan).delete()
    seen = set()
    rows = []
    for idx, acupoint_id in enumerate(main_ids):
        if acupoint_id in seen:
            continue
        seen.add(acupoint_id)
        rows.append(
            PlanAcupoint(
                plan=plan,
                acupoint_id=acupoint_id,
                type=PlanAcupoint.Type.MAIN,
                order=idx,
            )
        )
    for idx, acupoint_id in enumerate(adjunct_ids):
        if acupoint_id in seen:
            continue
        seen.add(acupoint_id)
        rows.append(
            PlanAcupoint(
                plan=plan,
                acupoint_id=acupoint_id,
                type=PlanAcupoint.Type.ADJUNCT,
                order=idx,
            )
        )
    PlanAcupoint.objects.bulk_create(rows)
    return plan


def complete_appointment_by_record(appointment):
    """治疗记录确认后，将主流程推进到“已完成”。"""
    if appointment.status == Appointment.Status.SCHEDULED:
        appointment.transition_to(Appointment.Status.TREATING)
    if appointment.status == Appointment.Status.TREATING:
        appointment.transition_to(Appointment.Status.COMPLETED)


def dashboard_metrics():
    today = timezone.localdate()
    appointments = Appointment.objects.all()
    records = TreatmentRecord.objects.all()
    total_patients = User.objects.filter(role=Role.PATIENT).count()
    total_doctors = User.objects.filter(role=Role.DOCTOR).count()
    metrics = {
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "total_appointments": appointments.count(),
        "today_appointments": appointments.filter(appoint_time__date=today).count(),
        "pending_appointments": appointments.filter(
            status=Appointment.Status.PENDING
        ).count(),
        "completed_appointments": appointments.filter(
            status__in=[Appointment.Status.COMPLETED, Appointment.Status.ARCHIVED]
        ).count(),
        "total_treatments": records.filter(
            status=TreatmentRecord.Status.CONFIRMED
        ).count(),
    }
    return metrics


def trend_series(days=7):
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    qs = (
        Appointment.objects.filter(appoint_time__date__gte=start)
        .values("appoint_time__date")
        .annotate(total=Count("id"))
    )
    data = {row["appoint_time__date"]: row["total"] for row in qs}
    labels, values = [], []
    for offset in range(days):
        day = start + timedelta(days=offset)
        labels.append(day.strftime("%m-%d"))
        values.append(data.get(day, 0))
    return labels, values


def status_distribution():
    qs = Appointment.objects.values("status").annotate(total=Count("id"))
    label_map = dict(Appointment.Status.choices)
    return [
        {"name": label_map.get(row["status"], row["status"]), "value": row["total"]}
        for row in qs
    ]


def doctor_workload(limit=6):
    qs = (
        Appointment.objects.filter(status__in=Appointment.ACTIVE_STATUSES)
        .values("doctor__name", "doctor__username")
        .annotate(total=Count("id"))
        .order_by("-total")[:limit]
    )
    return [
        {
            "name": row["doctor__name"] or row["doctor__username"],
            "value": row["total"],
        }
        for row in qs
    ]


def monthly_treatments(months=6):
    today = timezone.localdate().replace(day=1)
    labels, values = [], []
    for offset in range(months - 1, -1, -1):
        year = today.year
        month = today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        start = today.replace(year=year, month=month, day=1)
        if month == 12:
            end = start.replace(year=year + 1, month=1, day=1)
        else:
            end = start.replace(month=month + 1, day=1)
        count = TreatmentRecord.objects.filter(
            status=TreatmentRecord.Status.CONFIRMED,
            treat_time__date__gte=start,
            treat_time__date__lt=end,
        ).count()
        labels.append(f"{year}-{month:02d}")
        values.append(count)
    return labels, values


def doctor_daily_stats(doctor):
    today = timezone.localdate()
    appointments = Appointment.objects.filter(doctor=doctor)
    return {
        "today_total": appointments.filter(appoint_time__date=today).count(),
        "waiting_confirm": appointments.filter(status=Appointment.Status.PENDING).count(),
        "in_treatment": appointments.filter(status=Appointment.Status.TREATING).count(),
        "completed": appointments.filter(
            Q(status=Appointment.Status.COMPLETED) | Q(status=Appointment.Status.ARCHIVED)
        ).count(),
    }


def filter_appointments(params):
    qs = Appointment.objects.select_related("patient", "doctor", "schedule")
    status = params.get("status", "").strip()
    doctor_id = params.get("doctor", "").strip()
    start = params.get("start", "").strip()
    end = params.get("end", "").strip()
    keyword = params.get("q", "").strip()

    if status:
        qs = qs.filter(status=status)
    if doctor_id:
        qs = qs.filter(doctor_id=doctor_id)
    if start:
        qs = qs.filter(appoint_time__date__gte=start)
    if end:
        qs = qs.filter(appoint_time__date__lte=end)
    if keyword:
        qs = qs.filter(
            Q(patient__name__icontains=keyword)
            | Q(patient__username__icontains=keyword)
            | Q(patient__phone__icontains=keyword)
        )
    return qs
