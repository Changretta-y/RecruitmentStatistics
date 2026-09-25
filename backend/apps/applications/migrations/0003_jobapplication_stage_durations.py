from django.db import migrations, models


STAGE_FIELDS = (
    ("ai_interview_time", "ai_interview_duration_minutes"),
    ("written_test_time", "written_test_duration_minutes"),
    ("first_interview_time", "first_interview_duration_minutes"),
    ("second_interview_time", "second_interview_duration_minutes"),
    ("third_interview_time", "third_interview_duration_minutes"),
    ("hr_interview_time", "hr_interview_duration_minutes"),
)


def set_legacy_stage_durations(apps, schema_editor):
    JobApplication = apps.get_model("applications", "JobApplication")
    for time_field, duration_field in STAGE_FIELDS:
        JobApplication.objects.filter(
            **{f"{time_field}__isnull": False, f"{duration_field}__isnull": True}
        ).update(**{duration_field: 60})


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0002_jobapplication_application_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobapplication",
            name="ai_interview_duration_minutes",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="written_test_duration_minutes",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="first_interview_duration_minutes",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="second_interview_duration_minutes",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="third_interview_duration_minutes",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="hr_interview_duration_minutes",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(set_legacy_stage_durations, migrations.RunPython.noop),
    ]
