from django.db import migrations, models


CANONICAL = {
    "applied",
    "assessment",
    "written_test",
    "first_interview",
    "second_interview",
    "other_interview",
    "hr_interview",
    "rejected",
}


def _scheduled_stage(company, position, shared_stage_model):
    """Map the most advanced legacy schedule to the unified business status."""
    interview_names = {
        "一面": "first_interview",
        "二面": "second_interview",
        "HR 面": "hr_interview",
        "HR面": "hr_interview",
    }
    interviews = list(position.interviews.filter(scheduled_at__isnull=False))
    if any(interview_names.get(item.name) == "hr_interview" for item in interviews) or company.hr_interview_time is not None:
        return "hr_interview"
    if any(item.name not in interview_names for item in interviews) or company.third_interview_time is not None:
        return "other_interview"
    if any(interview_names.get(item.name) == "second_interview" for item in interviews) or company.second_interview_time is not None:
        return "second_interview"
    if any(interview_names.get(item.name) == "first_interview" for item in interviews) or company.first_interview_time is not None:
        return "first_interview"
    if shared_stage_model.filter(
        company_id=company.pk,
        type="written_test",
        scheduled_at__isnull=False,
    ).exists() or company.written_test_time is not None:
        return "written_test"
    if shared_stage_model.filter(
        company_id=company.pk,
        type="assessment",
        scheduled_at__isnull=False,
    ).exists():
        return "assessment"
    return "applied"


def canonical_status(company, position, shared_stage_model):
    status = position.application_status
    if status in CANONICAL:
        return status
    if status in {"offer", "withdrawn"}:
        return "rejected"
    if status == "in_progress":
        return _scheduled_stage(company, position, shared_stage_model)
    return "applied"


def migrate_statuses(apps, schema_editor):
    Company = apps.get_model("applications", "JobApplication")
    Position = apps.get_model("applications", "ApplicationPosition")
    SharedStage = apps.get_model("applications", "SharedStage")
    alias = schema_editor.connection.alias
    counts = {}

    for company in Company.objects.using(alias).all().order_by("pk"):
        positions = list(Position.objects.using(alias).filter(company_id=company.pk).order_by("pk"))
        for position in positions:
            old_status = position.application_status
            new_status = canonical_status(company, position, SharedStage.objects.using(alias))
            counts[(old_status, new_status)] = counts.get((old_status, new_status), 0) + 1
            if old_status != new_status:
                Position.objects.using(alias).filter(pk=position.pk).update(application_status=new_status)

        first = Position.objects.using(alias).filter(company_id=company.pk).order_by("pk").first()
        if first is not None and company.application_status != first.application_status:
            Company.objects.using(alias).filter(pk=company.pk).update(application_status=first.application_status)

    summary = ", ".join(
        f"{old}->{new}:{count}"
        for (old, new), count in sorted(counts.items())
    ) or "none"
    print(f"APP-010 migration: position status counts ({summary}); schedules and durations preserved.")


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0004_applicationposition_positioninterview_sharedstage_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="jobapplication",
            name="application_status",
            field=models.CharField(
                choices=[
                    ("applied", "投递"),
                    ("assessment", "测评"),
                    ("written_test", "笔试"),
                    ("first_interview", "一面"),
                    ("second_interview", "二面"),
                    ("other_interview", "其他轮次"),
                    ("hr_interview", "HR面"),
                    ("rejected", "拒绝"),
                ],
                default="applied",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="applicationposition",
            name="application_status",
            field=models.CharField(
                choices=[
                    ("applied", "投递"),
                    ("assessment", "测评"),
                    ("written_test", "笔试"),
                    ("first_interview", "一面"),
                    ("second_interview", "二面"),
                    ("other_interview", "其他轮次"),
                    ("hr_interview", "HR面"),
                    ("rejected", "拒绝"),
                ],
                default="applied",
                max_length=30,
            ),
        ),
    ]
