from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="PromptInitialization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="prompt_initialization", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "prompt_initializations"},
        ),
        migrations.CreateModel(
            name="Prompt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=100)),
                ("content", models.TextField(max_length=10000)),
                ("is_preset", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prompts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "prompts", "ordering": ["created_at", "id"]},
        ),
        migrations.AddIndex(
            model_name="prompt",
            index=models.Index(fields=["user", "title"], name="prompt_user_title_idx"),
        ),
    ]
