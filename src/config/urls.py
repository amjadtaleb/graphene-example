from asyncio import sleep

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from graphql_server.django.views import AsyncGraphQLView

from core.schemas import schema


async def arange(n):
    for i in range(n):
        await sleep(0.1)
        yield i


async def am_i_alive(request):
    async for i in arange(10):
        print(i)
    return HttpResponse(status=200)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", am_i_alive),
    path("graphql/", AsyncGraphQLView.as_view(schema=schema.graphql_schema, graphiql=True)),
    path("", include("django_prometheus.urls")),
]
