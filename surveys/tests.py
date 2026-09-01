from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from html import unescape
from unittest.mock import patch

from .models import Answer, Attendee, EventRegistration, Question, Submission, Survey


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
        self.assertEqual(
            self.client.get(reverse("surveys:default_survey"), HTTP_HOST="survey.test").status_code,
            200,
        )
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


@HOSTS
class EventRegistrationTests(TestCase):
    def registration_data(self):
        return {
            "company_name": "广州示例建设有限公司",
            "contact_name": "张三",
            "contact_phone": "13800138000",
            "city": "广州",
            "project_count": "6_15",
            "lawsuit_count": "1_3",
            "priority_issues": ["management_fee", "project_review"],
            "other_risk": "希望了解存量项目整改方案",
            "source_channel": "channels",
            "attendees-TOTAL_FORMS": "2",
            "attendees-INITIAL_FORMS": "0",
            "attendees-MIN_NUM_FORMS": "1",
            "attendees-MAX_NUM_FORMS": "1000",
            "attendees-0-name": "张三",
            "attendees-0-role": "负责人",
            "attendees-0-phone": "13800138000",
            "attendees-1-name": "李四",
            "attendees-1-role": "法务经理",
            "attendees-1-phone": "13900139000",
        }

    def test_registration_requires_csrf_saves_attendees_and_notifies(self):
        client = Client(enforce_csrf_checks=True, HTTP_HOST="survey.test")
        url = reverse("surveys:event_registration")
        page = client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "总包反背锅行动 001")
        self.assertContains(page, "项目是他的，责任为什么是你的？")
        self.assertContains(page, "用于现场内容深浅调节与客户分层，数据仅内部使用")
        self.assertContains(page, "可多选，建议最多选择 3 项")
        self.assertContains(page, "一片叶律师 ｜ 工程风险观察局 · 总包反背锅行动 001")
        page_text = unescape(page.content.decode("utf-8"))
        for _, label in EventRegistration.ISSUE_CHOICES:
            self.assertIn(label, page_text)
        self.assertEqual(client.post(url, self.registration_data()).status_code, 403)
        data = self.registration_data()
        data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        with patch(
            "surveys.views.send_registration_notification", return_value=(True, "")
        ) as notify:
            response = client.post(url, data)
        self.assertRedirects(
            response,
            reverse("surveys:event_registration_thanks"),
            fetch_redirect_response=False,
        )
        registration = EventRegistration.objects.get()
        self.assertEqual(registration.attendees.count(), 2)
        self.assertIsNotNone(registration.feishu_notified_at)
        notify.assert_called_once_with(registration)
        success_page = client.get(reverse("surveys:event_registration_thanks"))
        self.assertContains(success_page, "报名信息已收到")
        self.assertNotContains(success_page, "问卷摘要")
        self.assertNotContains(success_page, "13900139000")

    def test_at_most_three_priority_issues(self):
        data = self.registration_data()
        data["priority_issues"] = [
            "cooperation_model",
            "management_fee",
            "fees_and_tax",
            "project_review",
        ]
        response = self.client.post(
            reverse("surveys:event_registration"), data, HTTP_HOST="survey.test"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "建议最多选择 3 项，请留下您最急需的问题")
        self.assertFalse(EventRegistration.objects.exists())

    def test_registration_admin_has_statistics_and_markdown_export(self):
        user = get_user_model().objects.create_superuser("registration-admin", "", "password")
        registration = EventRegistration.objects.create(
            company_name="统计测试公司",
            contact_name="王五",
            contact_phone="13700137000",
            city="深圳",
            project_count="within_5",
            lawsuit_count="none",
            priority_issues=["project_review"],
            source_channel="referral",
        )
        Attendee.objects.create(
            registration=registration,
            name="王五",
            role="总经理",
            phone="13700137000",
        )
        self.client.force_login(user)
        changelist = reverse("admin:surveys_eventregistration_changelist")
        page = self.client.get(changelist, HTTP_HOST="survey.test")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "报名公司")
        self.assertContains(page, "朋友转介绍")
        response = self.client.post(
            changelist,
            {
                "_selected_action": [str(registration.id)],
                "index": "0",
                "action": "export_registration_markdown",
            },
            HTTP_HOST="survey.test",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("统计测试公司", response.content.decode("utf-8"))
