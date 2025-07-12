from datetime import datetime
from logging import getLogger
from typing import Optional

from asgiref.sync import sync_to_async
from django.core.mail import EmailMultiAlternatives
from django.core.mail import get_connection
import graphene
from graphene import relay

from core.custom_node import CustomNode
from mailer.dataloaders import AppEmailLoader, AppEmailTotalLoader

from . import models
from .smtp_providers import SMTPServiceProvider, SMTPUserNotFound
from .utils import get_smtp_user_config


logger = getLogger(__name__)


class DateBin(graphene.Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class EmailStats(graphene.ObjectType):
    total = graphene.Int()
    failed = graphene.Int()
    rejected = graphene.Int()
    sent = graphene.Int()


class Usage(graphene.ObjectType):
    timestamp = graphene.Date()
    emails = graphene.Field(EmailStats)


class UserEmails(graphene.ObjectType):
    sent_emails_count = graphene.Int()
    usage = graphene.List(Usage, group_by=DateBin(required=True), time_window=graphene.List(graphene.Date))

    async def resolve_sent_emails_count(parent, info):
        values = await AppEmailTotalLoader().load_many(
            [app_id async for app_id in parent.apps.values_list("pk", flat=True)]
        )
        return sum(values)

    async def resolve_usage(parent, info, group_by, time_window: Optional[list[datetime]] = None):
        if time_window is None:  # a python gatcha
            time_window = []
        app_ids = await sync_to_async(list)(parent.apps.values_list("pk", flat=True))
        senders = await sync_to_async(set)(
            models.EmailProvider.objects.filter(app_id__in=app_ids).values_list("from_address", flat=True)
        )
        if senders:
            return await AppEmailLoader().load((tuple(senders), group_by.value, *time_window))


class AppEmails(graphene.ObjectType):
    total_emails_count = graphene.Int()
    usage = graphene.List(Usage, group_by=DateBin(required=True), time_window=graphene.List(graphene.Date))

    class Meta:
        interfaces = (CustomNode,)

    @classmethod
    def get_node(cls, info, id):
        raise ValueError("get_node")

    async def resolve_total_emails_count(parent, info):
        return await AppEmailTotalLoader().load(parent.pk)

    async def resolve_usage(parent, info, group_by, time_window: Optional[list[datetime]] = None):
        if time_window is None:  # a python gotcha
            time_window = []
        # TODO: switch to app_id, or not?!
        app = await parent.emailprovider_set.filter(active=True).only("from_address").afirst()
        if app:
            return await AppEmailLoader().load(((app.from_address,), group_by.value, *time_window))


class AppEmailsConnection(relay.Connection):
    class Meta:
        node = AppEmails


class getSMTPCredentials(graphene.Mutation):
    class Arguments:
        id = graphene.ID()

    host = graphene.String()
    port = graphene.Int()
    username = graphene.String()
    password = graphene.String()
    provider = graphene.String()

    async def mutate(root, info, id):
        app_id = CustomNode.from_global_id(id)[1]
        return await get_smtp_user_config(app_id)


class sendEmail(graphene.Mutation):
    class Arguments:
        app_id = graphene.String(required=True)
        to = graphene.String(required=True)
        subject = graphene.String(required=True)
        html = graphene.String(required=True)

    successful = graphene.Boolean()

    async def mutate(root, info, app_id, to, subject, html):
        app_id = CustomNode.from_global_id(app_id)[1]
        credentials = await get_smtp_user_config(app_id)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=html,
            from_email=credentials.from_address,
            to=[to],
            connection=get_connection(
                backend="django.core.mail.backends.smtp.EmailBackend",
                host=credentials.host,
                port=credentials.port,
                username=credentials.username,
                password=credentials.password,
                use_tls=True,
            ),
        )

        msg.attach_alternative(html, "text/html")
        msg.send()
        return sendEmail(successful=True)


class Mutation(graphene.ObjectType):
    getSMTP_credentials = getSMTPCredentials.Field()
    send_email = sendEmail.Field()


schema = graphene.Schema(
    mutation=Mutation,
)
