from collections import OrderedDict
import re

from django import forms
from django.forms import formset_factory

from .models import Attendee, EventRegistration, Question


PHONE_PATTERN = r"^1[3-9]\d{9}$"


class EventRegistrationForm(forms.ModelForm):
    project_count = forms.ChoiceField(
        label="公司目前与外部合作的项目数量",
        choices=EventRegistration.PROJECT_CHOICES,
        widget=forms.RadioSelect,
    )
    lawsuit_count = forms.ChoiceField(
        label="公司过往涉诉 / 被追索案件数量",
        choices=EventRegistration.LAWSUIT_CHOICES,
        widget=forms.RadioSelect,
    )
    priority_issues = forms.MultipleChoiceField(
        label="本次专场中，您最希望重点解答哪些问题？",
        help_text="请选择 1-3 项，高频问题将优先安排讲解。",
        choices=EventRegistration.ISSUE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )
    source_channel = forms.ChoiceField(
        label="从哪里了解到本次活动",
        choices=EventRegistration.SOURCE_CHOICES,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = EventRegistration
        fields = (
            "company_name",
            "contact_name",
            "contact_phone",
            "city",
            "project_count",
            "lawsuit_count",
            "priority_issues",
            "other_risk",
            "source_channel",
        )
        widgets = {
            "company_name": forms.TextInput(attrs={"placeholder": "请填写营业执照上的全称"}),
            "contact_name": forms.TextInput(attrs={"placeholder": "请输入联系人姓名"}),
            "contact_phone": forms.TextInput(
                attrs={"placeholder": "请输入 11 位手机号", "inputmode": "numeric"}
            ),
            "city": forms.TextInput(attrs={"placeholder": "如：广州"}),
            "project_count": forms.RadioSelect,
            "lawsuit_count": forms.RadioSelect,
            "other_risk": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "简单描述项目背景、当前困难和希望实现的结果",
                }
            ),
            "source_channel": forms.RadioSelect,
        }
        error_messages = {
            "company_name": {"required": "请填写公司名称"},
            "contact_name": {"required": "请填写联系人"},
            "contact_phone": {"required": "请填写联系电话"},
            "city": {"required": "请填写公司所在城市"},
        }

    def clean_contact_phone(self):
        phone = self.cleaned_data["contact_phone"].strip()
        if not re.fullmatch(PHONE_PATTERN, phone):
            raise forms.ValidationError("请输入正确的 11 位手机号")
        return phone

    def clean_priority_issues(self):
        issues = self.cleaned_data["priority_issues"]
        if len(issues) > 3:
            raise forms.ValidationError("最多选择 3 项")
        return issues


class AttendeeForm(forms.ModelForm):
    class Meta:
        model = Attendee
        fields = ("name", "role", "phone")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "姓名"}),
            "role": forms.TextInput(attrs={"placeholder": "如：老板 / 财务负责人"}),
            "phone": forms.TextInput(
                attrs={"placeholder": "11 位手机号", "inputmode": "numeric"}
            ),
        }

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not re.fullmatch(PHONE_PATTERN, phone):
            raise forms.ValidationError("请输入正确的 11 位手机号")
        return phone


AttendeeFormSet = formset_factory(
    AttendeeForm,
    extra=0,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class SurveyResponseForm(forms.Form):
    def __init__(self, *args, survey, **kwargs):
        super().__init__(*args, **kwargs)
        self.survey = survey
        grouped = OrderedDict()
        for question in survey.questions.all():
            name = self.field_name(question)
            common = {
                "label": question.label,
                "help_text": question.help_text,
                "required": question.required,
            }
            if question.question_type == Question.TEXT:
                field = forms.CharField(
                    **common,
                    max_length=2000,
                    widget=forms.TextInput(
                        attrs={"class": "text-input", "placeholder": question.placeholder}
                    ),
                )
            elif question.question_type == Question.TEXTAREA:
                field = forms.CharField(
                    **common,
                    max_length=10000,
                    widget=forms.Textarea(
                        attrs={
                            "class": "text-input",
                            "rows": 5,
                            "placeholder": question.placeholder,
                        }
                    ),
                )
            elif question.question_type == Question.CHECKBOX:
                field = forms.MultipleChoiceField(
                    **common,
                    choices=[(option, option) for option in question.options],
                    widget=forms.CheckboxSelectMultiple(attrs={"class": "choice-list"}),
                )
            elif question.question_type == Question.RADIO:
                field = forms.ChoiceField(
                    **common,
                    choices=[(option, option) for option in question.options],
                    widget=forms.RadioSelect(attrs={"class": "choice-list"}),
                )
            else:
                field = forms.ChoiceField(
                    **common,
                    choices=[("", "请选择")] + [(option, option) for option in question.options],
                    widget=forms.Select(attrs={"class": "text-input"}),
                )
            field.question = question
            field.question_order = question.order
            self.fields[name] = field
            grouped.setdefault(question.section or "问卷内容", []).append(name)
        self.question_groups = [
            (section, [self[name] for name in names]) for section, names in grouped.items()
        ]

    @staticmethod
    def field_name(question):
        return f"q_{question.pk}"

    def answer_for(self, question):
        return self.cleaned_data[self.field_name(question)]


class QuestionAdminForm(forms.ModelForm):
    options_text = forms.CharField(
        label="选项（每行一个）",
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="单选、多选和下拉题必填；每行填写一个选项。",
    )

    class Meta:
        model = Question
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["options_text"].initial = "\n".join(self.instance.options)

    def clean(self):
        cleaned = super().clean()
        options = list(
            dict.fromkeys(
                line.strip() for line in cleaned.get("options_text", "").splitlines() if line.strip()
            )
        )
        if cleaned.get("question_type") in Question.CHOICE_TYPES and not options:
            self.add_error("options_text", "该题型至少需要一个选项。")
        cleaned["parsed_options"] = options
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.options = self.cleaned_data.get("parsed_options", [])
        if commit:
            instance.save()
        return instance
