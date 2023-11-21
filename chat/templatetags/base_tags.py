from django import template
from django.db.models import Q

from chat.models import Notif, UserOnlineStatus

register = template.Library()


@register.simple_tag
def notif_filter(slug, username):
    notif = Notif.objects.filter(Q(slug=slug) | Q(slug=username)).order_by('-updated').first()
    return notif.last_text


@register.simple_tag
def online_status(slug):
    user_online_status = UserOnlineStatus.objects.get(user__username=slug)
    return user_online_status.online_status
