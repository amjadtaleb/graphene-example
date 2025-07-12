from logging import getLogger

from asgiref.sync import sync_to_async
from django.db.models import Q
from django.http.response import HttpResponse, JsonResponse
from django.utils import timezone as dj_tz
import msgspec.json

from core import models as core_models

from .models import EmailEvent, EmailEventChoices, EmailProvider, SMTPProvider
from .smtp_providers import SMTPServiceProvider, SMTPUserNotFound


logger = getLogger(__name__)


async def get_app_credentials(request, app_id: str):
    try:
        app_provider_config = await EmailProvider.actives.select_related("provider").aget(app_id=app_id, active=True)
        # select_related(provider) is important: other than being optimal it prevents django from executing a sync query later
    except EmailProvider.DoesNotExist:
        return JsonResponse(status=404, data={"error": "This app does not have an active provider"})

    external_id = app_provider_config.external_id
    provider = SMTPServiceProvider.get_provider(app_provider_config.provider.name)

    try:
        provider_credentials = await provider.get_user_credentials(external_id)
    except SMTPUserNotFound as e:
        return JsonResponse(status=404, data={"error": "no smtp user", "provider": app_provider_config.provider})
    except ValueError as e:
        return JsonResponse(status=400, data={"error": str(e)})

    return JsonResponse(status=200, data=provider_credentials)


async def email_webhook(request, provider_name: str, token: str):
    try:
        provider_handler = SMTPServiceProvider.get_provider(provider_name)
    except KeyError:
        logger.warning("Invalid provider", extra={"provider": provider_name})
        return JsonResponse(status=400, data={"error": "Invalid provider"})
    if provider_handler.webhook_token != token:
        logger.warning("Invalid token", extra={"provider": provider_name, "token": token})
        return JsonResponse(status=400, data={"error": "Invalid token"})

    provider = await SMTPProvider.objects.only("id").aget(name=provider_name)
    data = msgspec.json.decode(request.body)
    try:
        if webhook_data := provider_handler.parse_webhook(data):
            new_event = await EmailEvent.objects.acreate(
                provider_id=provider.id,
                event=webhook_data["event"],
                event_time=webhook_data["event_time"],
                send_time=webhook_data["send_time"],
                message_id=webhook_data["message_id"],
                username=webhook_data["username"],
                from_address=webhook_data["from_address"],
                recipients=webhook_data["recipients"],
                reason=webhook_data["reason"],
            )
            logger.info("Email webhook", extra={"provider": provider_name, "event": webhook_data["event"]})

            # Check if the email was sent by a hobby user, and validate their quota
            if new_event.event == EmailEventChoices.SENT.value:
                # This is a:
                # 1- SENT event
                # 2- from some app owned by user with a hobby plan
                hobby_sender_app_ids = await sync_to_async(list)(
                    EmailProvider.objects.filter(
                        from_address=new_event.from_address, app__owner__plan=core_models.PlanEnum.HOBBY.value
                    )
                    .distinct()
                    .values_list("app_id", "from_address")
                )
                if hobby_sender_app_ids:
                    # 3- and there is another event from any of this user's apps in the same billing cycle
                    now = dj_tz.datetime.now()
                    if await EmailEvent.objects.filter(
                        ~Q(pk=new_event.pk),
                        send_time__gte=dj_tz.datetime(now.year, now.month, 1),
                        send_time__lte=now,
                        from_address__in=[i[1] for i in hobby_sender_app_ids],
                    ).aexists():
                        #  mark all this user apps as maxed_quota
                        await EmailProvider.objects.filter(app_id__in=[i[0] for i in hobby_sender_app_ids]).aupdate(
                            maxed_quota=True
                        )
                        # ideally we should also pause/disable all the smtp users of these hobby_sender_app_ids, till next month
            return JsonResponse(status=200, data={"success": True})
        return JsonResponse(status=200, data={"message": "Not important"})
    except Exception as e:
        logger.error(
            str(e),
            extra={"webhook": provider_handler.parse_webhook(data), "provider": provider_name},
            exc_info=True,
        )
        return JsonResponse(status=200, data={"error": "Invalid webhook data"})


async def get_usage(request, from_address: str):
    date_bin = request.GET.get("time_bin", "month")
    time_window = {}  # it makes more sense to call this a date window and the params from_date and to_date
    if from_time_str := request.GET.get("from_time"):
        time_window["from_time"] = dj_tz.make_aware(dj_tz.datetime.fromisoformat(from_time_str))
    if to_time_str := request.GET.get("to_time"):
        time_window["to_time"] = dj_tz.make_aware(dj_tz.datetime.fromisoformat(to_time_str))

    response = [i async for i in EmailEvent.gen_usage(from_address, date_bin, **time_window)]
    return HttpResponse(msgspec.json.encode(response), content_type="application/json")


async def switch_provider(request, app_id: str, provider_name: str):
    try:
        provider = await SMTPProvider.objects.only("id").aget(name=provider_name)
    except SMTPProvider.DoesNotExist:
        return JsonResponse(status=404, data={"error": "Invalid provider"})
    await EmailProvider.switch_provider(app_id, provider)
    return JsonResponse(status=200, data={"success": True})
