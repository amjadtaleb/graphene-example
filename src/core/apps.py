from django.apps import AppConfig
from psycopg.types.enum import register_enum, EnumInfo
import psycopg
from .fields import PlanEnum
from django.conf import settings


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Registering the PlanEnum has to be done synchronously
        # we cannot not use the django connection here
        conn = psycopg.connect(
            host=settings.DATABASES["default"]["HOST"],
            port=settings.DATABASES["default"]["PORT"],
            user=settings.DATABASES["default"]["USER"],
            password=settings.DATABASES["default"]["PASSWORD"],
            dbname=settings.DATABASES["default"]["NAME"],
        )

        if info := EnumInfo.fetch(conn, "plan"):
            register_enum(info, conn, PlanEnum)
