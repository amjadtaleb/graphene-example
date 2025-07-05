from logging import getLogger
from psycopg.types.enum import EnumInfo, register_enum

logger = getLogger(__name__)


def register_db_enum(db_connection, db_enum_name: str, enum_class):
    with db_connection.cursor() as cursor:
        conn = cursor.connection

        if info := EnumInfo.fetch(conn, db_enum_name):
            logger.info(f"Registering {enum_class.__name__}({info})")
            register_enum(info, conn, enum_class, mapping=[(plan.name, plan.value) for plan in enum_class])
        else:
            logger.warning(f"Enum '{db_enum_name}' not found in the database. You need to run the migration.")
