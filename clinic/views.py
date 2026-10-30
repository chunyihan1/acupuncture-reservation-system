import csv
import time
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import services
from .forms import (
    AcupointForm,
    AppointmentFilterForm,
    AppointmentForm,
    DoctorProfileForm,
    LoginForm,
    PlanForm,
    RecordForm,
    RegisterForm,
    ScheduleForm,
    UserCreateForm,
    UserEditForm,
)
from .models import (
    Acupoint,
    Appointment,
    DoctorProfile,
    OperationLog,
    PlanAcupoint,
    Role,
    Schedule,
    TreatmentPlan,
    TreatmentRecord,
    User,
)
from .permissions import can_view_patient_data, doctor_required, manager_required, patient_required, role_required


# ---------------------------------------------------------------- 认证与首页


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST":
        now = time.time()
        locked_until = request.session.get("login_locked_until", 0)
        if locked_until > now:
            wait = int(locked_until - now) + 1
            messages.error(request, f"登录失败次数过多，请 {wait} 秒后再试")
            return render(request, "auth/login.html", {"form": form})

        if form.is_valid():
            username = form.cleaned_data["username"]
            user = authenticate(
                request,
                username=username,
                password=form.cleaned_data["password"],
            )
            if user is None:
                failures = request.session.get("login_failures", 0) + 1
                request.session["login_failures"] = failures
                if failures >= settings.LOGIN_FAILURE_LIMIT:
                    request.session["login_locked_until"] = now + settings.LOGIN_LOCK_SECONDS
                    request.session["login_failures"] = 0
                OperationLog.objects.create(
                    user=None,
                    action="登录失败",
                    target=username,
                    detail=f"连续失败 {failures} 次",
                    ip=services.client_ip(request),
                )
                messages.error(request, "账号或密码错误")
            else:
                login(request, user)
                request.session.pop("login_failures", None)
                request.session.pop("login_locked_until", None)
                services.log_action(
                    request,
                    "登录成功",
                    target=user.username,
                    detail=f"角色：{user.get_role_display()}",
                )
                next_url = request.GET.get("next", "")
                if next_url and url_has_allowed_host_and_scheme(
                    next_url, allowed_hosts={request.get_host()}
                ):
                    return redirect(next_url)
                return redirect("home")

    return render(request, "auth/login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.role = Role.PATIENT
        user.is_active = True
        user.save()
        login(request, user)
        services.log_action(request, "患者注册", target=user.username)
        messages.success(request, "注册成功，欢迎使用针灸预约系统")
        return redirect("home")

    return render(request, "auth/register.html", {"form": form})


@require_POST
@login_required
def logout_view(request):
    services.log_action(request, "退出登录", target=request.user.username)
    logout(request)
    return redirect("login")


@login_required
def home(request):
    if request.user.is_patient:
        return redirect("patient_appointments")
    if request.user.is_doctor:
        return redirect("doctor_dashboard")
    return redirect("dashboard")


# ---------------------------------------------------------------- 患者端


@patient_required
def doctor_list(request):
    doctors = (
        User.objects.filter(role=Role.DOCTOR, is_active=True)
        .select_related("doctor_profile", "doctor_profile__room")
        .order_by("name")
    )
    today = timezone.localdate()
    for doctor in doctors:
        profile = getattr(doctor, "doctor_profile", None)
        doctor.upcoming_schedules = Schedule.objects.filter(
            doctor=doctor, date__gte=today, is_active=True
        ).order_by("date", "start_time")[:3]
        doctor.profile = profile
    return render(request, "patient/doctor_list.html", {"doctors": doctors})


@patient_required
def doctor_schedules(request, doctor_id):
    doctor = get_object_or_404(
        User.objects.select_related("doctor_profile"), pk=doctor_id, role=Role.DOCTOR
    )
    today = timezone.localdate()
    dates = [today + timedelta(days=i) for i in range(14)]
    schedules = Schedule.objects.filter(
        doctor=doctor, date__gte=today, date__lte=dates[-1], is_active=True
    ).order_by("date", "start_time")

    grouped = []
    for day in dates:
        day_schedules = [s for s in schedules if s.date == day]
        if not day_schedules:
            continue
        grouped.append(
            {
                "date": day,
                "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][
                    day.weekday()
                ],
                "schedules": day_schedules,
            }
        )

    return render(
        request,
        "patient/doctor_schedules.html",
        {"doctor": doctor, "grouped": grouped},
    )


