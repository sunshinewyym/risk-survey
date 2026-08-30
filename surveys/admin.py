from django.conf import settings
from django.contrib import admin
from django.db.models import Count, Q

from .exports import csv_response, markdown_response, xlsx_response
from .forms import QuestionAdminForm
from .models import Answer, Question, Submission, Survey


admin.site.site_header = "ylaw-survey 问卷管理"
admin.site.site_title = "ylaw-survey"
admin.site.index_title = "客户问卷与提交记录"


class QuestionInline(admin.StackedInline):
    model = Question
    form = QuestionAdminForm
    extra = 0
    fields = (
        "order",
        "section",
        "label",
        "help_text",
        "question_type",
        "required",
        "placeholder",
        "options_text",
    )
    ordering = ("order",)


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "submission_count", "updated_at")
    list_filter = ("is_published", "created_at")
    search_fields = ("title", "slug", "description")
    readonly_fields = ("created_at", "updated_at", "public_url")
    inlines = (QuestionInline,)
    fieldsets = (
        ("问卷信息", {"fields": ("title", "slug", "description", "success_message")}),
        ("发布", {"fields": ("is_published", "public_url")}),
        ("记录", {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_submission_count=Count("submissions"))

    @admin.display(description="提交数", ordering="_submission_count")
    def submission_count(self, obj):
        return obj._submission_count

    @admin.display(description="公开地址")
    def public_url(self, obj):
        return f"https://{settings.PUBLIC_HOST}{obj.get_absolute_url()}" if obj.pk else "保存后生成"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionAdminForm
    list_display = ("order", "label", "survey", "section", "question_type", "required")
    list_filter = ("survey", "question_type", "required", "section")
    search_fields = ("label", "help_text", "survey__title")
    ordering = ("survey", "order")


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = ("question_label", "display_value")
    readonly_fields = fields
    can_delete = False
    ordering = ("question__order",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.action(description="导出所选记录为 CSV")
def export_csv(modeladmin, request, queryset):
    return csv_response(queryset)


@admin.action(description="导出所选记录为 Excel")
def export_excel(modeladmin, request, queryset):
    return xlsx_response(queryset)


@admin.action(description="导出所选记录为 Markdown")
def export_markdown(modeladmin, request, queryset):
    return markdown_response(queryset)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("short_id", "survey", "submitted_at", "answer_count")
    list_filter = ("survey", "submitted_at")
    search_fields = ("id", "survey__title", "survey__slug")
    readonly_fields = ("id", "survey", "submitted_at")
    fields = ("id", "survey", "submitted_at")
    date_hierarchy = "submitted_at"
    list_select_related = ("survey",)
    inlines = (AnswerInline,)
    actions = (export_csv, export_excel, export_markdown)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_answer_count=Count("answers"))

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            queryset = queryset | self.model.objects.filter(
                Q(answers__question_label__icontains=search_term)
                | Q(answers__display_value__icontains=search_term)
            )
            use_distinct = True
        return queryset, use_distinct

    @admin.display(description="编号")
    def short_id(self, obj):
        return str(obj.id).split("-")[0].upper()

    @admin.display(description="答案数", ordering="_answer_count")
    def answer_count(self, obj):
        return obj._answer_count

    def has_add_permission(self, request):
        return False


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("question_label", "display_value", "submission")
    list_filter = ("submission__survey", "question__question_type")
    search_fields = ("question_label", "display_value", "submission__id")
    readonly_fields = ("submission", "question", "question_label", "value", "display_value")

    def has_add_permission(self, request):
        return False
