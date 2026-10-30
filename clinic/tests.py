from datetime import time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import services
from .models import (
    Acupoint,
    Appointment,
    DoctorProfile,
    PlanAcupoint,
    Role,
    Schedule,
    TreatmentPlan,
    TreatmentRecord,
    TreatmentRoom,
    User,
)
from .templatetags.clinic_extras import mask_phone


class ClinicTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.room = TreatmentRoom.objects.create(name="针灸一诊室", location="门诊二层")
        cls.doctor = User.objects.create_user(
            username="doctor_a",
            password="testpass123",
            name="赵医师",
            phone="13900000001",
            role=Role.DOCTOR,
        )
        DoctorProfile.objects.create(user=cls.doctor, department="针灸科", title="主治医师", room=cls.room)
        cls.other_doctor = User.objects.create_user(
            username="doctor_b",
            password="testpass123",
            name="孙医师",
            phone="13900000002",
            role=Role.DOCTOR,
        )
        DoctorProfile.objects.create(user=cls.other_doctor, department="针灸科")

        cls.patient = User.objects.create_user(
            username="patient_a",
            password="testpass123",
            name="张伟",
            phone="13900000003",
            role=Role.PATIENT,
        )
        cls.patient_b = User.objects.create_user(
            username="patient_b",
            password="testpass123",
            name="李娜",
            phone="13900000004",
            role=Role.PATIENT,
        )
        cls.patient_c = User.objects.create_user(
            username="patient_c",
            password="testpass123",
            name="王芳",
            phone="13900000005",
            role=Role.PATIENT,
        )
        cls.admin = User.objects.create_user(
            username="manager",
            password="testpass123",
            name="管理员",
            phone="13900000006",
            role=Role.ADMIN,
        )
        cls.sysadmin = User.objects.create_user(
            username="sys",
            password="testpass123",
            name="运维",
            phone="13900000007",
            role=Role.SYSADMIN,
        )

        cls.tomorrow = timezone.localdate() + timedelta(days=1)
        cls.schedule = Schedule.objects.create(
            doctor=cls.doctor,
            date=cls.tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=2,
        )
        cls.other_schedule = Schedule.objects.create(
            doctor=cls.doctor,
            date=cls.tomorrow,
            start_time=time(14, 0),
            end_time=time(15, 0),
            capacity=3,
        )
        cls.point_1 = Acupoint.objects.create(name="合谷", code="LI4", meridian="手阳明大肠经")
        cls.point_2 = Acupoint.objects.create(name="风池", code="GB20", meridian="足少阳胆经")
        cls.point_3 = Acupoint.objects.create(name="足三里", code="ST36", meridian="足阳明胃经")