@patient_required
def book_appointment(request, schedule_id):
    schedule = get_object_or_404(
        Schedule.objects.select_related("doctor", "doctor__doctor_profile"),
        pk=schedule_id,
    )
    form = AppointmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            appointment = services.create_appointment(
                request.user,
                schedule.pk,
                form.cleaned_data["chief_complaint"],
            )
        except services.BookingError as exc:
            messages.error(request, str(exc))
        else:
            services.log_action(
                request,
                "提交预约",
                target=appointment.appointment_no,
                detail=f"{schedule.doctor.display_name} {schedule.date} {schedule.time_range}",
            )
            messages.success(
                request,
                f"预约提交成功，预约单号 {appointment.appointment_no}，请等待医师排期确认",
            )
            return redirect("patient_appointments")

    return render(
        request,
        "patient/book.html",
        {"schedule": schedule, "doctor": schedule.doctor, "form": form},
    )


@patient_required
def patient_appointments(request):
    appointments = (
        Appointment.objects.filter(patient=request.user)
        .select_related("doctor", "schedule", "doctor__doctor_profile")
        .order_by("-appoint_time")
    )
    status = request.GET.get("status", "")
    if status:
        appointments = appointments.filter(status=status)
    page = paginate(request, appointments)
    return render(
        request,
        "patient/appointments.html",
        {
            "page_obj": page,
            "status": status,
            "status_choices": Appointment.Status.choices,
            "query": query_without_page(request),
        },
    )


def appointment_detail(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "patient", "doctor", "schedule", "doctor__doctor_profile"
        ),
        pk=appointment_id,
    )
    user = request.user
    if user.is_patient and appointment.patient_id != user.pk:
        raise PermissionDenied("无权查看他人的预约信息")
    if user.is_doctor and appointment.doctor_id != user.pk:
        raise PermissionDenied("无权查看其他医师的预约信息")
    if not (user.is_patient or user.is_doctor or user.is_manager):
        raise PermissionDenied

    plan = TreatmentPlan.objects.filter(appointment=appointment).first()
    records = []
    if plan:
        records = TreatmentRecord.objects.filter(plan=plan).order_by("-treat_time")
        if user.is_patient:
            records = records.filter(status=TreatmentRecord.Status.CONFIRMED)
    return render(
        request,
        "appointment_detail.html",
        {
            "appointment": appointment,
            "plan": plan,
            "records": records,
            "main_points": plan.main_points.select_related("acupoint") if plan else [],
            "adjunct_points": plan.adjunct_points.select_related("acupoint") if plan else [],
        },
    )


@require_POST
@patient_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.filter(patient=request.user), pk=appointment_id
    )
    reason = request.POST.get("reason", "").strip()
    try:
        services.patient_cancel_appointment(request, appointment, reason)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    else:
        messages.success(request, "预约已取消，号源已释放")
    return redirect("patient_appointments")


@patient_required
def my_records(request):
    records = (
        TreatmentRecord.objects.filter(
            plan__patient=request.user,
            status=TreatmentRecord.Status.CONFIRMED,
        )
        .select_related("plan", "plan__doctor", "doctor")
        .order_by("-treat_time")
    )
    page = paginate(request, records)
    return render(
        request,
        "patient/records.html",
        {"page_obj": page, "query": query_without_page(request)},
    )


def record_detail(request, record_id):
    record = get_object_or_404(
        TreatmentRecord.objects.select_related(
            "plan", "plan__patient", "plan__doctor", "doctor"
        ),
        pk=record_id,
    )
    if not can_view_patient_data(request.user, record.plan.patient):
        raise PermissionDenied("无权查看该治疗记录")
    return render(
        request,
        "record_detail.html",
        {
            "record": record,
            "plan": record.plan,
            "main_points": record.plan.main_points.select_related("acupoint"),
            "adjunct_points": record.plan.adjunct_points.select_related("acupoint"),
        },
    )


# ---------------------------------------------------------------- 医师端


