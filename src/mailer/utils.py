import calendar
from datetime import date
import logging
from typing import Optional

from django.conf import settings
from django.db.models import Q
from msgspec import Struct

from . import models
from .smtp_providers import SMTPServiceProvider, SMTPUserNotFound

logger = logging.getLogger(__name__)


class SMTPUserConfig(Struct):
    provider: str
    host: str
    port: int
    username: str
    password: str
    from_address: Optional[str] = None


async def get_smtp_user_config(app_id: str) -> SMTPUserConfig:
    try:
        app_provider_config = await models.EmailProvider.objects.select_related("provider").aget(
            Q(maxed_quota_for__isnull=True) | Q(maxed_quota_for__lt=this_billing_cycle()),
            app_id=app_id,
            active=True,
        )
    except models.EmailProvider.DoesNotExist:
        maybe_the_no_go_app = await models.EmailProvider.objects.filter(active=True, app_id=app_id).afirst()
        if maybe_the_no_go_app is None:
            raise SMTPUserNotFound("This app does not have an active provider")
        if maybe_the_no_go_app.maxed_quota_for >= this_billing_cycle():
            raise SMTPUserNotFound(
                f"This app has reached a quota limit, you cannot send another email until after {maybe_the_no_go_app.maxed_quota_for}"
            )
        logger.error("Unexpected EmailProvider.DoesNotExist reason", extra={"app_id": app_id})
        raise SMTPUserNotFound("App does not exist")  # this should never happen

    external_id = app_provider_config.external_id
    provider = SMTPServiceProvider.get_provider(app_provider_config.provider.name)
    # getting the provider should raise if it was not configured
    credentials = await provider.get_user_credentials(external_id)

    return SMTPUserConfig(
        provider=app_provider_config.provider.name,
        host=settings.STMP_PROVIDERS[app_provider_config.provider.name].smtp_host,
        port=settings.STMP_PROVIDERS[app_provider_config.provider.name].smtp_port,
        username=credentials["username"],
        password=credentials["password"],
        from_address=app_provider_config.from_address,
    )


def this_billing_cycle():
    today = date.today()
    _, last_day_of_month = calendar.monthrange(today.year, today.month)
    return date(today.year, today.month, last_day_of_month)
