import asyncio
from logging import getLogger

from asgiref.sync import sync_to_async
from django.apps import AppConfig
from django.db import connection

from .fields import PlanEnum
from .utils import register_db_enum

logger = getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        try:
            loop = asyncio.get_running_loop()
            logger.info("Registering PlanEnum in the running event loop.")
            loop.create_task(sync_to_async(register_db_enum)(connection, "plan", PlanEnum))
        except RuntimeError:
            # If no running loop, we are in a synchronous context
            logger.info("Registering PlanEnum in a synchronous context.")
            register_db_enum(connection, "plan", PlanEnum)
