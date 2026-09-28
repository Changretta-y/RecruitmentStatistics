from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SharingProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid="sharing_assign_avatar")
def assign_avatar(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        SharingProfile.objects.get_or_create(user=instance)
