from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Role


def role_required(*roles):
    """功能级权限：仅允许指定角色访问，未登录用户跳转登录页。"""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied("当前角色无权访问该功能")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


patient_required = role_required(Role.PATIENT)
doctor_required = role_required(Role.DOCTOR)
manager_required = role_required(Role.ADMIN, Role.SYSADMIN)
sysadmin_required = role_required(Role.SYSADMIN)


def can_view_patient_data(user, patient):
    """数据级权限（行级隔离）：患者仅本人，医师仅接诊过的患者，管理员全量。"""
    if user.is_manager:
        return True
    if user.is_patient:
        return patient.pk == user.pk
    if user.is_doctor:
        from .models import Appointment

        return Appointment.objects.filter(patient=patient, doctor=user).exists()
    return False