@doctor_required
def doctor_dashboard(request):
    today = timezone.localdate()
    stats = services.doctor_daily_stats(request.user)
    today_appointments = (
        Appointment.objects.filter(doctor=request.user, appoint_time__date=today)
        .select_related("patient", "schedule")
        .order_by("appoint_time")
    )
    pending = (
        Appointment.objects.filter(
            doctor=request.user, status=Appointment.Status.PENDING
        )
        .select_related("patient")
        .order_by("appoint_time")[:8]
    )
    profile, _ = DoctorProfile.objects.get_or_create(user=request.user)
    schedules = Schedule.objects.filter(
        doctor=request.user, date__gte=today, is_active=True
    ).order_by("date", "start_time")[:6]
    return render(
        request,
        "doctor/dashboard.html",
        {
            "stats": stats,
            "today_appointments": today_appointments,
            "pending": pending,
            "profile": profile,
            "schedules": schedules,
            "today": today,
        },
    )


@doctor_required
def doctor_appointments(request):
    appointments = (
        Appointment.objects.filter(doctor=request.user)
        .select_related("patient", "schedule")
        .order_by("-appoint_time")
    )
    status = request.GET.get("status", "")
    if status:
        appointments = appointments.filter(status=status)
    page = paginate(request, appointments)
    return render(
        request,
        "doctor/appointments.html",
        {
            "page_obj": page,
            "status": status,
            "status_choices": Appointment.Status.choices,
            "query": query_without_page(request),
        },
    )


@doctor_required
def doctor_appointment_detail(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("patient", "schedule"),
        pk=appointment_id,
        doctor=request.user,
    )
    plan = TreatmentPlan.objects.filter(appointment=appointment).first()
    records = (
        TreatmentRecord.objects.filter(plan=plan).select_related("doctor").order_by("-treat_time")
        if plan
        else []
    )
    status_labels = dict(Appointment.Status.choices)
    allowed_transitions = [
        {"value": status.value, "label": status_labels[status]}
        for status in Appointment.Status
        if appointment.can_transition_to(status)
    ]
    return render(
        request,
        "doctor/appointment_detail.html",
        {
            "appointment": appointment,
            "plan": plan,
            "records": records,
            "allowed_transitions": allowed_transitions,
            "main_points": plan.main_points.select_related("acupoint") if plan else [],
            "adjunct_points": plan.adjunct_points.select_related("acupoint") if plan else [],
        },
    )


DOCTOR_TRANSITIONS = {
    Appointment.Status.SCHEDULED,
    Appointment.Status.TREATING,
    Appointment.Status.COMPLETED,
    Appointment.Status.RETURNED,
    Appointment.Status.ARCHIVED,
    Appointment.Status.CANCELLED,
}


@require_POST
@doctor_required
def doctor_transition(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.filter(doctor=request.user), pk=appointment_id
    )
    target = request.POST.get("status", "")
    if target not in DOCTOR_TRANSITIONS:
        messages.error(request, "无效的目标状态")
        return redirect("doctor_appointment_detail", appointment_id=appointment.pk)
    reason = request.POST.get("reason", "").strip()
    try:
        services.transition_appointment(request, appointment, target, reason)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    else:
        messages.success(request, f"预约状态已更新为“{appointment.get_status_display()}”")
    return redirect("doctor_appointment_detail", appointment_id=appointment.pk)


