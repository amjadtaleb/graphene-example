from datetime import datetime
from typing import Literal, Optional

from asgiref.sync import sync_to_async
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db import transaction
from django.db.models import Count, constraints
import django.db.models.functions as dj_functions

from core.models import DeployedApp


class EmailEventChoices(models.TextChoices):
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    SOFT_BOUNCE = "soft_bounce", "Soft Bounce"
    HARD_BOUNCE = "hard_bounce", "Hard Bounce"
    UNSUBSCRIBE = "unsubscribe", "Unsubscribe"
    SPAM = "spam", "Spam"


class SMTPProvider(models.Model):
    name = models.SlugField(max_length=255)
    verified_domain = models.SlugField(max_length=255)
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class AppEmailActiveProviderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class EmailProvider(models.Model):
    """Link an app to a provider, switch and deactivate when necesary"""

    class Meta:
        constraints = [
            constraints.UniqueConstraint(fields=["app", "provider"], name="unique_app_smtp_provider"),
            constraints.UniqueConstraint(
                fields=["app"],
                name="unique_active_app_smtp_provider",
                condition=models.Q(active=True),
            ),
        ]

    app = models.ForeignKey(DeployedApp, on_delete=models.CASCADE)
    provider = models.ForeignKey(SMTPProvider, on_delete=models.PROTECT)
    external_id = models.CharField(
        max_length=255,
        help_text="Use it to query the provider for the app smtp credentials",
    )
    active = models.BooleanField(default=False)

    objects = models.Manager()
    actives = AppEmailActiveProviderManager()

    def __str__(self):
        return f"{self.app.pk} - {self.provider}"

    @classmethod
    @sync_to_async
    @transaction.atomic
    def switch_provider(cls, app_id: str, to_provider: SMTPProvider):
        # transactions are not really supported in async so we wrap this function with sync_to_async
        # https://docs.djangoproject.com/en/5.2/topics/async/#queries-the-orm
        cls.objects.filter(app_id=app_id).update(active=False)
        cls.objects.filter(app_id=app_id, provider=to_provider).update(active=True)


class AppEmailEventsManager(models.Manager):
    def get_queryset(self, app_id: str):
        return super().get_queryset().filter(app_id=app_id)


class EmailEvent(models.Model):
    TIME_BINS = {"day", "week", "month"}
    BIN_MAKERS = {
        "day": dj_functions.TruncDate,
        "week": dj_functions.TruncWeek,
        "month": dj_functions.TruncMonth,
    }
    """Registry of email events we receive via webhooks from providers
    All fields except provider and webhook_received_at come from the webhook
    """
    provider = models.ForeignKey(SMTPProvider, on_delete=models.PROTECT)
    webhook_received_at = models.DateTimeField(auto_now_add=True, help_text="The time we received the email")

    event = models.CharField(max_length=16, choices=EmailEventChoices.choices, default=EmailEventChoices.SENT)
    event_time = models.DateTimeField(help_text="The time the event was registered by the provider")
    send_time = models.DateTimeField(help_text="The time the email was sent, according to the provider")
    message_id = models.CharField(max_length=255, help_text="The unique id from the sender.")
    from_address = models.EmailField()
    recipients = ArrayField(models.EmailField())

    username = models.CharField(
        max_length=255,
        help_text="Some providers tell use the smtp username",
        null=True,  # mailersend does not provide the sender smtp username but we use the from_address instead
    )

    reason = models.TextField(help_text="Some events might have a reason", null=True)

    def __str__(self):
        return f"{self.event} <{self.from_address}>"

    @classmethod
    async def gen_app_usage(
        cls,
        from_address: str,
        time_bin: Literal["day", "week", "month"],
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ):
        """Generate usage stats for an app in time bins from from_time to to_time
        In a date range from from_time to to_time (exclusive)
        """
        filters = models.Q(from_address=from_address)
        if from_time:
            filters &= models.Q(send_time__gte=from_time)
        if to_time:
            filters &= models.Q(send_time__lt=to_time)

        async for result in (
            cls.objects.filter(filters)
            .annotate(time_bin_start=cls.BIN_MAKERS[time_bin](expression="send_time", output_field=models.DateField()))
            .values("time_bin_start")
            .annotate(
                total=Count("id", filter=models.Q(event="sent")),
                failed=Count("id", filter=models.Q(event__endswith="bounce")),
                rejected=Count(
                    "id", filter=models.Q(event__in=[EmailEventChoices.SPAM, EmailEventChoices.UNSUBSCRIBE])
                ),
                sent=Count("id", filter=models.Q(event=EmailEventChoices.DELIVERED)),
            )
            .order_by("time_bin_start")
        ):
            yield result
