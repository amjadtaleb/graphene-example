from .mailersend import MailersendProvider
from .smtp2go import SMTP2GoProvider
from .smtp_provider import SMTPServiceProvider, SMTPUserNotFound  # noqa: F401


SMTPServiceProvider.register(
    smtp2go=SMTP2GoProvider,
    mailersend=MailersendProvider,
)
