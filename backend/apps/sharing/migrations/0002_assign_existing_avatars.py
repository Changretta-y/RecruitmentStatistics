import secrets

from django.conf import settings
from django.db import migrations


def assign_existing_avatars(apps, schema_editor):
    user_app, user_model = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(user_app, user_model)
    Profile = apps.get_model("sharing", "SharingProfile")
    database = schema_editor.connection.alias
    avatars = tuple(f"avatar-{index:02d}" for index in range(1, 9))
    batch = []
    for user_id in User.objects.using(database).values_list("id", flat=True).iterator(chunk_size=1000):
        batch.append(Profile(user_id=user_id, avatar=secrets.choice(avatars)))
        if len(batch) == 1000:
            Profile.objects.using(database).bulk_create(batch, ignore_conflicts=True)
            batch.clear()
    if batch:
        Profile.objects.using(database).bulk_create(batch, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [("sharing", "0001_initial")]
    operations = [migrations.RunPython(assign_existing_avatars, migrations.RunPython.noop)]
