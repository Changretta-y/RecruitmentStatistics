from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def populate_settings_updated_at(apps, schema_editor):
    settings_model = apps.get_model("notifications", "NotificationSettings")
    settings_model.objects.filter(updated_at__isnull=True).update(updated_at=timezone.now())


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="notificationsettings",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
            preserve_default=False,
        ),
        migrations.RunPython(populate_settings_updated_at, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="notificationsettings",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.CreateModel(
            name="DailyDelivery",
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
                ("delivery_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "待发送"),
                            ("sending", "发送中"),
                            ("accepted", "已接受"),
                            ("failed_retryable", "可重试失败"),
                            ("failed", "终态失败"),
                            ("unknown", "结果不确定"),
                        ],
                        default="pending",
                        max_length=24,
                    ),
                ),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("next_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("error_category", models.CharField(blank=True, default="", max_length=64)),
                ("delivery_id", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "notification_settings",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_deliveries",
                        to="notifications.notificationsettings",
                    ),
                ),
            ],
            options={"db_table": "notification_daily_deliveries"},
        ),
        migrations.AddConstraint(
            model_name="dailydelivery",
            constraint=models.UniqueConstraint(
                fields=("notification_settings", "delivery_date"),
                name="notification_daily_delivery_unique",
            ),
        ),
        migrations.AddIndex(
            model_name="dailydelivery",
            index=models.Index(fields=["delivery_date", "status"], name="notificatio_deliver_5f334f_idx"),
        ),
    ]
