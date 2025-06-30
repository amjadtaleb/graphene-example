import asyncio
from django.core.management.base import BaseCommand
from core.models import User, DeployedApp
from core.fields import PlanEnum

from random import choice


plans = [plan.value for plan in PlanEnum]
names = [
    "John",
    "Jane",
    "Bob",
    "Alice",
    "Charlie",
    "David",
    "Eve",
    "Frank",
    "Grace",
    "Hank",
    "Lily",
    "Morgan",
    "Nathan",
    "Olivia",
    "Pete",
    "Quinn",
    "Ryan",
    "Sophia",
    "Tom",
    "Uma",
    "Victor",
    "Wendy",
    "Xander",
    "Yara",
    "Zack",
]
last_names = [
    "Fitzgerald",
    "Shakespere",
    "Goodall",
    "Snowden",
    "Hawking",
    "Huxley",
    "Darwin"
]
app_names = [
    "Fuzzy Stones",
    "Giant Ant",
    "Mighty Mouse",
    "Doom of the Gods",
    "Generation K",
    "Flat World",
    "Mighty Ducks",
    "In the mood for..."
]


def gen_users():
    print("\n Users: ")
    for name in names:
        print(name, end=" | ")
        yield User(username=name.lower(), plan=choice(plans), full_name=f"{name} {choice(last_names)}")

def gen_apps():
    print("\n Apps: ")
    for name in app_names:
        print(name, end=" | ")
        yield DeployedApp(name=name)


def populate_db():
    User.objects.bulk_create(
        gen_users()
        , ignore_conflicts=True
    )
    users = User.objects.all()
    DeployedApp.objects.bulk_create(
        [DeployedApp(owner=choice(users), name=app_name) for app_name in app_names]
        , ignore_conflicts=True
    )


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--rollback", "-r", action="store_true")

    def handle(self, *args, **options):
        if options["rollback"]:
            DeployedApp.objects.all().delete()
            User.objects.all().delete()
        else:
            populate_db()
            print("\nDone")
