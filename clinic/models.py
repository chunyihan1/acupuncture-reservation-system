from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def soft_delete(self):
        return self.update(is_deleted=True, updated_at=timezone.now())


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """默认只返回未删除数据，使用 all_objects 可查询已删除数据。"""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteUserManager(DjangoUserManager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Role(models.TextChoices):
    PATIENT = "patient", "就诊患者"
    DOCTOR = "doctor", "针灸医师"
    ADMIN = "admin", "门诊管理员"
    SYSADMIN = "sysadmin", "系统运维/教学管理员"


class User(AbstractUser):
    role = models.CharField("角色", max_length=20, choices=Role.choices, default=Role.PATIENT)
    name = models.CharField("真实姓名", max_length=50, blank=True)
    phone = models.CharField("联系电话", max_length=20, unique=True, null=True, blank=True)
    id_card = models.CharField("身份证号", max_length=18, unique=True, null=True, blank=True)
    gender = models.CharField(
        "性别", max_length=1, choices=(("M", "男"), ("F", "女")), default="M"
    )
    is_deleted = models.BooleanField("已删除", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    objects = SoftDeleteUserManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def save(self, *args, **kwargs):
        # 空字符串会破坏唯一约束，这里统一转为 None
        self.phone = self.phone or None
        self.id_card = self.id_card or None
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.name or self.username

    @property
    def role_label(self):
        return self.get_role_display()

    @property
    def is_patient(self):
        return self.role == Role.PATIENT

    @property
    def is_doctor(self):
        return self.role == Role.DOCTOR

    @property
    def is_manager(self):
        return self.role in (Role.ADMIN, Role.SYSADMIN)

    @property
    def is_sysadmin(self):
        return self.role == Role.SYSADMIN

    def soft_delete(self):
        self.is_deleted = True
        self.is_active = False
        self.save(update_fields=["is_deleted", "is_active", "updated_at"])

    def __str__(self):
        return f"{self.display_name}（{self.get_role_display()}）"


class TreatmentRoom(models.Model):
    name = models.CharField("治疗室名称", max_length=50, unique=True)
    location = models.CharField("位置", max_length=100, blank=True)
    equipment = models.CharField("设备配置", max_length=200, blank=True)
    is_deleted = models.BooleanField("已删除", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "治疗室"
        verbose_name_plural = "治疗室"

    def __str__(self):
        return self.name


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="doctor_profile", verbose_name="医师账号"
    )
    department = models.CharField("所属科室", max_length=50, default="针灸科")
    title = models.CharField("职称", max_length=50, blank=True)
    specialty = models.CharField("擅长方向", max_length=100, blank=True)
    room = models.ForeignKey(
        TreatmentRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doctors",
        verbose_name="治疗室",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "医师档案"
        verbose_name_plural = "医师档案"

    def __str__(self):
        return f"{self.user.display_name} · {self.department}"


class Schedule(models.Model):
    doctor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="schedules", verbose_name="出诊医师"
    )
    date = models.DateField("出诊日期")
    start_time = models.TimeField("开始时间")
    end_time = models.TimeField("结束时间")
    capacity = models.PositiveSmallIntegerField("号源数量", default=4)
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "医师排班"
        verbose_name_plural = "医师排班"
        ordering = ["date", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "date", "start_time"], name="unique_doctor_slot"
            )
        ]

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("结束时间必须晚于开始时间")

    @property
    def booked_count(self):
        return self.appointments.filter(
            status__in=Appointment.ACTIVE_STATUSES, is_deleted=False
        ).count()

    @property
    def remaining(self):
        return max(self.capacity - self.booked_count, 0)

    @property
    def is_bookable(self):
        return (
            self.is_active
            and self.date >= timezone.localdate()
            and self.remaining > 0
        )

    @property
    def time_range(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

    def __str__(self):
        return f"{self.doctor.display_name} {self.date} {self.time_range}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待排期"
        SCHEDULED = "scheduled", "已排期"
        TREATING = "treating", "治疗中"
        COMPLETED = "completed", "已完成"
        ARCHIVED = "archived", "已归档"
        CANCELLED = "cancelled", "已取消"
        RETURNED = "returned", "已退回(异常)"

    #: 主流程状态机，异常分支单独允许
    TRANSITIONS = {
        Status.PENDING: {Status.SCHEDULED, Status.CANCELLED},
        Status.SCHEDULED: {Status.TREATING, Status.CANCELLED, Status.RETURNED},
        Status.TREATING: {Status.COMPLETED, Status.RETURNED},
        Status.COMPLETED: {Status.ARCHIVED, Status.RETURNED},
        Status.ARCHIVED: set(),
        Status.CANCELLED: set(),
        Status.RETURNED: {Status.SCHEDULED, Status.CANCELLED},
    }

    ACTIVE_STATUSES = [
        Status.PENDING,
        Status.SCHEDULED,
        Status.TREATING,
        Status.COMPLETED,
    ]

    patient = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="patient_appointments", verbose_name="患者"
    )
    doctor = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="doctor_appointments", verbose_name="医师"
    )
    schedule = models.ForeignKey(
        Schedule, on_delete=models.PROTECT, related_name="appointments", verbose_name="排班时段"
    )
    appoint_time = models.DateTimeField("预约就诊时间")
    status = models.CharField(
        "预约状态", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    chief_complaint = models.TextField("患者主诉", blank=True)
    cancel_reason = models.CharField("取消原因", max_length=200, blank=True)
    is_deleted = models.BooleanField("已删除", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "针灸预约"
        verbose_name_plural = "针灸预约"
        ordering = ["-appoint_time"]
        indexes = [
            models.Index(fields=["doctor", "appoint_time"]),
            models.Index(fields=["patient", "status"]),
        ]

    @property
    def appointment_no(self):
        return f"AP{self.created_at:%Y%m%d}{self.pk:04d}"

    @property
    def can_cancel(self):
        return self.status in (self.Status.PENDING, self.Status.SCHEDULED)

    @property
    def status_tone(self):
        return {
            self.Status.PENDING: "warning",
            self.Status.SCHEDULED: "info",
            self.Status.TREATING: "primary",
            self.Status.COMPLETED: "success",
            self.Status.ARCHIVED: "secondary",
            self.Status.CANCELLED: "muted",
            self.Status.RETURNED: "danger",
        }.get(self.status, "secondary")

    def can_transition_to(self, new_status):
        return new_status in self.TRANSITIONS.get(self.Status(self.status), set())

    def transition_to(self, new_status, reason=""):
        if not self.can_transition_to(new_status):
            raise ValidationError(
                f"不允许从“{self.get_status_display()}”流转到“{dict(self.Status.choices).get(new_status, new_status)}”"
            )
        self.status = new_status
        if reason:
            self.cancel_reason = reason
        self.save(update_fields=["status", "cancel_reason", "updated_at"])

    def __str__(self):
        return f"{self.appointment_no} · {self.patient.display_name}"


class Acupoint(models.Model):
    name = models.CharField("穴位名称", max_length=50, unique=True)
    code = models.CharField("穴位代码", max_length=20, blank=True)
    meridian = models.CharField("归经", max_length=50, blank=True)
    location = models.CharField("定位", max_length=200, blank=True)
    is_deleted = models.BooleanField("已删除", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "穴位"
        verbose_name_plural = "穴位"
        ordering = ["meridian", "code", "name"]

    def __str__(self):
        return f"{self.name}（{self.meridian}）" if self.meridian else self.name


class TreatmentPlan(models.Model):
    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name="plan", verbose_name="关联预约"
    )
    patient = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="treatment_plans", verbose_name="患者"
    )
    doctor = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="authored_plans", verbose_name="制定医师"
    )
    syndrome = models.CharField("辨证结果", max_length=100, blank=True)
    technique = models.CharField("针灸手法", max_length=50, blank=True)
    course_cycle = models.PositiveSmallIntegerField("疗程周期（天）", default=14)
    frequency_per_week = models.PositiveSmallIntegerField("每周治疗次数", default=3)
    notes = models.TextField("方案备注", blank=True)
    is_deleted = models.BooleanField("已删除", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "针灸治疗方案"
        verbose_name_plural = "针灸治疗方案"

    @property
    def plan_no(self):
        return f"PL{self.created_at:%Y%m%d}{self.pk:04d}"

    @property
    def main_points(self):
        return self.acupoint_links.filter(type=PlanAcupoint.Type.MAIN)

    @property
    def adjunct_points(self):
        return self.acupoint_links.filter(type=PlanAcupoint.Type.ADJUNCT)

    def __str__(self):
        return f"{self.plan_no} · {self.patient.display_name}"


class PlanAcupoint(models.Model):
    class Type(models.IntegerChoices):
        MAIN = 1, "主穴"
        ADJUNCT = 2, "配穴"

    plan = models.ForeignKey(
        TreatmentPlan, on_delete=models.CASCADE, related_name="acupoint_links"
    )
    acupoint = models.ForeignKey(Acupoint, on_delete=models.PROTECT, verbose_name="穴位")
    type = models.IntegerField("穴位类型", choices=Type.choices, default=Type.MAIN)
    order = models.PositiveSmallIntegerField("排序", default=0)

    class Meta:
        verbose_name = "方案穴位关联"
        verbose_name_plural = "方案穴位关联"
        ordering = ["type", "order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["plan", "acupoint"], name="unique_plan_acupoint")
        ]

    def __str__(self):
        return f"{self.plan.plan_no} · {self.acupoint.name}·{self.get_type_display()}"


class TreatmentRecord(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "待登记"
        REGISTERED = "registered", "已登记"
        CONFIRMED = "confirmed", "已确认"
        RETURNED = "returned", "已退回"

    plan = models.ForeignKey(
        TreatmentPlan, on_delete=models.CASCADE, related_name="records", verbose_name="治疗方案"
    )
    doctor = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="treatment_records", verbose_name="接诊医师"
    )
    treat_time = models.DateTimeField("实际治疗时间")
    needling_duration = models.PositiveSmallIntegerField("留针时长（分钟）", default=30)
    advice = models.TextField("医嘱", blank=True)
    status = models.CharField(
        "记录状态", max_length=20, choices=Status.choices, default=Status.REGISTERED
    )
    audit_remark = models.CharField("审核意见", max_length=200, blank=True)
    is_deleted = models.BooleanField("已删除", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "针灸治疗记录"
        verbose_name_plural = "针灸治疗记录"
        ordering = ["-treat_time"]

    @property
    def record_no(self):
        return f"TR{self.created_at:%Y%m%d}{self.pk:04d}"

    def __str__(self):
        return f"{self.record_no} · {self.plan.patient.display_name}"


class OperationLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operation_logs",
        verbose_name="操作人",
    )
    action = models.CharField("操作类型", max_length=50)
    target = models.CharField("操作对象", max_length=200, blank=True)
    detail = models.TextField("操作描述", blank=True)
    ip = models.GenericIPAddressField("IP 地址", null=True, blank=True)
    created_at = models.DateTimeField("操作时间", auto_now_add=True)

    class Meta:
        verbose_name = "操作日志"
        verbose_name_plural = "操作日志"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action}"
