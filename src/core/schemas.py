from logging import getLogger

import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from mailer.schemas import AppEmails, UserEmails
from mailer.models import EmailProvider

from . import models
from .custom_node import CustomNode
from .dataloaders import AppLoader, EXCLUDE_USER_FIELDS, UserLoader
from .fields import PlanEnum

logger = getLogger(__name__)


class App(DjangoObjectType):
    id = graphene.ID(required=True)
    emails = graphene.Field(AppEmails)

    class Meta:
        model = models.DeployedApp
        interfaces = (CustomNode,)

    def resolve_id(self, info):  # this feels too hacky
        return CustomNode.to_global_id("DeployedApp", self.pk)

    async def resolve_owner(self, info):
        return await UserLoader().load(self.owner_id)

    async def resolve_emails(self, info):
        return self


class AppConnection(relay.Connection):
    class Meta:
        node = App


class User(DjangoObjectType):
    plan = graphene.Field(graphene.Enum.from_enum(PlanEnum, name="Plan"))
    apps = relay.ConnectionField(AppConnection)
    emails = graphene.Field(UserEmails)

    def resolve_plan(self, info):
        return self.plan

    class Meta:
        model = models.User
        exclude_fields = [
            *EXCLUDE_USER_FIELDS,
        ]
        include_fields = ["id", "username", "plan"]
        interfaces = (CustomNode,)
        convert_choices_to_enum = True

    async def resolve_apps(root, info):
        return await AppLoader().load_many([app async for app in root.apps.values_list("id", flat=True)])

    async def resolve_emails(self, info):
        return self


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
        uid = CustomNode.from_global_id(id)[1]
        count = await models.User.objects.filter(id=uid).aupdate(plan=PlanEnum.PRO.value)
        if count > 0:
            # TODO: try to do this without importing mailer models
            await EmailProvider.objects.filter(app__owner_id=uid).aupdate(maxed_quota_for=None)
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