class BookingTests(ClinicTestBase):
    def test_booking_creates_pending_appointment(self):
        self.client.force_login(self.patient)
        response = self.client.post(
            reverse("book_appointment", args=[self.schedule.pk]),
            {"chief_complaint": "颈肩酸痛"},
        )
        self.assertRedirects(response, reverse("patient_appointments"))
        appointment = Appointment.objects.get(patient=self.patient)
        self.assertEqual(appointment.status, Appointment.Status.PENDING)
        self.assertEqual(appointment.doctor, self.doctor)

    def test_duplicate_booking_same_slot_blocked(self):
        self.client.force_login(self.patient)
        data = {"chief_complaint": "颈肩酸痛"}
        self.client.post(reverse("book_appointment", args=[self.schedule.pk]), data)
        response = self.client.post(reverse("book_appointment", args=[self.schedule.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Appointment.objects.filter(patient=self.patient, schedule=self.schedule).count(), 1
        )

    def test_capacity_limit(self):
        services.create_appointment(self.patient, self.schedule.pk, "颈椎不适")
        services.create_appointment(self.patient_b, self.schedule.pk, "肩痛")
        self.assertEqual(self.schedule.remaining, 0)
        with self.assertRaises(services.BookingError):
            services.create_appointment(self.patient_c, self.schedule.pk, "腰痛")

    def test_past_schedule_rejected(self):
        past = Schedule.objects.create(
            doctor=self.doctor,
            date=timezone.localdate() - timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        with self.assertRaises(services.BookingError):
            services.create_appointment(self.patient, past.pk, "")

    def test_cancel_releases_slot(self):
        appointment = services.create_appointment(self.patient, self.schedule.pk, "")
        appointment.transition_to(Appointment.Status.CANCELLED)
        self.assertEqual(self.schedule.remaining, 2)
        services.create_appointment(self.patient_b, self.schedule.pk, "")

    def test_patient_only_sees_own_appointments(self):
        appointment = services.create_appointment(self.patient_b, self.schedule.pk, "")
        self.client.force_login(self.patient)
        response = self.client.get(reverse("appointment_detail", args=[appointment.pk]))
        self.assertEqual(response.status_code, 403)

    def test_patient_cannot_cancel_others_appointment(self):
        appointment = services.create_appointment(self.patient_b, self.schedule.pk, "")
        self.client.force_login(self.patient)
        response = self.client.post(reverse("cancel_appointment", args=[appointment.pk]))
        self.assertEqual(response.status_code, 404)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.PENDING)


class StateMachineTests(ClinicTestBase):
    def test_invalid_transition_rejected(self):
        appointment = services.create_appointment(self.patient, self.schedule.pk, "")
        with self.assertRaises(ValidationError):
            appointment.transition_to(Appointment.Status.COMPLETED)

    def test_valid_flow_to_completed(self):
        appointment = services.create_appointment(self.patient, self.schedule.pk, "")
        appointment.transition_to(Appointment.Status.SCHEDULED)
        appointment.transition_to(Appointment.Status.TREATING)
        appointment.transition_to(Appointment.Status.COMPLETED)
        self.assertEqual(appointment.status, Appointment.Status.COMPLETED)

    def test_doctor_can_confirm_schedule(self):
        appointment = services.create_appointment(self.patient, self.schedule.pk, "")
        self.client.force_login(self.doctor)
        response = self.client.post(
            reverse("doctor_transition", args=[appointment.pk]),
            {"status": Appointment.Status.SCHEDULED},
        )
        self.assertRedirects(
            response, reverse("doctor_appointment_detail", args=[appointment.pk])
        )
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)


class TreatmentTests(ClinicTestBase):
    def _make_scheduled_appointment(self):
        appointment = services.create_appointment(self.patient, self.other_schedule.pk, "失眠")
        appointment.transition_to(Appointment.Status.SCHEDULED)
        return appointment

    def test_create_plan_with_main_and_adjunct_points(self):
        appointment = self._make_scheduled_appointment()
        self.client.force_login(self.doctor)
        response = self.client.post(
            reverse("plan_edit", args=[appointment.pk]),
            {
                "syndrome": "心脾两虚证",
                "technique": "提插捻转补法",
                "course_cycle": 14,
                "frequency_per_week": 3,
                "notes": "注意休息",
                "main_points": [self.point_1.pk, self.point_2.pk],
                "adjunct_points": [self.point_3.pk],
            },
        )
        self.assertRedirects(
            response, reverse("doctor_appointment_detail", args=[appointment.pk])
        )
        plan = TreatmentPlan.objects.get(appointment=appointment)
        self.assertEqual(plan.main_points.count(), 2)
        self.assertEqual(plan.adjunct_points.count(), 1)
        self.assertFalse(
            PlanAcupoint.objects.filter(plan=plan, acupoint=self.point_3, type=PlanAcupoint.Type.MAIN).exists()
        )

    def test_plan_requires_main_point(self):
        appointment = self._make_scheduled_appointment()
        self.client.force_login(self.doctor)
        response = self.client.post(
            reverse("plan_edit", args=[appointment.pk]),
            {
                "syndrome": "心脾两虚证",
                "technique": "补法",
                "course_cycle": 14,
                "frequency_per_week": 3,
                "adjunct_points": [self.point_3.pk],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TreatmentPlan.objects.filter(appointment=appointment).exists())

    def test_confirm_record_completes_appointment(self):
        appointment = self._make_scheduled_appointment()
        plan = services.save_treatment_plan(
            appointment,
            self.doctor,
            {"syndrome": "心脾两虚证", "technique": "补法", "course_cycle": 14, "frequency_per_week": 3},
            [self.point_1.pk],
            [self.point_2.pk],
        )
        self.client.force_login(self.doctor)
        response = self.client.post(
            reverse("record_create", args=[plan.pk]),
            {
                "treat_time": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "needling_duration": 30,
                "advice": "规律作息",
                "action": "confirm",
            },
        )
        self.assertRedirects(
            response, reverse("doctor_appointment_detail", args=[appointment.pk])
        )
        record = TreatmentRecord.objects.get(plan=plan)
        self.assertEqual(record.status, TreatmentRecord.Status.CONFIRMED)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.COMPLETED)

    def test_admin_audit_confirms_record(self):
        appointment = self._make_scheduled_appointment()
        plan = services.save_treatment_plan(
            appointment,
            self.doctor,
            {"syndrome": "心脾两虚证", "technique": "补法", "course_cycle": 14, "frequency_per_week": 3},
            [self.point_1.pk],
            [],
        )
        record = TreatmentRecord.objects.create(
            plan=plan,
            doctor=self.doctor,
            treat_time=timezone.now(),
            needling_duration=30,
            status=TreatmentRecord.Status.REGISTERED,
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin_record_audit", args=[record.pk]),
            {"action": "confirm", "remark": "审核通过"},
        )
        self.assertRedirects(response, reverse("admin_records"))
        record.refresh_from_db()
        self.assertEqual(record.status, TreatmentRecord.Status.CONFIRMED)


class PermissionTests(ClinicTestBase):
    def test_patient_cannot_access_admin_dashboard(self):
        self.client.force_login(self.patient)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_doctor_cannot_access_user_management(self):
        self.client.force_login(self.doctor)
        response = self.client.get(reverse("admin_users"))
        self.assertEqual(response.status_code, 403)

    def test_doctor_cannot_view_other_doctor_appointment(self):
        appointment = services.create_appointment(self.patient, self.other_schedule.pk, "")
        appointment.doctor = self.other_doctor
        appointment.save()
        self.client.force_login(self.doctor)
        response = self.client.get(
            reverse("doctor_appointment_detail", args=[appointment.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_doctor_cannot_view_unrelated_patient_history(self):
        self.client.force_login(self.doctor)
        response = self.client.get(reverse("patient_history", args=[self.patient_b.pk]))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_logs_only_sysadmin(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin_logs")).status_code, 403)
        self.client.force_login(self.sysadmin)
        self.assertEqual(self.client.get(reverse("admin_logs")).status_code, 200)

    def test_patient_cannot_view_others_record(self):
        appointment = services.create_appointment(self.patient_b, self.other_schedule.pk, "")
        plan = services.save_treatment_plan(
            appointment,
            self.doctor,
            {"syndrome": "测试", "technique": "", "course_cycle": 14, "frequency_per_week": 3},
            [self.point_1.pk],
            [],
        )
        record = TreatmentRecord.objects.create(
            plan=plan, doctor=self.doctor, treat_time=timezone.now()
        )
        self.client.force_login(self.patient)
        response = self.client.get(reverse("record_detail", args=[record.pk]))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("patient_appointments"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


class UtilityTests(TestCase):
    def test_mask_phone(self):
        self.assertEqual(mask_phone("13800000123"), "138****0123")
        self.assertEqual(mask_phone(""), "—")
