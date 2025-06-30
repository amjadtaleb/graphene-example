import string
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q # noqa
from nanoid import generate
from .fields import PlanEnum, PlanField

alpha_numeric = string.ascii_letters + string.digits
RANDOM_ID_LENGTH = 12

def generate_user_id() -> str:
    while True:
        user_id = generate(alphabet=alpha_numeric, size=RANDOM_ID_LENGTH)
        if not User.objects.filter(id=user_id).exists():
            return user_id


def generate_app_id() -> str:
    while True:
        app_id = generate(alphabet=alpha_numeric, size=RANDOM_ID_LENGTH)
        if not DeployedApp.objects.filter(id=app_id).exists():
            return app_id

class User(AbstractUser):
    
    id = models.CharField(primary_key=True, default=generate_user_id, max_length=RANDOM_ID_LENGTH)
    plan = PlanField(default=PlanEnum.HOBBY.value)

    first_name = None
    last_name = None
    full_name = models.TextField()

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name

    def __str__(self):
        return self.username


class DeployedApp(models.Model):

    id = models.CharField(primary_key=True, default=generate_app_id, max_length=RANDOM_ID_LENGTH)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="apps")
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
