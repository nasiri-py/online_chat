from django import template
from django.db.models import Q

from chat.models import Notification, UserOnlineStatus

register = template.Library()


@register.simple_tag
def notif_filter(slug, username):
    notif = Notification.objects.filter(Q(slug=slug) | Q(slug=username)).order_by('updated').first()
    last_text = notif.last_text
    if last_text is None:
        last_text = 'No Message'
    return last_text


@register.simple_tag
def online_status(slug):
    try:
        user_online_status = UserOnlineStatus.objects.get(user__username=slug)
        return user_online_status.online_status
    except UserOnlineStatus.DoesNotExist:
        return None
