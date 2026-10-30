from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    Acupoint,
    Appointment,
    DoctorProfile,
    OperationLog,
    PlanAcupoint,
    Schedule,
    TreatmentPlan,
    TreatmentRecord,
    TreatmentRoom,
    User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "name", "role", "phone", "is_active", "is_deleted")
    list_filter = ("role", "is_active", "is_deleted")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("业务信息", {"fields": ("role", "name", "phone", "id_card", "gender", "is_deleted")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("业务信息", {"fields": ("role", "name", "phone", "gender")}),
    )


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "department", "title", "specialty", "room")
    search_fields = ("user__username", "user__name")


@admin.register(TreatmentRoom)
class TreatmentRoomAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "equipment", "is_deleted")


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("doctor", "date", "start_time", "end_time", "capacity", "is_active")
    list_filter = ("date", "doctor", "is_active")
    date_hierarchy = "date"


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("appointment_no", "patient", "doctor", "appoint_time", "status")
    list_filter = ("status", "doctor")
    search_fields = ("patient__name", "patient__phone")
    readonly_fields = ("appointment_no",)


@admin.register(Acupoint)
class AcupointAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "meridian", "location", "is_deleted")
    list_filter = ("meridian",)
    search_fields = ("name", "meridian")


class PlanAcupointInline(admin.TabularInline):
    model = PlanAcupoint
    extra = 0


@admin.register(TreatmentPlan)
class TreatmentPlanAdmin(admin.ModelAdmin):
    list_display = ("plan_no", "patient", "doctor", "syndrome", "course_cycle")
    inlines = [PlanAcupointInline]


@admin.register(TreatmentRecord)
class TreatmentRecordAdmin(admin.ModelAdmin):
    list_display = ("record_no", "plan", "doctor", "treat_time", "status")
    list_filter = ("status", "doctor")


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "target", "ip")
    list_filter = ("action",)
    search_fields = ("target", "detail")
    readonly_fields = ("user", "action", "target", "detail", "ip", "created_at")
