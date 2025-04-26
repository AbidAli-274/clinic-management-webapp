import json

from channels.generic.websocket import AsyncWebsocketConsumer


class PresenceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "presence_group"

        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_patient_status(self, event):
        message = event["message"]
        pending_sessions = event["pending_sessions"]
        in_progress_sessions = event["in_progress_sessions"]
        pending_consultancies = event["pending_consultancies"]
        in_progress_consultancies = event["in_progress_consultancies"]

        await self.send(
            text_data=json.dumps(
                {
                    "message": message,
                    "pending_sessions": pending_sessions,
                    "in_progress_sessions": in_progress_sessions,
                    "pending_consultancies": pending_consultancies,
                    "in_progress_consultancies": in_progress_consultancies,
                }
            )
        )
