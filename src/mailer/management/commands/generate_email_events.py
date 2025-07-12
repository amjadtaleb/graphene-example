from datetime import datetime, timedelta
import random
from string import ascii_letters, digits

from django.core.management.base import BaseCommand
from django.utils import timezone as dj_tz

from mailer.models import EmailEvent

alpha_numeric = ascii_letters + digits
RANDOM_ID_LENGTH = 24

FROMS = [
    "nice.person@nicedomain.com",
    "sender.1@nicedomain.com",
    "sender.2@nicedomain.com",
    "sender.3@nicedomain.com",
    "sender.anonymous@secretdomain.com",
]
RECIPIENTS = [
    "test-1@example.com",
    "test-2@example.com",
    "test-3@example.com",
    "test-4@example.com",
    "test-5@example.com",
    "test-6@example.com",
    "test-7@example.com",
    "test-8@example.com",
    "test-9@example.com",
    "test-10@example.com",
]


def generate(alphabet: str, size: int) -> str:
    return "".join(random.choice(alphabet) for _ in range(size))


def gen_events(n):
    for i in range(n):
        message_id = generate(alphabet=alpha_numeric, size=RANDOM_ID_LENGTH)
        send_time = dj_tz.make_aware(datetime.now() - timedelta(seconds=random.randint(0, 3 * 30 * 24 * 60 * 60)))
        event_time = send_time + timedelta(seconds=random.randint(5, 15))
        next_event = random.choice(["delivered", "hard_bounce", "soft_bounce"])
        next_event_time = send_time + timedelta(seconds=random.randint(15, 15 * 60))
        from_address = random.choice(FROMS)
        recipients = random.sample(RECIPIENTS, random.randint(1, 3))
        reason = (
            None
            if not next_event.endswith("bounce")
            else random.choice(["Host or domain name not found", "User unknown", "Some random shit"])
        )
        provider_id = random.randint(1, 2)
        # sent event
        yield (
            "sent",
            send_time,
            event_time,
            message_id,
            from_address,
            recipients,
            provider_id,
            reason,
        )
        # next event
        yield (
            next_event,
            send_time,
            next_event_time,
            message_id,
            from_address,
            recipients,
            provider_id,
            reason,
        )


def gen_events_bulk(n):
    EmailEvent.objects.bulk_create(
        [
            EmailEvent(
                event=event,
                event_time=event_time,
                send_time=send_time,
                message_id=message_id,
                from_address=from_address,
                recipients=recipients,
                provider_id=provider_id,
                reason=reason,
            )
            for (
                event,
                send_time,
                event_time,
                message_id,
                from_address,
                recipients,
                provider_id,
                reason,
            ) in gen_events(n)
        ]
    )


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--count", "-c", type=int, default=1000)

    def handle(self, *args, **options):
        BULK_COUNT = 100
        total = options["count"]
        rounds, final = divmod(total, BULK_COUNT)
        counter = 0
        print("Generating events...")
        for i in range(rounds):
            gen_events_bulk(BULK_COUNT)
            counter += BULK_COUNT
            print(f"\rGenerated events {counter}", end="")

        gen_events_bulk(final)
        print(f"\rGenerated {counter + final} events")
        print()
