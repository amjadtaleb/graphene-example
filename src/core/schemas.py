import asyncio
from logging import getLogger

from django.core.exceptions import ObjectDoesNotExist
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from . import models
from .dataloaders import AppLoader, EXCLUDE_USER_FIELDS, UserLoader
from .fields import PlanEnum

logger = getLogger(__name__)


class CustomNode(relay.Node):
    USER_ID_PREFIX = "u_"
    APP_ID_PREFIX = "app_"

    class Meta:
        name = "Node"

    @staticmethod
    def to_global_id(type_, id):
        if type_ == "User":
            return f"{CustomNode.USER_ID_PREFIX}{id}"
        elif type_ == "DeployedApp":
            return f"{CustomNode.APP_ID_PREFIX}{id}"
        else:
            raise GraphQLError("Invalid type")
            return f"z_{id}"

    @staticmethod
    def from_global_id(global_id):
        try:
            type_, id_ = global_id.split("_", maxsplit=1)
        except ValueError:
            raise GraphQLError("Invalid global ID")
        return type_, id_

    @staticmethod
    async def get_node_from_global_id(info, global_id, only_type=None):
        type_, id_ = CustomNode.from_global_id(global_id)
        try:
            if CustomNode.USER_ID_PREFIX.startswith(type_):
                return await models.User.objects.aget(id=id_)
            elif CustomNode.APP_ID_PREFIX.startswith(type_):
                return await models.DeployedApp.objects.aget(id=id_)
        except ObjectDoesNotExist:
            return None


class App(DjangoObjectType):
    id = graphene.ID(required=True)

    class Meta:
        model = models.DeployedApp
        filter_fields = {
            "id": ["exact"],
            "name": ["exact", "icontains", "istartswith"],
            "active": ["exact"],
            "owner": ["exact"],
        }
        interfaces = (CustomNode,)

    def resolve_id(self, info):  # this feels too hacky
        return CustomNode.to_global_id("DeployedApp", self.pk)

    async def resolve_owner(self, info):
        loop = asyncio.get_running_loop()
        return await UserLoader(loop=loop).load(self.owner_id)


class AppConnection(relay.Connection):
    class Meta:
        node = App


class User(DjangoObjectType):
    plan = graphene.Field(graphene.Enum.from_enum(PlanEnum, name="Plan"))
    apps = relay.ConnectionField(AppConnection)

    def resolve_plan(self, info):
        return self.plan

    class Meta:
        model = models.User
        filter_fields = {
            "id": ["exact"],
            "username": ["exact"],
            "plan": ["exact"],
        }
        exclude_fields = [
            *EXCLUDE_USER_FIELDS,
        ]
        include_fields = ["id", "username", "plan"]
        interfaces = (CustomNode,)
        convert_choices_to_enum = True

    async def resolve_apps(root, info):
        loop = asyncio.get_running_loop()
        return await AppLoader(loop=loop).load_many([app async for app in root.apps.values_list("id", flat=True)])


class Query(graphene.ObjectType):
    node = CustomNode.Field()
    user = CustomNode.Field(User)
    app = CustomNode.Field(App)

    ## for ease of debugging we could use a list of available users
    users = graphene.List(User)

    async def resolve_users(root, info):
        return [user async for user in models.User.objects.all()]


class UserPlanInput(graphene.InputObjectType):
    id = graphene.ID()
    plan = graphene.Field(graphene.Enum.from_enum(PlanEnum, name="Plan"))


class UpdateUserPlan(graphene.Mutation):
    class Arguments:
        plan_input = UserPlanInput(required=True)

    count = graphene.Int()

    async def mutate(root, info, plan_input):
        changed_count = await models.User.objects.filter(id=CustomNode.from_global_id(plan_input.id)[1]).aupdate(
            plan=plan_input.plan.value
        )
        return UpdateUserPlan(count=changed_count)


class upgradeAccount(graphene.Mutation):
    class Arguments:
        id = graphene.ID()

    ok = graphene.Boolean()

    async def mutate(root, info, id):
        count = await models.User.objects.filter(id=CustomNode.from_global_id(id)[1]).aupdate(plan=PlanEnum.PRO.value)
        return upgradeAccount(ok=count > 0)


class downgradeAccount(graphene.Mutation):
    class Arguments:
        id = graphene.ID()

    ok = graphene.Boolean()

    async def mutate(root, info, id):
        count = await models.User.objects.filter(id=CustomNode.from_global_id(id)[1]).aupdate(plan=PlanEnum.HOBBY.value)
        return downgradeAccount(ok=count > 0)


class Mutation(graphene.ObjectType):
    update_user_plan = UpdateUserPlan.Field()
    upgrade_account = upgradeAccount.Field()
    downgrade_account = downgradeAccount.Field()


schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
)
