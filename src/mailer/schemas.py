"""
```GraphQL
sendEmail(appId, to, subject, html) { # This should fail if the user has no more credits
  successful
}
```

```GraphQL
getSMTPCredentials(appId) {
    host
    port
    username
    password
    provider
}
```
"""

import graphene


from core.schemas import CustomNode
from . import models
from django.conf import settings
from .smtp_providers import SMTPServiceProvider, SMTPUserNotFound


class getSMTPCredentials(graphene.Mutation):
    class Arguments:
        id = graphene.ID()

    host = graphene.String()
    port = graphene.Int()
    username = graphene.String()
    password = graphene.String()
    provider = graphene.String()

    async def mutate(root, info, id):
        app_id = CustomNode.from_global_id(id)[1]
        try:
            app_provider_config = await models.EmailProvider.actives.select_related("provider").aget(app_id=app_id)
        except models.EmailProvider.DoesNotExist:
            raise SMTPUserNotFound("App is not active or does not have an active provider")

        external_id = app_provider_config.external_id
        provider = SMTPServiceProvider.get_provider(app_provider_config.provider.name)
        # getting the provider should raise if it was not configured
        credentials = await provider.get_user_credentials(external_id)
        return {
            "provider": app_provider_config.provider.name,
            "host": settings.STMP_PROVIDERS[app_provider_config.provider.name].smtp_host,
            "port": settings.STMP_PROVIDERS[app_provider_config.provider.name].smtp_port,
            **credentials,
        }


class sendEmail(graphene.Mutation):
    async def mutate(info):
        return sendEmail(successful=True)


class Mutation(graphene.ObjectType):
    getSMTP_credentials = getSMTPCredentials.Field()
    # send_email = sendEmail.Field()


schema = graphene.Schema(
    mutation=Mutation,
)
