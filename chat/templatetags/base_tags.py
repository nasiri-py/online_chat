from django import template
from django.db.models import Q

from chat.models import UserOnlineStatus, Message

register = template.Library()


@register.simple_tag
def notif_filter(username, slug, category):
    if category == 'r':
        message = Message.objects.filter((Q(author__username=username) & Q(slug=slug)) | (Q(author__username=slug) & Q(slug=username))).order_by('-created').first()
    else:
        message = Message.objects.filter(slug=slug).order_by('-created').first()
    last_text = message.text
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