@doctor_required
def plan_edit(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("patient"), pk=appointment_id, doctor=request.user
    )
    if appointment.status not in (
        Appointment.Status.SCHEDULED,
        Appointment.Status.TREATING,
        Appointment.Status.COMPLETED,
    ):
        messages.warning(request, "请先确认排期后再制定治疗方案")
        return redirect("doctor_appointment_detail", appointment_id=appointment.pk)

    plan = TreatmentPlan.objects.filter(appointment=appointment).first()
    initial = None
    if plan:
        initial = {
            "syndrome": plan.syndrome,
            "technique": plan.technique,
            "course_cycle": plan.course_cycle,
            "frequency_per_week": plan.frequency_per_week,
            "notes": plan.notes,
        }
    form = PlanForm(request.POST or None, initial=initial)

    acupoints = Acupoint.objects.all()
    main_ids, adjunct_ids = set(), set()
    if plan:
        main_ids = set(plan.main_points.values_list("acupoint_id", flat=True))
        adjunct_ids = set(plan.adjunct_points.values_list("acupoint_id", flat=True))
    if request.method == "POST":
        main_ids = {int(v) for v in request.POST.getlist("main_points") if v.isdigit()}
        adjunct_ids = {int(v) for v in request.POST.getlist("adjunct_points") if v.isdigit()}
        if not form.is_valid():
            messages.error(request, "请检查治疗方案表单")
        elif not main_ids:
            messages.error(request, "请至少选择一个主穴")
        else:
            if Acupoint.objects.filter(pk__in=main_ids | adjunct_ids).count() != len(
                main_ids | adjunct_ids
            ):
                messages.error(request, "穴位选择包含无效数据")
            else:
                plan = services.save_treatment_plan(
                    appointment,
                    request.user,
                    form.cleaned_data,
                    sorted(main_ids),
                    sorted(adjunct_ids - main_ids),
                )
                services.log_action(
                    request,
                    "保存治疗方案",
                    target=plan.plan_no,
                    detail=f"主穴 {len(main_ids)} 个，配穴 {len(adjunct_ids - main_ids)} 个",
                )
                messages.success(request, "治疗方案已保存")
                return redirect(
                    "doctor_appointment_detail", appointment_id=appointment.pk
                )

    grouped_acupoints = {}
    for point in acupoints:
        grouped_acupoints.setdefault(point.meridian or "其他", []).append(point)

    return render(
        request,
        "doctor/plan_form.html",
        {
            "appointment": appointment,
            "plan": plan,
            "form": form,
            "grouped_acupoints": grouped_acupoints,
            "main_ids": main_ids,
            "adjunct_ids": adjunct_ids,
        },
    )


@doctor_required
def record_create(request, plan_id):
    plan = get_object_or_404(
        TreatmentPlan.objects.select_related("appointment", "patient"),
        pk=plan_id,
        doctor=request.user,
    )
    initial = {
        "treat_time": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        "needling_duration": 30,
    }
    form = RecordForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.plan = plan
        record.doctor = request.user
        action = request.POST.get("action", "registered")
        record.status = (
            TreatmentRecord.Status.CONFIRMED
            if action == "confirm"
            else TreatmentRecord.Status.REGISTERED
        )
        record.save()
        if record.status == TreatmentRecord.Status.CONFIRMED:
            services.complete_appointment_by_record(plan.appointment)
        services.log_action(
            request,
            "录入治疗记录",
            target=record.record_no,
            detail=f"状态：{record.get_status_display()}",
        )
        messages.success(request, "治疗记录已保存")
        return redirect("doctor_appointment_detail", appointment_id=plan.appointment_id)

    return render(
        request,
        "doctor/record_form.html",
        {"plan": plan, "appointment": plan.appointment, "form": form},
    )


@doctor_required
def doctor_patients(request):
    patients = (
        User.objects.filter(
            patient_appointments__doctor=request.user,
            patient_appointments__is_deleted=False,
        )
        .distinct()
        .annotate(
            visit_count=Count(
                "patient_appointments",
                filter=Q(patient_appointments__doctor=request.user, patient_appointments__is_deleted=False),
            )
        )
        .order_by("name")
    )
    keyword = request.GET.get("q", "").strip()
    if keyword:
        patients = patients.filter(
            Q(name__icontains=keyword) | Q(phone__icontains=keyword)
        )
    return render(
        request,
        "doctor/patients.html",
        {"patients": patients, "keyword": keyword},
    )


@doctor_required
def patient_history(request, patient_id):
    patient = get_object_or_404(User, pk=patient_id, role=Role.PATIENT)
    if not can_view_patient_data(request.user, patient):
        raise PermissionDenied("您未接诊过该患者，无权查看其档案")

    appointments = (
        Appointment.objects.filter(patient=patient, doctor=request.user)
        .select_related("schedule")
        .order_by("-appoint_time")
    )
    records = (
        TreatmentRecord.objects.filter(plan__patient=patient, doctor=request.user)
        .select_related("plan")
        .order_by("-treat_time")
    )
    plans = TreatmentPlan.objects.filter(patient=patient, doctor=request.user).order_by(
        "-created_at"
    )
    return render(
        request,
        "doctor/patient_history.html",
        {
            "patient": patient,
            "appointments": appointments,
            "records": records,
            "plans": plans,
        },
    )


