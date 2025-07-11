from asyncio import sleep

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
import graphene
from graphql_server.django.views import AsyncGraphQLView

from core.schemas import schema as core_schema
from mailer.schemas import schema as mailer_schema
from mailer.views import email_webhook, get_app_credentials, get_usage, switch_provider


async def arange(n):
    for i in range(n):
        await sleep(0.1)
        yield i


async def am_i_alive(request):
    async for i in arange(10):
        print(i)
    return HttpResponse(status=200)


class Query(core_schema.Query, graphene.ObjectType): ...


class Mutation(core_schema.Mutation, mailer_schema.Mutation, graphene.ObjectType): ...


schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", am_i_alive),
    path("credentials/<str:app_id>", get_app_credentials),
    path("switch_provider/<str:app_id>/<str:provider_name>", switch_provider),
    path("webhook/email/<str:provider_name>/<str:token>", csrf_exempt(email_webhook), name="email_webhook"),
    path("usage/<str:from_address>", get_usage),
    path("graphql/", AsyncGraphQLView.as_view(schema=schema.graphql_schema, graphiql=True)),
    path("", include("django_prometheus.urls")),
]
