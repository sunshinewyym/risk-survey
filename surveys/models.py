import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse


class Survey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField("标题", max_length=200)
    slug = models.SlugField("公开地址标识", max_length=100, unique=True)
    description = models.TextField("说明", blank=True)
    success_message = models.TextField(
        "提交成功提示",
        default="您的问卷已成功提交，感谢您的配合。",
    )
    is_published = models.BooleanField("允许公开填写", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "问卷"
        verbose_name_plural = "问卷"
        ordering = ("-created_at",)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("surveys:detail", kwargs={"slug": self.slug})


class Question(models.Model):
    TEXT = "text"
    TEXTAREA = "textarea"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    SELECT = "select"
    TYPE_CHOICES = [
        (TEXT, "单行文本"),
        (TEXTAREA, "多行文本"),
        (RADIO, "单选"),
        (CHECKBOX, "多选"),
        (SELECT, "下拉选项"),
    ]
    CHOICE_TYPES = {RADIO, CHECKBOX, SELECT}

    survey = models.ForeignKey(
        Survey,
        verbose_name="所属问卷",
        related_name="questions",
        on_delete=models.CASCADE,
    )
    order = models.PositiveIntegerField("序号", default=1)
    section = models.CharField("分组标题", max_length=120, blank=True)
    label = models.CharField("问题", max_length=500)
    help_text = models.TextField("补充说明", blank=True)
    question_type = models.CharField("类型", max_length=20, choices=TYPE_CHOICES)
    required = models.BooleanField("必填", default=True)
    options = models.JSONField("选项", default=list, blank=True)
    placeholder = models.CharField("输入提示", max_length=200, blank=True)

    class Meta:
        verbose_name = "问题"
        verbose_name_plural = "问题"
        ordering = ("survey", "order", "id")
        constraints = [
            models.UniqueConstraint(fields=("survey", "order"), name="unique_question_order")
        ]

    def __str__(self):
        return f"{self.order}. {self.label}"

    def clean(self):
        super().clean()
        if self.question_type in self.CHOICE_TYPES:
            if not self.options or not isinstance(self.options, list) or not all(
                isinstance(option, str) and option.strip() for option in self.options
            ):
                raise ValidationError({"options": "选项题必须提供至少一个有效选项。"})


class Submission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey = models.ForeignKey(
        Survey,
        verbose_name="问卷",
        related_name="submissions",
        on_delete=models.PROTECT,
    )
    submitted_at = models.DateTimeField("提交时间", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "提交记录"
        verbose_name_plural = "提交记录"
        ordering = ("-submitted_at",)

    def __str__(self):
        return f"{self.survey.title} · {self.submitted_at:%Y-%m-%d %H:%M}"


class Answer(models.Model):
    submission = models.ForeignKey(
        Submission,
        verbose_name="提交记录",
        related_name="answers",
        on_delete=models.CASCADE,
    )
    question = models.ForeignKey(
        Question,
        verbose_name="问题",
        related_name="answers",
        on_delete=models.PROTECT,
    )
    question_label = models.CharField("问题快照", max_length=500)
    value = models.JSONField("原始答案")
    display_value = models.TextField("答案")

    class Meta:
        verbose_name = "答案"
        verbose_name_plural = "答案"
        ordering = ("question__order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("submission", "question"), name="unique_submission_answer"
            )
        ]

    def __str__(self):
        return self.display_value
