from graphene import relay

from django.core.exceptions import ObjectDoesNotExist

from graphql import GraphQLError

from . import models


class CustomNode(relay.Node):
    USER_ID_PREFIX = "u_"
    APP_ID_PREFIX = "app_"
    APP_EMAILS_ID_PREFIX = "app_emails_"
    # TODO: provide is_app_id and is_user_id methods to complain in queries that mix id types
    # the actual id should be an int so we don't want to get the wrong item because we used
    # the wrong prefix

    class Meta:
        name = "Node"

    @staticmethod
    def to_global_id(type_, id):
        if type_ == "User":
            return f"{CustomNode.USER_ID_PREFIX}{id}"
        elif type_ == "DeployedApp":
            return f"{CustomNode.APP_ID_PREFIX}{id}"
        elif type_ == "AppEmails":
            return f"{CustomNode.APP_EMAILS_ID_PREFIX}{id}"
        else:
            raise GraphQLError("Invalid type")

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
            elif CustomNode.APP_EMAILS_ID_PREFIX.startswith(type_):
                return await models.AppEmails.objects.aget(id=id_)
        except ObjectDoesNotExist:
            return None