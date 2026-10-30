from django.urls import path

from . import views

urlpatterns = [
    # 认证
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("", views.home, name="home"),

    # 共享：预约与记录详情
    path("appointments/<int:appointment_id>/", views.appointment_detail, name="appointment_detail"),
    path("records/<int:record_id>/", views.record_detail, name="record_detail"),

    # 患者端
    path("patient/doctors/", views.doctor_list, name="doctor_list"),
    path(
        "patient/doctors/<int:doctor_id>/schedules/",
        views.doctor_schedules,
        name="doctor_schedules",
    ),
    path("patient/book/<int:schedule_id>/", views.book_appointment, name="book_appointment"),
    path("patient/appointments/", views.patient_appointments, name="patient_appointments"),
    path(
        "patient/appointments/<int:appointment_id>/cancel/",
        views.cancel_appointment,
        name="cancel_appointment",
    ),
    path("patient/records/", views.my_records, name="my_records"),

    # 医师端
    path("doctor/dashboard/", views.doctor_dashboard, name="doctor_dashboard"),
    path("doctor/appointments/", views.doctor_appointments, name="doctor_appointments"),
    path(
        "doctor/appointments/<int:appointment_id>/",
        views.doctor_appointment_detail,
        name="doctor_appointment_detail",
    ),
    path(
        "doctor/appointments/<int:appointment_id>/transition/",
        views.doctor_transition,
        name="doctor_transition",
    ),
    path(
        "doctor/appointments/<int:appointment_id>/plan/",
        views.plan_edit,
        name="plan_edit",
    ),
    path(
        "doctor/plans/<int:plan_id>/records/new/",
        views.record_create,
        name="record_create",
    ),
    path("doctor/patients/", views.doctor_patients, name="doctor_patients"),
    path(
        "doctor/patients/<int:patient_id>/history/",
        views.patient_history,
        name="patient_history",
    ),
    path("doctor/profile/", views.doctor_profile, name="doctor_profile"),

    # 管理端
    path("manage/dashboard/", views.dashboard, name="dashboard"),
    path("manage/api/stats/", views.stats_api, name="stats_api"),
    path("manage/appointments/", views.admin_appointments, name="admin_appointments"),
    path(
        "manage/appointments/export/",
        views.export_appointments,
        name="export_appointments",
    ),
    path("manage/users/", views.admin_users, name="admin_users"),
    path("manage/users/new/", views.admin_user_create, name="admin_user_create"),
    path("manage/users/<int:user_id>/edit/", views.admin_user_edit, name="admin_user_edit"),
    path(
        "manage/users/<int:user_id>/toggle/",
        views.admin_user_toggle,
        name="admin_user_toggle",
    ),
    path(
        "manage/users/<int:user_id>/delete/",
        views.admin_user_delete,
        name="admin_user_delete",
    ),
    path("manage/schedules/", views.admin_schedules, name="admin_schedules"),
    path(
        "manage/schedules/new/",
        views.admin_schedule_edit,
        name="admin_schedule_create",
    ),
    path(
        "manage/schedules/<int:schedule_id>/edit/",
        views.admin_schedule_edit,
        name="admin_schedule_edit",
    ),
    path(
        "manage/schedules/<int:schedule_id>/toggle/",
        views.admin_schedule_toggle,
        name="admin_schedule_toggle",
    ),
    path("manage/acupoints/", views.admin_acupoints, name="admin_acupoints"),
    path(
        "manage/acupoints/new/",
        views.admin_acupoint_edit,
        name="admin_acupoint_create",
    ),
    path(
        "manage/acupoints/<int:acupoint_id>/edit/",
        views.admin_acupoint_edit,
        name="admin_acupoint_edit",
    ),
    path(
        "manage/acupoints/<int:acupoint_id>/delete/",
        views.admin_acupoint_delete,
        name="admin_acupoint_delete",
    ),
    path("manage/records/", views.admin_records, name="admin_records"),
    path(
        "manage/records/<int:record_id>/audit/",
        views.admin_record_audit,
        name="admin_record_audit",
    ),
    path("manage/logs/", views.admin_logs, name="admin_logs"),
]