@doctor_required
def doctor_profile(request):
    profile, _ = DoctorProfile.objects.get_or_create(user=request.user)
    form = DoctorProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        services.log_action(request, "修改医师资料", target=request.user.username)
        messages.success(request, "医师资料已更新")
        return redirect("doctor_profile")
    return render(
        request,
        "doctor/profile.html",
        {"form": form, "profile": profile},
    )


# ---------------------------------------------------------------- 管理端


@manager_required
def dashboard(request):
    metrics = services.dashboard_metrics()
    labels, values = services.trend_series(7)
    status_data = services.status_distribution()
    workload = services.doctor_workload()
    month_labels, month_values = services.monthly_treatments(6)
    recent = (
        Appointment.objects.select_related("patient", "doctor")
        .order_by("-created_at")[:8]
    )
    return render(
        request,
        "admin/dashboard.html",
        {
            "metrics": metrics,
            "labels": labels,
            "values": values,
            "status_data": status_data,
            "workload": workload,
            "month_labels": month_labels,
            "month_values": month_values,
            "recent": recent,
        },
    )


@manager_required
def stats_api(request):
    labels, values = services.trend_series(7)
    month_labels, month_values = services.monthly_treatments(6)
    return JsonResponse(
        {
            "trend": {"labels": labels, "values": values},
            "status": services.status_distribution(),
            "workload": services.doctor_workload(),
            "monthly": {"labels": month_labels, "values": month_values},
            "metrics": services.dashboard_metrics(),
        }
    )


@manager_required
def admin_appointments(request):
    form = AppointmentFilterForm(request.GET or None)
    appointments = services.filter_appointments(request.GET)
    page = paginate(request, appointments, per_page=12)
    return render(
        request,
        "admin/appointments.html",
        {
            "form": form,
            "page_obj": page,
            "query": query_without_page(request),
            "status_choices": Appointment.Status.choices,
        },
    )


@manager_required
def export_appointments(request):
    appointments = services.filter_appointments(request.GET).select_related(
        "patient", "doctor", "schedule"
    )
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="appointments.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        ["预约单号", "患者", "联系电话", "医师", "就诊时间", "状态", "主诉", "创建时间"]
    )
    for item in appointments:
        writer.writerow(
            [
                item.appointment_no,
                item.patient.display_name,
                item.patient.phone or "",
                item.doctor.display_name,
                timezone.localtime(item.appoint_time).strftime("%Y-%m-%d %H:%M"),
                item.get_status_display(),
                item.chief_complaint,
                timezone.localtime(item.created_at).strftime("%Y-%m-%d %H:%M"),
            ]
        )
    services.log_action(request, "导出预约报表", detail=f"共 {appointments.count()} 条")
    return response


@manager_required
def admin_users(request):
    users = User.objects.select_related("doctor_profile").order_by("-created_at")
    role = request.GET.get("role", "")
    keyword = request.GET.get("q", "").strip()
    if role:
        users = users.filter(role=role)
    if keyword:
        users = users.filter(
            Q(name__icontains=keyword)
            | Q(username__icontains=keyword)
            | Q(phone__icontains=keyword)
        )
    page = paginate(request, users, per_page=12)
    return render(
        request,
        "admin/users.html",
        {
            "page_obj": page,
            "role": role,
            "keyword": keyword,
            "role_choices": Role.choices,
            "query": query_without_page(request),
        },
    )


def _guard_sysadmin(request, target):
    if target.role == Role.SYSADMIN and request.user.role != Role.SYSADMIN:
        raise PermissionDenied("只有系统运维管理员可管理该账号")


