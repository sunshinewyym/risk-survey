from django.db import migrations


def use_flat_choices(apps, schema_editor):
    Question = apps.get_model("surveys", "Question")
    Question.objects.filter(
        survey__slug="joint-project-risk-diagnosis",
        order=43,
    ).update(question_type="radio")


def restore_dropdown(apps, schema_editor):
    Question = apps.get_model("surveys", "Question")
    Question.objects.filter(
        survey__slug="joint-project-risk-diagnosis",
        order=43,
    ).update(question_type="select")


class Migration(migrations.Migration):
    dependencies = [("surveys", "0001_initial")]
    operations = [migrations.RunPython(use_flat_choices, restore_dropdown)]
