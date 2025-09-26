import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Notifica todos que a sala será fechada
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room_closed",
                "message": "A sala foi encerrada. Voltando para a espera..."
            }
        )
        await self.close_room(self.room_id)
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @sync_to_async
    def close_room(self, room_id):
        from .models import ChatRoom
        try:
            room = ChatRoom.objects.get(id=room_id)
            room.delete()
        except ChatRoom.DoesNotExist:
            pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "user_typing", "user": self.channel_name}
            )

        elif msg_type == "message":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": data["message"],
                    "sender": self.channel_name,
                }
            )

        elif msg_type == "media":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_media",
                    "filename": data["filename"],
                    "content_type": data["content_type"],
                    "data": data["data"],
                    "sender_id": self.scope["user"].id,
                    "sender_name": self.scope["user"].username,
                }
            )

        elif msg_type == "video-offer":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "video_offer",
                    "offer": data["offer"],
                    "sender": self.channel_name,
                }
            )

        elif msg_type == "video-answer":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "video_answer",
                    "answer": data["answer"],
                    "sender": self.channel_name,
                }
            )

        elif msg_type == "ice-candidate":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "ice_candidate",
                    "candidate": data["candidate"],
                    "sender": self.channel_name,
                }
            )

    # Handlers para mensagens de chat e mídia

    async def chat_message(self, event):
        await self.send(json.dumps({
            "type": "message",
            "message": event["message"],
            "sender": event["sender"] == self.channel_name
        }))

    async def chat_media(self, event):
        await self.send(json.dumps({
            "type": "media",
            "filename": event["filename"],
            "content_type": event["content_type"],
            "data": event["data"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"],
            "is_self": event["sender_id"] == self.scope["user"].id
        }))

    async def user_typing(self, event):
        if event["user"] != self.channel_name:
            await self.send(json.dumps({"type": "typing"}))

    async def room_closed(self, event):
        await self.send(json.dumps({
            "type": "room_closed",
            "message": event.get("message", "")
        }))

    # Handlers para WebRTC

    async def video_offer(self, event):
        if event["sender"] != self.channel_name:
            await self.send(json.dumps({
                "type": "video-offer",
                "offer": event["offer"]
            }))

    async def video_answer(self, event):
        if event["sender"] != self.channel_name:
            await self.send(json.dumps({
                "type": "video-answer",
                "answer": event["answer"]
            }))

    async def ice_candidate(self, event):
        if event["sender"] != self.channel_name:
            await self.send(json.dumps({
                "type": "ice-candidate",
                "candidate": event["candidate"]
            }))
