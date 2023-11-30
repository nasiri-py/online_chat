from channels.generic.websocket import StopConsumer, AsyncConsumer, AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync
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
        self.group_name = f"group_{self.chat_id}"

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

            msg_id = await self.create_message(text)

            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': json.dumps(
                        {'text': text, 'type': "msg", 'sender': self.user.username, 'id': msg_id,
                         'time': str(datetime.today().strftime("%H:%M %p")),
                         'receiver': self.chat_id}),
                }
            )

    async def chat_message(self, event):
        message = event['message']

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
            notification = Notification.objects.get(user__username=member.username, slug=self.chat_id, category='g')
            if member.username != self.user.username:
                notification.last_text = text
                notification.not_seen_count += 1
                notification.save()
            else:
                notification.position = ''
                notification.save()
        message = Message.objects.create(slug=self.chat_id, author_id=self.user.id, text=text)
        message.member_not_seen.set(members)
        message.member_not_seen.remove(self.user)
        return message.id


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

            msg_id = await self.create_message(text)

            await self.channel_layer.group_send(
                user_room_name,
                {
                    'type': 'chat_message',
                    'message': json.dumps(
                        {'text': text, 'id': msg_id, 'time': str(datetime.today().strftime("%H:%M %p")), 'receiver': self.contact})
                }
            )

            await self.channel_layer.group_send(
                self.room_name,
                {
                    'type': 'chat_message',
                    'message': json.dumps(
                        {'text': text, 'id': msg_id, 'time': str(datetime.today().strftime("%H:%M %p")), 'receiver': self.contact})
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
            notification = Notification.objects.get(user__username=self.contact, slug=self.user.username, category='r')
            notification.last_text = text
            notification.not_seen_count += 1
            notification.save()
        except Notification.DoesNotExist:
            user = User.objects.get(username=self.contact)
            Notification.objects.create(title=self.contact, user=user, slug=self.user.username, category='r', last_text=text, not_seen_count=1)
        Notification.objects.get_or_create(title=self.user.username, user=self.user, slug=self.contact, category='r')

        try:
            notification = Notification.objects.get(title=self.user.username, user=self.user, slug=self.contact, category='r')
            notification.position = ''
            notification.save()
        except Notification.DoesNotExist:
            Notification.objects.Create(title=self.user.username, user=self.user, slug=self.contact, category='r')

        message = Message.objects.create(slug=self.contact, author_id=self.user.id, text=text)
        return message.id


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

    async def send_notification(self, event):
        data = json.loads(event.get('value'))
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


class SeenMessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.username = self.scope['user']
        self.slug = self.scope['url_route']['kwargs']['slug']
        self.room_group_name = f'seen_{self.slug}'
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
            msg_id = text_data_json['msg_id']
            slug = text_data_json['slug']
            category = text_data_json['category']
            user = text_data_json['user']
            position = text_data_json['position']
            await self.change_message_to_seen(msg_id, slug, category, user, position)

    @database_sync_to_async
    def change_message_to_seen(self, msg_id, slug, category, user, position):
        message = Message.objects.get(id=int(msg_id))
        if not message.is_seen:
            this_user = User.objects.get(username=user)
            message.is_seen = True
            message.member_not_seen.remove(this_user)
            message.save()
        if category == 'r':
            notification = Notification.objects.get(user__username=user, slug=message.author, category=category)
            if notification.not_seen_count > 0:
                notification.not_seen_count -= 1
                notification.position = position
                notification.save(update_fields=['not_seen_count', 'position'])
            if message.author != self.username:
                async_to_sync(self.channel_layer.group_send)(
                    f'seen_{message.author}', {
                        'type': 'send_seen_message',
                        'msg_id': msg_id,
                    }
                )
        else:
            notification = Notification.objects.get(user__username=user, slug=slug, category=category)
            if notification.not_seen_count > 0:
                notification.not_seen_count -= 1
                notification.position = position
                notification.save(update_fields=['not_seen_count', 'position'])
            if message.author != user:
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name, {
                        'type': 'send_seen_message',
                        'msg_id': {'id': msg_id, 'sender': str(message.author.username)}
                    }
                )

    async def send_seen_message(self, event):
        msg_id = event['msg_id']
        if 'sender' in msg_id:
            id = msg_id['id']
            sender = msg_id['sender']
            await self.send(text_data=json.dumps({
                'msg_id': id,
                'sender': sender
            }))
        await self.send(text_data=json.dumps({
            'msg_id': msg_id
        }))
