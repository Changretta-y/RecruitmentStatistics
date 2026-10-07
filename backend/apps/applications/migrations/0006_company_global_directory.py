import unicodedata

import django.db.models.deletion
from django.db import migrations, models
from django.db.migrations.exceptions import IrreversibleError


def normalize_name(value):
    return unicodedata.normalize("NFKC", str(value or "").strip()).casefold()


def migrate_companies(apps, schema_editor):
    Company = apps.get_model("applications", "Company")
    JobApplication = apps.get_model("applications", "JobApplication")
    Position = apps.get_model("applications", "ApplicationPosition")
    alias = schema_editor.connection.alias

    grouped = {}
    applications = list(
        JobApplication.objects.using(alias).order_by("created_at", "id")
    )
    for application in applications:
        key = normalize_name(application.company_name)
        grouped.setdefault(key, []).append(application)

    merged_rows = 0
    url_candidates = 0
    url_conflicts = 0
    invalid_url_candidates = 0
    for normalized_name, rows in grouped.items():
        display_name = str(rows[0].company_name or "").strip()
        if not display_name:
            display_name = normalized_name[:200] or "未命名公司"

        candidates = []
        for row in rows:
            raw_url = str(row.application_url or "").strip()
            if raw_url:
                candidates.append((row.created_at, row.pk, -1, raw_url))
            for position in Position.objects.using(alias).filter(
                company_id=row.pk
            ).order_by("id"):
                raw_position_url = str(position.application_url or "").strip()
                if raw_position_url:
                    candidates.append(
                        (row.created_at, row.pk, position.pk, raw_position_url)
                    )

        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        valid_candidates = []
        for candidate in candidates:
            url = candidate[3]
            # URLField validation is not a database constraint. Preserve the
            # migration and report malformed legacy values instead of failing
            # the entire non-empty migration.
            if not (url.startswith("http://") or url.startswith("https://")):
                invalid_url_candidates += 1
                continue
            valid_candidates.append(url)
        url_candidates += len(valid_candidates)
        distinct_urls = set(valid_candidates)
        url_conflicts += max(0, len(distinct_urls) - 1)
        recruitment_url = valid_candidates[0] if valid_candidates else None

        company = Company.objects.using(alias).create(
            company_name=display_name[:200],
            normalized_name=normalized_name[:200],
            recruitment_url=recruitment_url,
        )
        earliest = min(row.created_at for row in rows)
        latest = max(row.updated_at for row in rows)
        Company.objects.using(alias).filter(pk=company.pk).update(
            created_at=earliest,
            updated_at=latest,
        )
        for row in rows:
            JobApplication.objects.using(alias).filter(pk=row.pk).update(
                company_id=company.pk
            )
        merged_rows += len(rows) - 1

    print(
        "APP-012 migration: "
        f"companies={len(grouped)} merged_rows={merged_rows} "
        f"url_candidates={url_candidates} url_conflicts={url_conflicts} "
        f"invalid_url_candidates={invalid_url_candidates}; "
        "display name=earliest created_at then old id; URL=created_at, old id, position id."
    )


def reverse_non_empty_guard(apps, schema_editor):
    JobApplication = apps.get_model("applications", "JobApplication")
    Company = apps.get_model("applications", "Company")
    alias = schema_editor.connection.alias
    if JobApplication.objects.using(alias).filter(company_id__isnull=False).exists():
        raise IrreversibleError(
            "APP-012 cannot downgrade non-empty company relationships without a backup; "
            "restore the pre-migration database instead."
        )
    if Company.objects.using(alias).exists():
        raise IrreversibleError(
            "APP-012 cannot downgrade a non-empty global company directory without a backup."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0005_unify_application_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("company_name", models.CharField(max_length=200)),
                (
                    "normalized_name",
                    models.CharField(max_length=200, unique=True),
                ),
                (
                    "recruitment_url",
                    models.URLField(blank=True, max_length=500, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "companies",
                "ordering": ["company_name", "id"],
                "indexes": [
                    models.Index(fields=["company_name"], name="company_name_idx"),
                    models.Index(fields=["created_at"], name="company_created_idx"),
                ],
            },
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="applications",
                to="applications.company",
            ),
        ),
        migrations.RunPython(migrate_companies, reverse_non_empty_guard),
        migrations.RemoveConstraint(
            model_name="jobapplication",
            name="application_unique_company",
        ),
        migrations.AlterField(
            model_name="jobapplication",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="applications",
                to="applications.company",
            ),
        ),
        migrations.AlterField(
            model_name="jobapplication",
            name="company_name",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddConstraint(
            model_name="jobapplication",
            constraint=models.UniqueConstraint(
                fields=("user", "company"),
                name="application_unique_user_company",
            ),
        ),
    ]
