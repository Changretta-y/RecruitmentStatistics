from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobapplication",
            name="application_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
    ]
