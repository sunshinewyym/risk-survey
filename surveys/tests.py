from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Answer, Question, Submission, Survey


HOSTS = override_settings(
    ALLOWED_HOSTS=["survey.test", "testserver"],
    PUBLIC_HOST="survey.test",
    DEFAULT_SURVEY_SLUG="customer-needs",
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)


@HOSTS
class PublicSurveyTests(TestCase):
    def setUp(self):
        self.survey = Survey.objects.create(
            title="客户需求调查",
            slug="customer-needs",
            description="请按实际情况填写。",
            is_published=True,
        )
        question_data = [
            (1, "姓名", Question.TEXT, True, []),
            (2, "补充说明", Question.TEXTAREA, False, []),
            (3, "合作意向", Question.RADIO, True, ["有", "无"]),
            (4, "关注事项", Question.CHECKBOX, True, ["合同", "税务"]),
            (5, "跟进时间", Question.SELECT, True, ["本周", "下周"]),
        ]
        self.questions = [
            Question.objects.create(
                survey=self.survey,
                order=order,
                section="基本信息",
                label=label,
                question_type=question_type,
                required=required,
                options=options,
            )
            for order, label, question_type, required, options in question_data
        ]

    def test_public_form_requires_csrf_and_saves_every_answer(self):
        client = Client(enforce_csrf_checks=True, HTTP_HOST="survey.test")
        url = reverse("surveys:detail", kwargs={"slug": self.survey.slug})
        page = client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "客户需求调查")
        self.assertContains(page, 'id="validation-summary"', html=False)
        self.assertContains(page, "hidden", html=False)
        data = {
            f"q_{self.questions[0].pk}": "张三",
            f"q_{self.questions[1].pk}": "希望进一步沟通",
            f"q_{self.questions[2].pk}": "有",
            f"q_{self.questions[3].pk}": ["合同", "税务"],
            f"q_{self.questions[4].pk}": "本周",
        }
        self.assertEqual(client.post(url, data).status_code, 403)
        data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        response = client.post(url, data)
        self.assertRedirects(
            response,
            reverse("surveys:thanks", kwargs={"slug": self.survey.slug}),
            fetch_redirect_response=False,
        )
        submission = Submission.objects.get()
        self.assertIsNotNone(submission.submitted_at)
        self.assertEqual(submission.answers.count(), 5)
        self.assertEqual(
            Answer.objects.get(question=self.questions[3]).display_value,
            "合同；税务",
        )

    def test_required_fields_are_validated(self):
        response = self.client.post(
            reverse("surveys:detail", kwargs={"slug": self.survey.slug}),
            HTTP_HOST="survey.test",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "这个字段是必填项", count=4)
        self.assertContains(response, "还有必填项未完成")
        self.assertContains(response, 'class="question invalid"', count=4, html=False)
        self.assertFalse(Submission.objects.exists())

    def test_choice_question_requires_options(self):
        question = Question(
            survey=self.survey,
            order=99,
            label="无选项问题",
            question_type=Question.RADIO,
            options=[],
        )
        with self.assertRaises(ValidationError):
            question.full_clean()

    def test_public_and_admin_share_one_hostname(self):
        public_url = reverse("surveys:detail", kwargs={"slug": self.survey.slug})
        self.assertRedirects(
            self.client.get("/", HTTP_HOST="survey.test"),
            public_url,
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.get(public_url, HTTP_HOST="survey.test").status_code, 200)
        self.assertEqual(self.client.get("/admin/login/", HTTP_HOST="survey.test").status_code, 200)


@HOSTS
class AdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("admin", "", "test-password")
        self.survey = Survey.objects.create(title="企业调查", slug="business", is_published=True)
        self.question = Question.objects.create(
            survey=self.survey,
            order=1,
            label="公司名称",
            question_type=Question.TEXT,
        )
        self.submission = Submission.objects.create(survey=self.survey)
        Answer.objects.create(
            submission=self.submission,
            question=self.question,
            question_label=self.question.label,
            value="测试公司",
            display_value="测试公司",
        )
        self.client.force_login(self.user)

    def test_admin_search_filter_and_exports(self):
        changelist = reverse("admin:surveys_submission_changelist")
        searched = self.client.get(changelist, {"q": "测试公司"}, HTTP_HOST="survey.test")
        self.assertEqual(searched.status_code, 200)
        self.assertContains(searched, "企业调查")
        filtered = self.client.get(
            changelist,
            {"survey__id__exact": str(self.survey.id)},
            HTTP_HOST="survey.test",
        )
        self.assertEqual(filtered.status_code, 200)
        action_data = {
            "_selected_action": [str(self.submission.id)],
            "index": "0",
        }
        csv_response = self.client.post(
            changelist,
            {**action_data, "action": "export_csv"},
            HTTP_HOST="survey.test",
        )
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("测试公司", csv_response.content.decode("utf-8-sig"))
        xlsx_response = self.client.post(
            changelist,
            {**action_data, "action": "export_excel"},
            HTTP_HOST="survey.test",
        )
        self.assertEqual(xlsx_response.status_code, 200)
        self.assertEqual(xlsx_response.content[:4], b"PK\x03\x04")
        markdown_response = self.client.post(
            changelist,
            {**action_data, "action": "export_markdown"},
            HTTP_HOST="survey.test",
        )
        self.assertEqual(markdown_response.status_code, 200)
        self.assertIn("测试公司", markdown_response.content.decode("utf-8"))
