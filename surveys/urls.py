from django.urls import path

from . import views


app_name = "surveys"
urlpatterns = [
    path("", views.home, name="home"),
    path("s/<slug:slug>/", views.survey_detail, name="detail"),
    path("s/<slug:slug>/thanks/", views.thanks, name="thanks"),
]
