from django.conf import settings
from django.contrib import admin
from django.db.models import Count, Max
from django.shortcuts import render
from django.urls import reverse

from .models import EventRegistration, Submission, Survey


def _form_cards():
    surveys = Survey.objects.annotate(
        response_count=Count("submissions", distinct=True),
        latest_response=Max("submissions__submitted_at"),
    )
    cards = [
        {
            "title": survey.title,
            "description": survey.description,
            "type": "普通问卷",
            "status": "收集中" if survey.is_published else "未发布",
            "status_class": "collecting" if survey.is_published else "paused",
            "response_count": survey.response_count,
            "latest_response": survey.latest_response,
            "public_url": survey.get_absolute_url(),
            "edit_url": reverse("admin:surveys_survey_change", args=(survey.pk,)),
            "data_url": (
                f'{reverse("admin:surveys_submission_changelist")}'
                f"?survey__id__exact={survey.pk}"
            ),
        }
        for survey in surveys
    ]
    registration_stats = EventRegistration.objects.aggregate(
        response_count=Count("id"),
        latest_response=Max("submitted_at"),
    )
    cards.append(
        {
            "title": "总包反背锅行动 001 报名表",
            "description": "收集企业信息、参会人员、重点问题和来源渠道。",
            "type": "活动报名",
            "status": "收集中",
            "status_class": "collecting",
            "response_count": registration_stats["response_count"],
            "latest_response": registration_stats["latest_response"],
            "public_url": reverse("surveys:event_registration"),
            "edit_url": "",
            "data_url": reverse("admin:surveys_eventregistration_changelist"),
        }
    )
    return cards


def admin_home(request):
    forms = _form_cards()
    context = {
        **admin.site.each_context(request),
        "title": "表单中心",
        "forms": forms,
        "form_count": len(forms),
        "collecting_count": sum(card["status_class"] == "collecting" for card in forms),
        "response_count": sum(card["response_count"] for card in forms),
        "feishu_enabled": bool(settings.FEISHU_WEBHOOK_URL),
    }
    return render(request, "admin/forms_home.html", context)


def data_center(request):
    forms = _form_cards()
    context = {
        **admin.site.each_context(request),
        "title": "数据中心",
        "forms": forms,
        "form_count": len(forms),
        "response_count": sum(card["response_count"] for card in forms),
        "survey_response_count": Submission.objects.count(),
        "registration_count": EventRegistration.objects.count(),
    }
    return render(request, "admin/data_center.html", context)
