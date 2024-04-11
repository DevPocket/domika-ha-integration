# notifier_ios


import traceback
import sys
import asyncio
import aioapns
from . import push_logger


class Notifier_ios:
    apns = None
    loop = None

    def __init__(self, client_cert_uri, loop, use_sandbox):
        if loop is not None:
            self.loop = loop
            asyncio.set_event_loop(self.loop)

        self.apns = aioapns.APNs(
            key = client_cert_uri,
            key_id = "2V43S8PRK7",
            team_id = "R6R7D9LUCJ",
            topic = "com.devpocket.test.jester",  # Bundle ID
            use_sandbox = use_sandbox
        )


    async def apns_send_notification(self, token, data, callback):
        request = aioapns.NotificationRequest(
            device_token = token,
            message = {
                "aps": {
                    "alert": data,
                    "mutable-content": 1
                },
                "data": data
            }
        )
        res = await self.apns.send_notification(request)
        push_logger.log_debug(f"###### PUSH SENT apns_send_notification, status: {res.status}")
        callback(token, res.status)


    def send_push_ios(self, token, data, callback):
        try:
            push_logger.log_debug(f"### STARTED send_push_ios for {token}: {data}")
            if self.loop is not None:
                asyncio.run_coroutine_threadsafe(
                    self.apns_send_notification(token, data, callback), self.loop
                )
            else:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.apns_send_notification(token, data, callback))
                # print("###### Not sending this push to prevent too many pushes sent")
        except:
            push_logger.log_error(f"ERROR >>> Notifier traceback: {traceback.format_exception(*sys.exc_info())}")
