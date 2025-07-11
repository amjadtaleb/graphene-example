from aiodataloader import DataLoader

from . import models


EXCLUDE_USER_FIELDS = [
    "password",
    "is_superuser",
    "is_staff",
    "is_active",
    "date_joined",
    "last_login",
    "email",
]


class UserLoader(DataLoader):
    async def batch_load_fn(self, keys):
        users = {user.id: user async for user in models.User.objects.defer(*EXCLUDE_USER_FIELDS).filter(id__in=keys)}
        return [users.get(user_id) for user_id in keys]


class AppLoader(DataLoader):
    async def batch_load_fn(self, keys):
        apps = {app.id: app async for app in models.DeployedApp.objects.filter(id__in=keys)}
        return [apps.get(app_id) for app_id in keys]
