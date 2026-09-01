from django.contrib import admin
from django.urls import include, path

from surveys.admin_views import admin_home, data_center
from surveys.views import healthz


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("admin/data/", admin.site.admin_view(data_center), name="admin_data_center"),
    path("admin/", admin.site.admin_view(admin_home), name="admin_home"),
    path("admin/", admin.site.urls),
    path("", include("surveys.urls")),
]
