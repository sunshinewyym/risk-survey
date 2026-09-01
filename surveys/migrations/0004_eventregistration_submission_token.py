from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("surveys", "0003_eventregistration_attendee")]
    operations = [
        migrations.AddField(
            model_name="eventregistration",
            name="submission_token",
            field=models.UUIDField(
                editable=False, null=True, unique=True, verbose_name="提交凭证"
            ),
        ),
    ]
