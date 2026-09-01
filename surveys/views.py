from django.conf import settings
from django.db import IntegrityError, connection, transaction
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
    attendee_required_error = False
    if request.method == "POST":
        form_valid = form.is_valid()
        formset_valid = attendee_formset.is_valid()
        attendee_data = (
            [
                attendee_form.cleaned_data
                for attendee_form in attendee_formset
                if attendee_form.cleaned_data
                and not attendee_form.cleaned_data.get("DELETE")
            ]
            if formset_valid
            else []
        )
        attendee_required_error = (
            form_valid
            and form.cleaned_data["contact_attending"] is False
            and not attendee_data
        )
        if form_valid and formset_valid and not attendee_required_error:
            registration = form.save(commit=False)
            registration.submission_token = form.cleaned_data["submission_token"]
            attendees = []
            seen_phones = set()
            if registration.contact_attending:
                attendees.append(
                    Attendee(
                        registration=registration,
                        name=registration.contact_name,
                        role=registration.contact_role,
                        phone=registration.contact_phone,
                    )
                )
                seen_phones.add(registration.contact_phone)
            for person in attendee_data:
                if person["phone"] in seen_phones:
                    continue
                attendees.append(
                    Attendee(
                        registration=registration,
                        name=person["name"],
                        role=person["role"],
                        phone=person["phone"],
                    )
                )
                seen_phones.add(person["phone"])
            try:
                with transaction.atomic():
                    registration.save()
                    Attendee.objects.bulk_create(attendees)
            except IntegrityError:
                if EventRegistration.objects.filter(
                    submission_token=form.cleaned_data["submission_token"]
                ).exists():
                    return redirect("surveys:event_registration_thanks")
                raise
            notified, status = send_registration_notification(registration)
            registration.feishu_error = status
            if notified:
                from django.utils import timezone

                registration.feishu_notified_at = timezone.now()
            registration.save(update_fields=("feishu_notified_at", "feishu_error"))
            return redirect("surveys:event_registration_thanks")
    return render(
        request,
        "surveys/apply.html",
        {
            "form": form,
            "attendee_formset": attendee_formset,
            "attendee_required_error": attendee_required_error,
        },
    )


def event_registration_thanks(request):
    return render(request, "surveys/apply_thanks.html")
