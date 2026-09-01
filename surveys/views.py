from django.conf import settings
from django.db import connection, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .feishu import send_registration_notification
from .forms import AttendeeFormSet, EventRegistrationForm, SurveyResponseForm
from .models import Answer, Attendee, EventRegistration, Submission, Survey


def home(request):
    survey = Survey.objects.filter(
        slug=settings.DEFAULT_SURVEY_SLUG,
        is_published=True,
    ).first()
    if survey:
        return redirect(survey)
    return render(request, "surveys/home.html")


@require_http_methods(["GET", "POST"])
def survey_detail(request, slug):
    survey = get_object_or_404(
        Survey.objects.prefetch_related("questions"), slug=slug, is_published=True
    )
    form = SurveyResponseForm(request.POST if request.method == "POST" else None, survey=survey)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            submission = Submission.objects.create(survey=survey)
            Answer.objects.bulk_create(
                [
                    Answer(
                        submission=submission,
                        question=question,
                        question_label=question.label,
                        value=form.answer_for(question),
                        display_value=(
                            "；".join(form.answer_for(question))
                            if isinstance(form.answer_for(question), list)
                            else str(form.answer_for(question))
                        ),
                    )
                    for question in survey.questions.all()
                ]
            )
        return redirect("surveys:thanks", slug=survey.slug)
    return render(request, "surveys/detail.html", {"survey": survey, "form": form})


def default_survey(request):
    return survey_detail(request, settings.DEFAULT_SURVEY_SLUG)


def thanks(request, slug):
    survey = get_object_or_404(Survey, slug=slug, is_published=True)
    return render(request, "surveys/thanks.html", {"survey": survey})


def healthz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unhealthy"}, status=503)
    return JsonResponse({"status": "ok"})


@require_http_methods(["GET", "POST"])
def event_registration(request):
    form = EventRegistrationForm(request.POST or None)
    attendee_formset = AttendeeFormSet(request.POST or None, prefix="attendees")
    if request.method == "POST" and form.is_valid() and attendee_formset.is_valid():
        with transaction.atomic():
            registration = form.save()
            Attendee.objects.bulk_create(
                [
                    Attendee(
                        registration=registration,
                        name=attendee_form.cleaned_data["name"],
                        role=attendee_form.cleaned_data["role"],
                        phone=attendee_form.cleaned_data["phone"],
                    )
                    for attendee_form in attendee_formset
                    if attendee_form.cleaned_data
                    and not attendee_form.cleaned_data.get("DELETE")
                ]
            )
        notified, status = send_registration_notification(registration)
        registration.feishu_error = status
        if notified:
            from django.utils import timezone

            registration.feishu_notified_at = timezone.now()
        registration.save(update_fields=("feishu_notified_at", "feishu_error"))
        request.session["latest_event_registration_id"] = str(registration.pk)
        return redirect("surveys:event_registration_thanks")
    return render(
        request,
        "surveys/apply.html",
        {"form": form, "attendee_formset": attendee_formset},
    )


def event_registration_thanks(request):
    registration = get_object_or_404(
        EventRegistration.objects.prefetch_related("attendees"),
        pk=request.session.get("latest_event_registration_id"),
    )
    lines = [
        "【报名问卷 · 总包反背锅行动 001】",
        f"公司名称：{registration.company_name}",
        f"联系人：{registration.contact_name}｜电话：{registration.contact_phone}",
        f"公司所在城市：{registration.city}",
        f"报名人数：{registration.attendees.count()} 人",
    ]
    lines.extend(
        f"参会人员{index}：{person.name}｜{person.role}｜{person.phone}"
        for index, person in enumerate(registration.attendees.all(), start=1)
    )
    lines.extend(
        [
            f"外部合作项目数量：{registration.get_project_count_display()}",
            f"过往涉诉/被追索案件：{registration.get_lawsuit_count_display()}",
            "最希望重点解答的问题：",
        ]
    )
    lines.extend(f"  · {label}" for label in registration.priority_issue_labels())
    if registration.other_risk:
        lines.append(f"最急需解决的合作项目风险（自述）：{registration.other_risk}")
    lines.extend(
        [
            f"来源渠道：{registration.get_source_channel_display()}",
            "—— 请主办方查收并归档 ——",
        ]
    )
    return render(
        request,
        "surveys/apply_thanks.html",
        {"registration_summary": "\n".join(lines)},
    )
