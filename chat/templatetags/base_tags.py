from django import template
from django.db.models import Q

from chat.models import Notif

register = template.Library()


@register.simple_tag
def notif_filter(slug, username):
    notif = Notif.objects.filter(Q(slug=slug) | Q(slug=username)).order_by('-updated').first()
    return notif.last_text
