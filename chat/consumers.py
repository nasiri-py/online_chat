from channels.generic.websocket import StopConsumer, AsyncConsumer, AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
import json
from datetime import datetime

from .models import GroupChat, Message, Notification, UserOnlineStatus

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
        members = self.chat.member.all()
        for member in members:
            if member.username != self.user.username:
                notif = Notification.objects.get(user__username=member.username, slug=self.chat_id, category='g')
                notif.last_text = text
                notif.not_seen_count += 1
                notif.save()
        Message.objects.create(slug=self.chat_id, author_id=self.user.id, text=text)


class RoomConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        self.user = self.scope['user']
        self.author = self.scope['url_route']['kwargs']['username']
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
            self.contact_id = await self.get_contact_id()
            user_room_name = f'chat_{self.contact}'
            text = text_data_json['text']

            await self.create_message(text)

            await self.channel_layer.group_send(
                user_room_name,
                {
                    'type': 'chat_message',
                    'message': json.dumps({'text': text, 'time': str(datetime.today().strftime("%H:%M %p"))})
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
        try:
            notif = Notification.objects.get(user__username=self.contact, slug=self.user, category='r')
            notif.last_text = text
            notif.not_seen_count += 1
            notif.save()
        except Notification.DoesNotExist:
            contact = User.objects.get(username=self.contact)
            Notification.objects.create(title=self.user.username, user=contact, slug=self.user, category='r', last_text=text)
        Message.objects.create(slug=self.contact, author_id=self.user.id, text=text)


class UserOnlineStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'user'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, code):
        self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            text_data_json = json.loads(text_data)
            username = text_data_json['username']
            connection_type = text_data_json['type']
            await self.change_online_status(username, connection_type)

    @database_sync_to_async
    def change_online_status(self, username, c_type):
        user_online_status = UserOnlineStatus.objects.get(user__username=username)
        if c_type == 'open':
            user_online_status.online_status = True
            user_online_status.save()
        else:
            user_online_status.online_status = False
            user_online_status.save()

    async def send_user_online_status(self, event):
        data = json.loads(event.get('value'))
        username = data['username']
        online_status = data['status']
        await self.send(text_data=json.dumps({
            'username': username,
            'online_status': online_status
        }))


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        my_username = self.scope['user']
        self.room_group_name = f'{my_username}'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, code):
        self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            text_data_json = json.loads(text_data)
            username = text_data_json['username']
            path = text_data_json['path']
            await self.change_notification_to_seen(username, path)

    async def send_notification(self, event):
        data = json.loads(event.get('value'))
        if data == 'seen':
            await self.send(text_data=json.dumps({
                'seen': data,
            }))
        else:
            user = data['user']
            not_seen_count = data['not_seen_count']
            last_text = data['last_text']
            category = data['category']
            slug = data['slug']
            title = data['title']
            await self.send(text_data=json.dumps({
                'user': user,
                'not_seen_count': not_seen_count,
                'last_text': last_text,
                'category': category,
                'slug': slug,
                'title': title
            }))

    @database_sync_to_async
    def change_notification_to_seen(self, username, path):
        if 'group' in path:
            slug = path[7:-1]
            category = 'g'
        else:
            slug = path[6:-1]
            category = 'r'
        notification = Notification.objects.get(user__username=username, slug=slug, category=category)
        notification.not_seen_count = 0
        notification.save()
        messages = Message.objects.filter(author__username=username, slug=slug)
        for message in messages:
            message.is_seen = True
            message.save()
        self.channel_layer.group_send(
            username, {
                'type': 'send_notification_to_seen',
                'seen': 'true'
            }
        )

    async def send_notification_to_seen(self, event):
        seen = json.loads(event.get('seen'))
        print(seen)
        await self.send(text_data=json.dumps({
            'seen': seen
        }))
