from django.urls import path

from . import views


app_name = "surveys"
urlpatterns = [
    path("", views.home, name="home"),
    path("survey/", views.default_survey, name="default_survey"),
    path("apply/", views.event_registration, name="event_registration"),
    path("apply/thanks/", views.event_registration_thanks, name="event_registration_thanks"),
    path("s/<slug:slug>/", views.survey_detail, name="detail"),
    path("s/<slug:slug>/thanks/", views.thanks, name="thanks"),
]
