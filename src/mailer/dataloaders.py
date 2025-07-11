from aiodataloader import DataLoader

from . import models


class AppEmailLoader(DataLoader):
    async def batch_load_fn(self, keys):
        res = {
            from_address: [i async for i in models.EmailEvent.gen_usage(from_address, time_bin, *time_window)]
            for from_address, time_bin, *time_window in keys
        }
        return [res.get(key) for key, *_ in keys]


class AppEmailTotalLoader(DataLoader):
    async def batch_load_fn(self, keys):
        res = {}
        for app_id in keys:
            app = await models.EmailProvider.objects.filter(app_id=app_id).only("from_address").afirst()
            res[app_id] = await models.EmailEvent.objects.filter(
                from_address=app.from_address, event=models.EmailEventChoices.SENT
            ).acount()
        return [res.get(key) for key in keys]
