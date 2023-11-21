from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserOnlineStatus
import json

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


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
