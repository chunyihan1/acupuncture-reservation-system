from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "针灸预约系统后台"
admin.site.site_title = "ART-RS 后台"
admin.site.index_title = "基础数据维护"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("clinic.urls")),
]

handler403 = "clinic.views.handler403"
handler404 = "clinic.views.handler404"
handler500 = "clinic.views.handler500"
