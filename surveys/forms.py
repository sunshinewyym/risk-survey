from collections import OrderedDict

from django import forms

from .models import Question


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
