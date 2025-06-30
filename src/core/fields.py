from django.db import models

class PlanEnum(models.TextChoices):
    HOBBY = "hobby", "Hobby"
    PRO = "pro", "Pro"


class PlanField(models.Field):
    description = "PostgreSQL ENUM type for 'plan'"

    def db_type(self, connection):
        return 'plan'

    def get_prep_value(self, value):
        return str(value) if value is not None else None

    def from_db_value(self, value, expression, connection):
        return value

    def to_python(self, value):
        return value


from graphene_django.converter import convert_django_field, convert_choices_to_named_enum_with_descriptions

@convert_django_field.register(PlanField)
def convert_plan_field_to_enum(field, registry=None):
    return convert_choices_to_named_enum_with_descriptions("Plan", PlanEnum.choices)
