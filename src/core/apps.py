import asyncio
from logging import getLogger

from asgiref.sync import sync_to_async
from django.apps import AppConfig
from django.db import connection
from psycopg.types.enum import EnumInfo, register_enum

from .fields import PlanEnum

logger = getLogger(__name__)


def do_it():
    with connection.cursor() as cursor:
        conn = cursor.connection
        if info := EnumInfo.fetch(conn, "plan"):
            logger.info(str(info))
            register_enum(info, conn, PlanEnum, mapping=[(plan.name, plan.value) for plan in PlanEnum])
        else:
            logger.warning("Enum 'plan' not found in the database. You need to run the migration.")


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(sync_to_async(do_it)())
            logger.info("Registered 'plan' enum in the running event loop.")
        except RuntimeError:
            # If no running loop, we are in a synchronous context
            do_it()
            logger.info("Registered 'plan' enum in a synchronous context.")
