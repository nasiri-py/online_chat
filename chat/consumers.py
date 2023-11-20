from channels.generic.websocket import StopConsumer, AsyncConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
import json

from .models import GroupChat, GroupMessage, RoomMessage

User = get_user_model()


class GroupConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        self.user = self.scope['user']
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat = await self.get_chat()
        self.group_name = f"chat_{self.chat_id}"

        if self.chat:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )

            await self.send({
                'type': 'websocket.accept'
                })
        else:
            await self.send({
                'type': 'websocket.close'
            })

    async def websocket_disconnect(self, event):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        raise StopConsumer()

    async def websocket_receive(self, event):
        text_data = event.get('text', None)
        bytes_data = event.get('bytes', None)

        if text_data:
            text_data_json = json.loads(text_data)
            text = text_data_json['text']

            await self.create_message(text)

            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': json.dumps({'type': "msg", 'sender': self.user.username, 'text': text}),
                    'sender_channel_name': self.channel_name
                }
            )

    async def chat_message(self, event):
        message = event['message']

        if self.channel_name != event['sender_channel_name']:
            await self.send({
                'type': 'websocket.send',
                'text': message
            })

    async def chat_activity(self, event):
        message = event['message']

        await self.send({
            'type': 'websocket.send',
            'text': message
        })

    @database_sync_to_async
    def get_chat(self):
        try:
            chat = GroupChat.objects.get(unique_code=self.chat_id)
            return chat
        except GroupChat.DoesNotExist:
            return None

    @database_sync_to_async
    def create_message(self, text):
        GroupMessage.objects.create(chat_id=self.chat.id, author_id=self.user.id, text=text)


class RoomConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        self.user = self.scope['user']
        self.author = self.scope['url_route']['kwargs']['username']
        print(self.author)
        self.author_id = await self.get_author_id()
        self.room_name = f"chat_{self.author}"

        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )

        await self.send({
            'type': 'websocket.accept'
            })

    async def websocket_disconnect(self, event):
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )
        raise StopConsumer()

    async def websocket_receive(self, event):
        text_data = event.get('text', None)
        bytes_data = event.get('bytes', None)

        if text_data:
            text_data_json = json.loads(text_data)
            self.contact = text_data_json['receiver']
            print(self.contact)
            self.contact_id = await self.get_contact_id()
            user_room_name = f'chat_{self.contact}'
            text = text_data_json['text']

            await self.create_message(text)

            await self.channel_layer.group_send(
                user_room_name,
                {
                    'type': 'chat_message',
                    'message': text_data,
                }
            )

    async def chat_message(self, event):
        message = event['message']

        await self.send({
            'type': 'websocket.send',
            'text': message
        })

    @database_sync_to_async
    def get_contact_id(self):
        try:
            contact_id = User.objects.get(username=self.contact).id
            return contact_id
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def get_author_id(self):
        try:
            author_id = User.objects.get(username=self.author).id
            return author_id
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def create_message(self, text):
        RoomMessage.objects.create(contact_id=self.author_id, author_id=self.contact_id, text=text)

