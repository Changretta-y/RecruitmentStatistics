"""Nested flow persistence and the legacy single-position projection."""

from .models import ApplicationPosition, INTERVIEW_NAMES, PositionInterview, SHARED_TYPES, SharedStage

POSITION_FIELDS = ("position_name", "application_status", "application_time", "notes")


def bootstrap_legacy(company):
    if company.positions.exists():
        return
    position = ApplicationPosition.objects.create(
        company=company,
        application_url=getattr(company.company, "recruitment_url", None) or "",
        **{field: getattr(company, field) for field in POSITION_FIELDS},
    )
    for kind in SHARED_TYPES:
        when = getattr(company, kind + "_time", None)
        SharedStage.objects.get_or_create(company=company, type=kind, defaults={"scheduled_at": when, "duration_minutes": getattr(company, kind + "_duration_minutes", None) if when else None})
    for kind, name in INTERVIEW_NAMES.items():
        when = getattr(company, kind + "_time")
        if when:
            PositionInterview.objects.create(position=position, name=name, scheduled_at=when, duration_minutes=getattr(company, kind + "_duration_minutes") or 60)


def sync_projection(company):
    company._prefetched_objects_cache = {}
    first = company.positions.first()
    if first is None:
        return
    values = {field: getattr(first, field) for field in POSITION_FIELDS}
    for kind in ("ai_interview", "written_test"):
        stage = company.shared_stages.filter(type=kind).first()
        values[kind + "_time"] = stage.scheduled_at if stage else None
        values[kind + "_duration_minutes"] = stage.duration_minutes if stage else None
    for kind, name in INTERVIEW_NAMES.items():
        interview = first.interviews.filter(name=name).order_by("scheduled_at", "id").first()
        values[kind + "_time"] = interview.scheduled_at if interview else None
        values[kind + "_duration_minutes"] = interview.duration_minutes if interview else None
    for field, value in values.items():
        setattr(company, field, value)
    company.company_name = company.company.company_name
    company.application_url = company.company.recruitment_url or ""
    company.save()


def sync_legacy_write(company, fields):
    bootstrap_legacy(company)
    first = company.positions.first()
    for field in POSITION_FIELDS:
        if field in fields:
            setattr(first, field, getattr(company, field))
    first.save()
    for kind in ("ai_interview", "written_test"):
        if kind + "_time" in fields or kind + "_duration_minutes" in fields:
            SharedStage.objects.update_or_create(company=company, type=kind, defaults={"scheduled_at": getattr(company, kind + "_time"), "duration_minutes": getattr(company, kind + "_duration_minutes")})
    for kind, name in INTERVIEW_NAMES.items():
        if kind + "_time" in fields or kind + "_duration_minutes" in fields:
            interview = first.interviews.filter(name=name).first()
            when = getattr(company, kind + "_time")
            if interview:
                interview.scheduled_at = when
                interview.duration_minutes = getattr(company, kind + "_duration_minutes")
                interview.save()
            elif when:
                PositionInterview.objects.create(position=first, name=name, scheduled_at=when, duration_minutes=getattr(company, kind + "_duration_minutes"))
    company._prefetched_objects_cache = {}
