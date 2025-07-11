from datetime import datetime
from logging import getLogger

from django.conf import settings

from .smtp_provider import ProviderEmailEvent, SMTPServiceProvider, SMTPUserNotFound

logger = getLogger(__name__)


class MailersendProvider(SMTPServiceProvider):
    """Unlimited usage of Webhooks and number of SMTP users in professional plan
    https://www.mailersend.com/pricing#compare
    """

    ALL_EVENTS = {
        "sent": ProviderEmailEvent.SENT.value,
        "delivered": ProviderEmailEvent.DELIVERED.value,
        "soft_bounced": ProviderEmailEvent.SOFT_BOUNCE.value,
        "hard_bounced": ProviderEmailEvent.HARD_BOUNCE.value,
        "unsubscribed": ProviderEmailEvent.UNSUBSCRIBE.value,
        "spam_complaint": ProviderEmailEvent.SPAM.value,
    }

    def __init__(self, webhook_token: str):
        self.method = "GET"
        self.webhook_token = webhook_token

    def users_url(self, user_id: str):
        return f"""https://api.mailersend.com/v1/domains/{settings.STMP_PROVIDERS["mailersend"].domain_id}/smtp-users/{user_id}"""

    def gen_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"""Bearer {settings.STMP_PROVIDERS["mailersend"].api_token}""",
            "accept": "application/json",
        }

    def gen_body(self, *_):
        return {}

    def parse_credentials(self, response: dict, user_id: str) -> dict:
        if "message" in response:
            raise SMTPUserNotFound("User not found", self.__class__)
        if response["data"]["enabled"]:
            return {
                "username": response["data"]["username"],
                "password": response["data"]["password"],
            }
        raise ValueError("User not enabled", self.__class__)

    @classmethod
    def parse_webhook(cls, payload: dict):
        if payload["data"].get("object") == "activity" and payload["data"]["type"] in cls.ALL_EVENTS:
            return {
                "event": cls.ALL_EVENTS[payload["data"]["type"]],
                "event_time": datetime.fromisoformat(payload["data"]["created_at"]),
                "send_time": datetime.fromisoformat(payload["data"]["email"]["created_at"]),
                "message_id": payload["data"]["id"],
                "username": payload["data"]["email"]["from"],
                "from_address": payload["data"]["email"]["from"],
                "recipients": [payload["data"]["email"]["recipient"]["email"]],
                "reason": payload["data"]["morph"]["reason"] if payload["data"]["morph"] else None,
            }
