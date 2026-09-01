import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("surveys", "0002_flatten_default_service_scope_question")]
    operations = [
        migrations.CreateModel(
            name="EventRegistration",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("company_name", models.CharField(max_length=200, verbose_name="公司名称")),
                ("contact_name", models.CharField(max_length=80, verbose_name="联系人")),
                ("contact_phone", models.CharField(db_index=True, max_length=20, verbose_name="联系电话")),
                ("city", models.CharField(max_length=80, verbose_name="公司所在城市")),
                ("project_count", models.CharField(choices=[("within_5", "5 个以内"), ("6_15", "6-15 个"), ("16_30", "16-30 个"), ("over_30", "30 个以上")], max_length=20, verbose_name="外部合作项目数量")),
                ("lawsuit_count", models.CharField(choices=[("none", "0 个"), ("1_3", "1-3 个"), ("4_10", "4-10 个"), ("over_10", "10 个以上"), ("unknown", "未统计")], max_length=20, verbose_name="过往涉诉/被追索案件数量")),
                ("priority_issues", models.JSONField(default=list, verbose_name="希望重点解答的问题")),
                ("other_risk", models.TextField(blank=True, verbose_name="其他急需解决的风险")),
                ("source_channel", models.CharField(choices=[("douyin", "抖音"), ("channels", "视频号"), ("xiaohongshu", "小红书"), ("moments", "朋友圈"), ("referral", "朋友转介绍"), ("other", "其他")], max_length=20, verbose_name="了解活动的渠道")),
                ("submitted_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="提交时间")),
                ("feishu_notified_at", models.DateTimeField(blank=True, null=True, verbose_name="飞书通知时间")),
                ("feishu_error", models.TextField(blank=True, verbose_name="飞书通知状态说明")),
            ],
            options={"verbose_name": "活动报名", "verbose_name_plural": "活动报名", "ordering": ("-submitted_at",)},
        ),
        migrations.CreateModel(
            name="Attendee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, verbose_name="姓名")),
                ("role", models.CharField(max_length=100, verbose_name="职务")),
                ("phone", models.CharField(db_index=True, max_length=20, verbose_name="联系电话")),
                ("registration", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attendees", to="surveys.eventregistration", verbose_name="报名记录")),
            ],
            options={"verbose_name": "参会人员", "verbose_name_plural": "参会人员", "ordering": ("id",)},
        ),
    ]
