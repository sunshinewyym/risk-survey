import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Survey",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=200, verbose_name="标题")),
                ("slug", models.SlugField(max_length=100, unique=True, verbose_name="公开地址标识")),
                ("description", models.TextField(blank=True, verbose_name="说明")),
                ("success_message", models.TextField(default="您的问卷已成功提交，感谢您的配合。", verbose_name="提交成功提示")),
                ("is_published", models.BooleanField(default=False, verbose_name="允许公开填写")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={"verbose_name": "问卷", "verbose_name_plural": "问卷", "ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=1, verbose_name="序号")),
                ("section", models.CharField(blank=True, max_length=120, verbose_name="分组标题")),
                ("label", models.CharField(max_length=500, verbose_name="问题")),
                ("help_text", models.TextField(blank=True, verbose_name="补充说明")),
                ("question_type", models.CharField(choices=[("text", "单行文本"), ("textarea", "多行文本"), ("radio", "单选"), ("checkbox", "多选"), ("select", "下拉选项")], max_length=20, verbose_name="类型")),
                ("required", models.BooleanField(default=True, verbose_name="必填")),
                ("options", models.JSONField(blank=True, default=list, verbose_name="选项")),
                ("placeholder", models.CharField(blank=True, max_length=200, verbose_name="输入提示")),
                ("survey", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="surveys.survey", verbose_name="所属问卷")),
            ],
            options={"verbose_name": "问题", "verbose_name_plural": "问题", "ordering": ("survey", "order", "id")},
        ),
        migrations.CreateModel(
            name="Submission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("submitted_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="提交时间")),
                ("survey", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="submissions", to="surveys.survey", verbose_name="问卷")),
            ],
            options={"verbose_name": "提交记录", "verbose_name_plural": "提交记录", "ordering": ("-submitted_at",)},
        ),
        migrations.CreateModel(
            name="Answer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_label", models.CharField(max_length=500, verbose_name="问题快照")),
                ("value", models.JSONField(verbose_name="原始答案")),
                ("display_value", models.TextField(verbose_name="答案")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="answers", to="surveys.question", verbose_name="问题")),
                ("submission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="surveys.submission", verbose_name="提交记录")),
            ],
            options={"verbose_name": "答案", "verbose_name_plural": "答案", "ordering": ("question__order", "id")},
        ),
        migrations.AddConstraint(
            model_name="question",
            constraint=models.UniqueConstraint(fields=("survey", "order"), name="unique_question_order"),
        ),
        migrations.AddConstraint(
            model_name="answer",
            constraint=models.UniqueConstraint(fields=("submission", "question"), name="unique_submission_answer"),
        ),
    ]
