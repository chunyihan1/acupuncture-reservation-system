import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone

from .models import (
    Acupoint,
    Appointment,
    DoctorProfile,
    Role,
    Schedule,
    TreatmentPlan,
    TreatmentRecord,
    User,
)

PHONE_RE = re.compile(r"^\+?[0-9\- ]{7,20}$")


class StyledFormMixin:
    def _style(self):
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                continue
            css = "form-select" if isinstance(widget, forms.Select) else "form-control"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css}".strip()
            widget.attrs.setdefault("placeholder", field.label or name)


class LoginForm(StyledFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class RegisterForm(StyledFormMixin, UserCreationForm):
    name = forms.CharField(label="真实姓名", max_length=50)
    phone = forms.CharField(label="联系电话", max_length=20)
    gender = forms.ChoiceField(label="性别", choices=(("M", "男"), ("F", "女")))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "name", "phone", "gender")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "登录账号"
        self.fields["password1"].label = "密码"
        self.fields["password2"].label = "确认密码"
        self._style()
        self.fields["username"].widget.attrs["placeholder"] = "请输入登录账号"
        self.fields["phone"].widget.attrs["placeholder"] = "请输入手机号"

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not PHONE_RE.match(phone):
            raise forms.ValidationError("请输入有效的联系电话")
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("该手机号已被注册")
        return phone


class DoctorProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = DoctorProfile
        fields = ("department", "title", "specialty", "room")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class ScheduleForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ("doctor", "date", "start_time", "end_time", "capacity", "is_active")
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = User.objects.filter(role=Role.DOCTOR)
        self._style()

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date < timezone.localdate():
            raise forms.ValidationError("不能创建过去日期的排班")
        return date

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if start and end and start >= end:
            self.add_error("end_time", "结束时间必须晚于开始时间")
        return cleaned


class AppointmentForm(StyledFormMixin, forms.Form):
    chief_complaint = forms.CharField(
        label="主诉症状",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "例如：颈肩疼痛 3 天，久坐后加重"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class PlanForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TreatmentPlan
        fields = (
            "syndrome",
            "technique",
            "course_cycle",
            "frequency_per_week",
            "notes",
        )
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "syndrome": forms.TextInput(attrs={"placeholder": "例如：气血两虚证"}),
            "technique": forms.TextInput(attrs={"placeholder": "例如：提插捻转"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class RecordForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TreatmentRecord
        fields = ("treat_time", "needling_duration", "advice")
        widgets = {
            "treat_time": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "advice": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["treat_time"].input_formats = ["%Y-%m-%dT%H:%M"]
        self._style()

    def clean_needling_duration(self):
        duration = self.cleaned_data["needling_duration"]
        if not 1 <= duration <= 240:
            raise forms.ValidationError("留针时长应在 1-240 分钟之间")
        return duration


class UserCreateForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(label="初始密码", widget=forms.PasswordInput)
    department = forms.CharField(label="所属科室", required=False, initial="针灸科")
    title = forms.CharField(label="职称", required=False)
    specialty = forms.CharField(label="擅长方向", required=False)

    class Meta:
        model = User
        fields = ("username", "name", "phone", "gender", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (Role.PATIENT, "就诊患者"),
            (Role.DOCTOR, "针灸医师"),
            (Role.ADMIN, "门诊管理员"),
            (Role.SYSADMIN, "系统运维/教学管理员"),
        ]
        self._style()

    def clean_phone(self):
        phone = self.cleaned_data.get("phone") or None
        if phone and User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("该手机号已被使用")
        return phone

    def clean_password(self):
        password = self.cleaned_data["password"]
        if len(password) < 8:
            raise forms.ValidationError("密码长度不得少于 8 位")
        return password


class UserEditForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "name", "phone", "id_card", "gender", "role", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_phone(self):
        phone = self.cleaned_data.get("phone") or None
        qs = User.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if phone and qs.exists():
            raise forms.ValidationError("该手机号已被使用")
        return phone


class AcupointForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Acupoint
        fields = ("name", "code", "meridian", "location")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class AppointmentFilterForm(StyledFormMixin, forms.Form):
    status = forms.ChoiceField(
        label="预约状态", required=False, choices=[("", "全部")] + list(Appointment.Status.choices)
    )
    doctor = forms.ModelChoiceField(
        label="接诊医师", required=False, queryset=User.objects.none(), empty_label="全部医师"
    )
    start = forms.DateField(
        label="开始日期", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    end = forms.DateField(
        label="结束日期", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    q = forms.CharField(label="关键词", required=False, max_length=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = User.objects.filter(role=Role.DOCTOR)
        self._style()
