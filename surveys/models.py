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


class EventRegistration(models.Model):
    PROJECT_CHOICES = [
        ("within_5", "5 个以内"),
        ("6_15", "6-15 个"),
        ("16_30", "16-30 个"),
        ("over_30", "30 个以上"),
    ]
    LAWSUIT_CHOICES = [
        ("none", "0 个"),
        ("1_3", "1-3 个"),
        ("4_10", "4-10 个"),
        ("over_10", "10 个以上"),
        ("unknown", "未统计"),
    ]
    SOURCE_CHOICES = [
        ("douyin", "抖音"),
        ("channels", "视频号"),
        ("xiaohongshu", "小红书"),
        ("moments", "朋友圈"),
        ("referral", "朋友转介绍"),
        ("other", "其他"),
    ]
    ISSUE_CHOICES = [
        ("cooperation_model", "新规下，挂靠、联营项目还能否继续开展，怎样更安全？"),
        ("management_fee", "合作协议无效后，公司约定的管理费还能否收取？"),
        ("fees_and_tax", "管理费和税费应如何约定、收取，避免被合作方追回？"),
        ("internal_contracting", "项目团队购买公司社保后，能否认定为内部承包？"),
        ("project_review", "接项目前，应重点审查项目和合作方的哪些情况？"),
        ("external_liability", "合作方对外签约、欠款或私刻公章，公司如何避免担责？"),
        ("invoice_risk", "合作方指定供应商虚开发票，公司如何处理并追责？"),
        ("existing_projects", "新规之后，存量合作项目应如何做好风险防控？"),
        ("project_control", "工程款、结算和资料被合作方控制，公司如何拿回主动权？"),
        ("takeover_exit", "合作方失联、资金链断裂或项目亏损时，如何接管、止损和退出？"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name = models.CharField("公司名称", max_length=200)
    contact_name = models.CharField("联系人", max_length=80)
    contact_phone = models.CharField("联系电话", max_length=20, db_index=True)
    city = models.CharField("公司所在城市", max_length=80)
    project_count = models.CharField("外部合作项目数量", max_length=20, choices=PROJECT_CHOICES)
    lawsuit_count = models.CharField("过往涉诉/被追索案件数量", max_length=20, choices=LAWSUIT_CHOICES)
    priority_issues = models.JSONField("希望重点解答的问题", default=list)
    other_risk = models.TextField("其他急需解决的风险", blank=True)
    source_channel = models.CharField("了解活动的渠道", max_length=20, choices=SOURCE_CHOICES)
    submitted_at = models.DateTimeField("提交时间", auto_now_add=True, db_index=True)
    feishu_notified_at = models.DateTimeField("飞书通知时间", null=True, blank=True)
    feishu_error = models.TextField("飞书通知状态说明", blank=True)

    class Meta:
        verbose_name = "活动报名"
        verbose_name_plural = "活动报名"
        ordering = ("-submitted_at",)

    def __str__(self):
        return f"{self.company_name} · {self.contact_name}"

    def priority_issue_labels(self):
        labels = dict(self.ISSUE_CHOICES)
        return [labels.get(value, value) for value in self.priority_issues]


class Attendee(models.Model):
    registration = models.ForeignKey(
        EventRegistration,
        verbose_name="报名记录",
        related_name="attendees",
        on_delete=models.CASCADE,
    )
    name = models.CharField("姓名", max_length=80)
    role = models.CharField("职务", max_length=100)
    phone = models.CharField("联系电话", max_length=20, db_index=True)

    class Meta:
        verbose_name = "参会人员"
        verbose_name_plural = "参会人员"
        ordering = ("id",)

    def __str__(self):
        return f"{self.name}（{self.role}）"
