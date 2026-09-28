from django.conf import settings
from django.core.checks import Error, register


@register()
def recommendation_configuration_check(app_configs, **kwargs):
    value = getattr(settings, "SHARING_RECOMMENDATION_COUNT", 10)
    if type(value) is not int or not 1 <= value <= 50:
        return [Error("SHARING_RECOMMENDATION_COUNT must be an integer from 1 to 50.", id="sharing.E001")]
    return []
