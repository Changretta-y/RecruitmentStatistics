from django.conf import settings
from django.db import models


class PromptInitialization(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="prompt_initialization")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "prompt_initializations"


class Prompt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="prompts")
    title = models.CharField(max_length=100)
    content = models.TextField(max_length=10000)
    is_preset = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "prompts"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["user", "title"], name="prompt_user_title_idx")]
