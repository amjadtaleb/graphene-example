from enum import Enum
from logging import getLogger

from django.conf import settings
import httpx


class ProviderEmailEvent(Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCE = "bounce"  # not an event per se, SMTP2GO likes to mix things up
    SOFT_BOUNCE = "soft_bounce"
    HARD_BOUNCE = "hard_bounce"
    UNSUBSCRIBE = "unsubscribe"
    SPAM = "spam"


logger = getLogger(__name__)


class SMTPUserNotFound(Exception): ...


class SMTPServiceProvider:
    """Inherith this class to implement a specific SMTP provider"""

    providers = {}
    webhook_token = None

    @classmethod
    def register(cls, **kwargs):
        cls.providers.update(kwargs)

    @classmethod
    def get_provider_class(cls, provider: str):
        return cls.providers[provider]

    @classmethod
    def get_provider(cls, provider: str):
        return cls.get_provider_class(provider)(webhook_token=settings.STMP_PROVIDERS[provider].webhook_token)

    def get_credentials_request(self, user_id: str):
        return (
            self.method,
            self.users_url(user_id),
            self.gen_headers(),
            self.gen_body(user_id),
        )

    def gen_headers(self):
        raise NotImplementedError

    def gen_body(self):
        raise NotImplementedError

    def parse_credentials(self, response):
        raise NotImplementedError

    def parse_webhook(self, data: dict):
        raise NotImplementedError

    async def get_user_credentials(self, user_id: str) -> dict[str, str]:
        method, url, headers, body = self.get_credentials_request(user_id)
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
            )
            if resp.status_code != 200:
                logger.error(resp.json())
                if resp.status_code == 404:
                    raise SMTPUserNotFound("User not found")
                else:
                    raise ValueError("Error looking up user credentials", resp.status_code, self.__class__)
            return self.parse_credentials(resp.json(), user_id)

    async def create_smtp_user(self, user_id: str):
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method=self.method,
                url=self.users_url(user_id),
                headers=self.gen_headers(),
                json=self.gen_body(user_id),
            )
            if resp.status_code != 200:
                logger.error(resp.json())
                raise ValueError("Error looking up user credentials", resp.status_code, self.__class__)
            return self.parse_credentials(resp.json(), user_id)
