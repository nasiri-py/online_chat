from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserOnlineStatus, Notification, GroupChat
import json

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_online_status(sender, instance, created, **kwargs):
    if created:
        UserOnlineStatus.objects.create(user_id=instance.id)


@receiver(post_save, sender=UserOnlineStatus)
def send_online_status(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    user = instance.user.username
    user_status = instance.online_status

    data = {
        'username': user,
        'status': user_status
    }
    async_to_sync(channel_layer.group_send)(
        'user', {
            'type': 'send_user_online_status',
            'value': json.dumps(data)
        }
    )


@receiver(post_save, sender=Notification)
def send_notification(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    user = str(instance.slug)
    if instance.not_seen_count != 0:
        notification = Notification.objects.get(user_id=instance.user, slug=instance.slug)

        data = {
            'user': notification.user.username,
            'not_seen_count': notification.not_seen_count,
            'last_text': notification.last_text,
            'category': notification.category,
            'slug': notification.slug,
            'title': notification.title,
        }

        if notification.category == 'g':
            chat = GroupChat.objects.get(unique_code=notification.slug)
            for user in chat.member.all():
                async_to_sync(channel_layer.group_send)(
                    user.username, {
                        'type': 'send_notification',
                        'value': json.dumps(data)
                    }
                )
        else:
            async_to_sync(channel_layer.group_send)(
                user, {
                    'type': 'send_notification',
                    'value': json.dumps(data)
                }
            )
            async_to_sync(channel_layer.group_send)(
                instance.user.username, {
                    'type': 'send_notification',
                    'value': json.dumps(data)
                }
            )
    else:
        async_to_sync(channel_layer.group_send)(
            user, {
                'type': 'send_notification',
                'value': json.dumps('seen')
            }
        )
