from django.conf import settings
from django.db import connection, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import SurveyResponseForm
from .models import Answer, Submission, Survey


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
