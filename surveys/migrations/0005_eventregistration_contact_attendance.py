from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("surveys", "0004_eventregistration_submission_token")]
    operations = [
        migrations.AddField(
            model_name="eventregistration",
            name="contact_attending",
            field=models.BooleanField(
                blank=True, null=True, verbose_name="联系人本人是否参会"
            ),
        ),
        migrations.AddField(
            model_name="eventregistration",
            name="contact_role",
            field=models.CharField(blank=True, max_length=100, verbose_name="联系人职务"),
        ),
    ]
