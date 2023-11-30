from channels.consumer import AsyncConsumer, StopConsumer
from asgiref.sync import sync_to_async
from datetime import datetime
from django.db.models import Q
import json

from .models import VideoCall
from chat.models import UserOnlineStatus
from django.contrib.auth import get_user_model

User = get_user_model()

# Video Call Status
VC_CONTACTING, VC_NOT_AVAILABLE, VC_ACCEPTED, VC_REJECTED, VC_BUSY, VC_PROCESSING, VC_ENDED, VC_CANCEL = \
    0, 1, 2, 3, 4, 5, 6, 7


class VideoCallConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        self.user = self.scope['user']
        self.user_room_id = f"videochat_{self.user.id}"

        await self.channel_layer.group_add(
            self.user_room_id,
            self.channel_name
        )

        await self.send({
            'type': 'websocket.accept'
        })

    async def websocket_disconnect(self, event):
        video_thread_id = self.scope['session'].get('video_thread_id', None)
        videothread = await sync_to_async(self.change_videothread_status)(video_thread_id, VC_ENDED)
        if videothread is not None:
            await sync_to_async(self.change_videothread_datetime)(video_thread_id, False)
            await self.channel_layer.group_send(
                f"videochat_{videothread.caller.id}",
                {
                    'type': 'chat_message',
                    'message': json.dumps(
                        {'type': "offerResult", 'status': VC_ENDED, 'video_thread_id': videothread.id}),
                }
            )
            await self.channel_layer.group_send(
                f"videochat_{videothread.callee.id}",
                {
                    'type': 'chat_message',
                    'message': json.dumps(
                        {'type': "offerResult", 'status': VC_ENDED, 'video_thread_id': videothread.id}),
                }
            )
        await self.channel_layer.group_discard(
            self.user_room_id,
            self.channel_name
        )
        raise StopConsumer()

    async def websocket_receive(self, event):
        text_data = event.get('text', None)
        bytes_data = event.get('bytes', None)

        if text_data:
            text_data_json = json.loads(text_data)
            message_type = text_data_json['type']

            if message_type == "createOffer":
                callee_username = text_data_json['username']
                status, video_thread_id = await sync_to_async(self.create_videothread)(callee_username)
                callee_online_status = await sync_to_async(self.callee_online_status)(callee_username)

                await self.send({
                    'type': 'websocket.send',
                    'text': json.dumps({'type': "offerResult", 'status': status, 'video_thread_id': video_thread_id, 'callee_online_status': str(callee_online_status)})
                })

                if status == VC_CONTACTING:
                    videothread = await sync_to_async(self.get_videothread)(video_thread_id)
                    await self.channel_layer.group_send(
                        f"videochat_{videothread.callee.id}",
                        {
                            'type': 'chat_message',
                            'message': json.dumps(
                                {'type': "offer", 'username': self.user.username, 'video_thread_id': video_thread_id}),
                        }
                    )

            elif message_type == "cancelOffer":
                video_thread_id = text_data_json['video_thread_id']
                videothread = await sync_to_async(self.get_videothread)(video_thread_id)
                self.scope['session']['video_thread_id'] = None

                if videothread.status != VC_ACCEPTED or videothread.status != VC_REJECTED:
                    await sync_to_async(self.change_videothread_status)(video_thread_id, VC_NOT_AVAILABLE)
                    await self.send({
                        'type': 'websocket.send',
                        'text': json.dumps(
                            {'type': "offerResult", 'status': VC_NOT_AVAILABLE, 'video_thread_id': videothread.id})
                    })
                    await self.channel_layer.group_send(
                        f"videochat_{videothread.callee.id}",
                        {
                            'type': 'chat_message',
                            'message': json.dumps({'type': "offerFinished"}),
                        }
                    )

            elif message_type == "acceptOffer":
                video_thread_id = text_data_json['video_thread_id']
                videothread = await sync_to_async(self.change_videothread_status)(video_thread_id, VC_PROCESSING)
                await sync_to_async(self.change_videothread_datetime)(video_thread_id, True)

                await self.channel_layer.group_send(
                    f"videochat_{videothread.caller.id}",
                    {
                        'type': 'chat_message',
                        'message': json.dumps(
                            {'type': "offerResult", 'status': VC_ACCEPTED, 'video_thread_id': videothread.id}),
                    }
                )

            elif message_type == "rejectOffer":
                video_thread_id = text_data_json['video_thread_id']
                videothread = await sync_to_async(self.change_videothread_status)(video_thread_id, VC_REJECTED)
                self.scope['session']['video_thread_id'] = None


                await self.channel_layer.group_send(
                    f"videochat_{videothread.caller.id}",
                    {
                        'type': 'chat_message',
                        'message': json.dumps(
                            {'type': "offerResult", 'status': VC_REJECTED, 'video_thread_id': videothread.id}),
                    }
                )

            elif message_type == "hangUp":
                video_thread_id = text_data_json['video_thread_id']
                print(video_thread_id)
                videothread = await sync_to_async(self.change_videothread_status)(video_thread_id, VC_ENDED)
                print(videothread)
                await sync_to_async(self.change_videothread_datetime)(video_thread_id, False)
                self.scope['session']['video_thread_id'] = None

                await self.channel_layer.group_send(
                    f"videochat_{videothread.caller.id}",
                    {
                        'type': 'chat_message',
                        'message': json.dumps(
                            {'type': "offerResult", 'status': VC_ENDED, 'video_thread_id': videothread.id}),
                    }
                )
                await self.channel_layer.group_send(
                    f"videochat_{videothread.callee.id}",
                    {
                        'type': 'chat_message',
                        'message': json.dumps(
                            {'type': "offerResult", 'status': VC_ENDED, 'video_thread_id': videothread.id}),
                    }
                )

            elif message_type == "cancel":
                video_thread_id = text_data_json['video_thread_id']
                videothread = await sync_to_async(self.get_videothread)(video_thread_id)
                self.scope['session']['video_thread_id'] = None

                if videothread.status != VC_ACCEPTED or videothread.status != VC_REJECTED:
                    await sync_to_async(self.change_videothread_status)(video_thread_id, VC_NOT_AVAILABLE)
                    await self.channel_layer.group_send(
                        f"videochat_{videothread.caller.id}",
                        {
                            'type': 'chat_message',
                            'message': json.dumps({'type': "offerFinished"}),
                        }
                    )
                    await self.channel_layer.group_send(
                        f"videochat_{videothread.callee.id}",
                        {
                            'type': 'chat_message',
                            'message': json.dumps({'type': "offerFinished"}),
                        }
                    )

            elif message_type == "callerData":
                video_thread_id = text_data_json['video_thread_id']
                videothread = await sync_to_async(self.get_videothread)(video_thread_id)

                await self.channel_layer.group_send(
                    f"videochat_{videothread.callee.id}",
                    {
                        'type': 'chat_message',
                        'message': text_data,
                    }
                )

            elif message_type == "calleeData":
                video_thread_id = text_data_json['video_thread_id']
                videothread = await sync_to_async(self.get_videothread)(video_thread_id)

                await self.channel_layer.group_send(
                    f"videochat_{videothread.caller.id}",
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


    def get_videothread(self, id):
        try:
            videothread = VideoCall.objects.get(id=id)
            print(videothread.callee)
            print(videothread.caller)
            return videothread
        except VideoCall.DoesNotExist:
            return None


    def create_videothread(self, callee_username):
        try:
            callee = User.objects.get(username=callee_username)
        except User.DoesNotExist:
            return 404, None

        if VideoCall.objects.filter(Q(caller_id=callee.id) | Q(callee_id=callee.id),
                                    status=VC_PROCESSING).count() > 0:
            return VC_BUSY, None

        videothread = VideoCall.objects.create(caller_id=self.user.id, callee_id=callee.id)
        self.scope['session']['video_thread_id'] = videothread.id

        print(videothread.callee)
        print(videothread.caller)

        return VC_CONTACTING, videothread.id


    def change_videothread_status(self, id, status):
        try:
            videothread = VideoCall.objects.get(id=id)
            print(videothread.callee)
            print(videothread.caller)
            videothread.status = status
            videothread.save()
            return videothread
        except VideoCall.DoesNotExist:
            return None


    def change_videothread_datetime(self, id, is_start):
        try:
            videothread = VideoCall.objects.get(id=id)
            if is_start:
                videothread.started = datetime.now()
            else:
                videothread.ended = datetime.now()
            videothread.save()
            print(videothread.callee)
            print(videothread.caller)
            print(videothread.started)
            print(videothread.ended)
            return videothread
        except VideoCall.DoesNotExist:
            return None

    def callee_online_status(self, username):
        user = User.objects.get(username=username)
        return UserOnlineStatus.objects.get(user=user).online_status