@manager_required
def admin_user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password"])
        user.save()
        if user.role == Role.DOCTOR:
            DoctorProfile.objects.create(
                user=user,
                department=form.cleaned_data.get("department") or "针灸科",
                title=form.cleaned_data.get("title", ""),
                specialty=form.cleaned_data.get("specialty", ""),
            )
        services.log_action(
            request, "新增账号", target=user.username, detail=user.get_role_display()
        )
        messages.success(request, f"账号 {user.username} 创建成功")
        return redirect("admin_users")
    return render(
        request,
        "admin/user_form.html",
        {"form": form, "title": "新增账号", "is_create": True},
    )


@manager_required
def admin_user_edit(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    _guard_sysadmin(request, target)
    form = UserEditForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        if user.role == Role.DOCTOR:
            DoctorProfile.objects.get_or_create(user=user)
        services.log_action(
            request, "修改账号", target=user.username, detail="资料与角色已更新"
        )
        messages.success(request, "账号资料已更新")
        return redirect("admin_users")
    return render(
        request,
        "admin/user_form.html",
        {"form": form, "title": f"编辑账号 · {target.username}", "is_create": False},
    )


@require_POST
@manager_required
def admin_user_toggle(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    _guard_sysadmin(request, target)
    if target.pk == request.user.pk:
        messages.error(request, "不能停用当前登录账号")
        return redirect("admin_users")
    target.is_active = not target.is_active
    target.save(update_fields=["is_active", "updated_at"])
    services.log_action(
        request,
        "启用账号" if target.is_active else "停用账号",
        target=target.username,
    )
    messages.success(request, f"账号已{'启用' if target.is_active else '停用'}")
    return redirect("admin_users")


@require_POST
@manager_required
def admin_user_delete(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    _guard_sysadmin(request, target)
    if target.pk == request.user.pk:
        messages.error(request, "不能删除当前登录账号")
        return redirect("admin_users")
    target.soft_delete()
    services.log_action(request, "删除账号（逻辑删除）", target=target.username)
    messages.success(request, "账号已删除（保留历史业务数据）")
    return redirect("admin_users")


@manager_required
def admin_schedules(request):
    today = timezone.localdate()
    schedules = (
        Schedule.objects.select_related("doctor")
        .filter(date__gte=today)
        .order_by("date", "start_time")
    )
    doctor_id = request.GET.get("doctor", "")
    if doctor_id:
        schedules = schedules.filter(doctor_id=doctor_id)
    page = paginate(request, schedules, per_page=14)
    doctors = User.objects.filter(role=Role.DOCTOR)
    return render(
        request,
        "admin/schedules.html",
        {
            "page_obj": page,
            "doctors": doctors,
            "doctor_id": doctor_id,
            "today": today,
            "query": query_without_page(request),
        },
    )


@manager_required
def admin_schedule_edit(request, schedule_id=None):
    instance = get_object_or_404(Schedule, pk=schedule_id) if schedule_id else None
    form = ScheduleForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        schedule = form.save()
        services.log_action(
            request,
            "维护排班",
            target=f"{schedule.doctor.display_name} {schedule.date}",
            detail=f"{schedule.time_range}，号源 {schedule.capacity}",
        )
        messages.success(request, "排班信息已保存")
        return redirect("admin_schedules")
    return render(
        request,
        "admin/schedule_form.html",
        {
            "form": form,
            "instance": instance,
            "title": "编辑排班" if instance else "新增排班",
        },
    )


@require_POST
@manager_required
def admin_schedule_toggle(request, schedule_id):
    schedule = get_object_or_404(Schedule, pk=schedule_id)
    schedule.is_active = not schedule.is_active
    schedule.save(update_fields=["is_active", "updated_at"])
    services.log_action(
        request,
        "停用排班" if not schedule.is_active else "启用排班",
        target=str(schedule),
    )
    messages.success(request, "排班状态已更新")
    return redirect("admin_schedules")


@manager_required
def admin_acupoints(request):
    acupoints = Acupoint.objects.order_by("meridian", "code", "name")
    keyword = request.GET.get("q", "").strip()
    if keyword:
        acupoints = acupoints.filter(
            Q(name__icontains=keyword) | Q(meridian__icontains=keyword)
        )
    page = paginate(request, acupoints, per_page=15)
    return render(
        request,
        "admin/acupoints.html",
        {"page_obj": page, "keyword": keyword, "query": query_without_page(request)},
    )


@manager_required
def admin_acupoint_edit(request, acupoint_id=None):
    instance = get_object_or_404(Acupoint, pk=acupoint_id) if acupoint_id else None
    form = AcupointForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        point = form.save()
        services.log_action(request, "维护穴位", target=point.name)
        messages.success(request, "穴位信息已保存")
        return redirect("admin_acupoints")
    return render(
        request,
        "admin/acupoint_form.html",
        {
            "form": form,
            "instance": instance,
            "title": "编辑穴位" if instance else "新增穴位",
        },
    )


@require_POST
@manager_required
def admin_acupoint_delete(request, acupoint_id):
    point = get_object_or_404(Acupoint, pk=acupoint_id)
    if point.planacupoint_set.exists():
        messages.error(request, "该穴位已被治疗方案引用，不能删除")
    else:
        point.is_deleted = True
        point.save(update_fields=["is_deleted", "updated_at"])
        services.log_action(request, "删除穴位（逻辑删除）", target=point.name)
        messages.success(request, "穴位已删除")
    return redirect("admin_acupoints")


@manager_required
def admin_records(request):
    records = (
        TreatmentRecord.objects.select_related(
            "plan", "plan__patient", "doctor", "plan__appointment"
        )
        .order_by("-created_at")
    )
    status = request.GET.get("status", "")
    if status:
        records = records.filter(status=status)
    keyword = request.GET.get("q", "").strip()
    if keyword:
        records = records.filter(Q(plan__patient__name__icontains=keyword))
    page = paginate(request, records, per_page=12)
    return render(
        request,
        "admin/records.html",
        {
            "page_obj": page,
            "status": status,
            "keyword": keyword,
            "status_choices": TreatmentRecord.Status.choices,
            "query": query_without_page(request),
        },
    )


@require_POST
@manager_required
def admin_record_audit(request, record_id):
    record = get_object_or_404(
        TreatmentRecord.objects.select_related("plan", "plan__appointment"), pk=record_id
    )
    action = request.POST.get("action")
    remark = request.POST.get("remark", "").strip()
    if action == "confirm":
        if record.status == TreatmentRecord.Status.RETURNED:
            messages.error(request, "已退回的记录需由医师重新登记")
            return redirect("admin_records")
        record.status = TreatmentRecord.Status.CONFIRMED
        record.audit_remark = remark
        record.save(update_fields=["status", "audit_remark", "updated_at"])
        services.complete_appointment_by_record(record.plan.appointment)
        services.log_action(request, "审核治疗记录", target=record.record_no, detail="确认")
        messages.success(request, "治疗记录已确认，主流程推进为“已完成”")
    elif action == "return":
        record.status = TreatmentRecord.Status.RETURNED
        record.audit_remark = remark
        record.save(update_fields=["status", "audit_remark", "updated_at"])
        appointment = record.plan.appointment
        if appointment.can_transition_to(Appointment.Status.RETURNED):
            appointment.transition_to(Appointment.Status.RETURNED, reason=remark)
        services.log_action(
            request, "审核治疗记录", target=record.record_no, detail=f"退回：{remark}"
        )
        messages.warning(request, "治疗记录已退回，需重新登记")
    else:
        messages.error(request, "无效的审核操作")
    return redirect("admin_records")


@role_required(Role.SYSADMIN)
def admin_logs(request):
    logs = OperationLog.objects.select_related("user").order_by("-created_at")
    action = request.GET.get("action", "").strip()
    keyword = request.GET.get("q", "").strip()
    if action:
        logs = logs.filter(action=action)
    if keyword:
        logs = logs.filter(
            Q(target__icontains=keyword) | Q(detail__icontains=keyword)
        )
    page = paginate(request, logs, per_page=20)
    actions = (
        OperationLog.objects.values_list("action", flat=True)
        .distinct()
        .order_by("action")
    )
    return render(
        request,
        "admin/logs.html",
        {
            "page_obj": page,
            "action": action,
            "keyword": keyword,
            "actions": actions,
            "query": query_without_page(request),
        },
    )


# ---------------------------------------------------------------- 工具函数


def paginate(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get("page"))


def query_without_page(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


def handler403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def handler404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def handler500(request):
    return render(request, "errors/500.html", status=500)
