from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="NotificationSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipient_email", models.EmailField(blank=True, default="", max_length=254)),
                ("daily_time", models.TimeField(blank=True, null=True)),
                ("enabled", models.BooleanField(default=False)),
                ("verified", models.BooleanField(default=False)),
                ("timezone", models.CharField(default="Asia/Shanghai", editable=False, max_length=64)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "notification_settings"},
        ),
        migrations.CreateModel(
            name="VerificationToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipient_email", models.EmailField(max_length=254)),
                ("token_digest", models.CharField(max_length=64, unique=True)),
                ("created_at", models.DateTimeField()),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_verification_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "notification_verification_tokens"},
        ),
        migrations.AddIndex(
            model_name="verificationtoken",
            index=models.Index(fields=["user", "recipient_email", "created_at"], name="notificatio_user_id_cb0fb3_idx"),
        ),
    ]
