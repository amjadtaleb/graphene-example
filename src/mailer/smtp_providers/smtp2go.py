from datetime import datetime
from logging import getLogger

from django.conf import settings

from .smtp_provider import ProviderEmailEvent, SMTPServiceProvider, SMTPUserNotFound

logger = getLogger(__name__)


class SMTP2GoProvider(SMTPServiceProvider):
    ALL_EVENTS = {
        "processed": ProviderEmailEvent.SENT.value,
        "delivered": ProviderEmailEvent.DELIVERED.value,
        "bounce": ProviderEmailEvent.BOUNCE.value,
        "unsubscribe": ProviderEmailEvent.UNSUBSCRIBE.value,
        "spam": ProviderEmailEvent.SPAM.value,
    }

    def __init__(self, webhook_token: str):
        self.method = "POST"
        self.webhook_token = webhook_token

    def users_url(self, *_):
        return "https://api.smtp2go.com/v3/users/smtp/view"

    def gen_headers(self):
        logger.warning(settings.STMP_PROVIDERS["smtp2go"].api_token)
        return {
            "Content-Type": "application/json",
            "X-Smtp2go-Api-Key": settings.STMP_PROVIDERS["smtp2go"].api_token,
            "accept": "application/json",
        }

    def gen_body(self, user_id: str) -> dict:
        return {"username": user_id}

    def parse_credentials(self, response: dict, user_id: str) -> dict:
        """This provider does not give a single value when a user is found, instead it gives a
        list of matching values, even when the match is partial
        so looking up user_1 will return user_1 and user_11...
        """
        if "error" in response["data"]:
            logger.warning(response["data"]["error_code"] + " " + response["data"]["error"])
            raise ValueError("Error in quering user credentials", self.__class__)

        if len(response["data"]["results"]) > 0:
            try:
                user = next(filter(lambda x: x["username"] == user_id, response["data"]["results"]))
            except StopIteration:
                raise SMTPUserNotFound("User not found with", self.__class__)

            if user["sending_allowed"]:
                return {
                    "username": user["username"],
                    "password": user["email_password"],
                }
            raise ValueError("User not enabled with", self.__class__)
        raise SMTPUserNotFound("User not found with", self.__class__)

    @classmethod
    def parse_webhook(cls, payload: dict):
        if payload["event"] in cls.ALL_EVENTS:
            event = cls.ALL_EVENTS[payload["event"]]  # map the event
            if event == "bounce":  # prefix the bounce event with the bounce type
                event = f"""{payload["bounce"]}_{event}"""
            return {
                "event": event,
                "event_time": datetime.fromisoformat(payload["time"]),
                "send_time": datetime.fromisoformat(payload["sendtime"]),
                "message_id": payload["email_id"],  # The unique id from the sender.
                "username": payload["auth"],
                "from_address": payload["from_address"],
                "recipients": payload.get("recipients") or [payload.get("rcpt")],
                "reason": payload.get("message"),  # the error message we got (where available).
            }
