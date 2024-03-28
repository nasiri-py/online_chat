import hashlib
from django import template
from django.db.models import Q
from urllib.parse import urlencode

from chat.models import UserOnlineStatus, Message
from core.models import User

register = template.Library()


@register.simple_tag
def notif_filter(username, slug, category):
    try:
        if category == 'r':
            message = Message.objects.filter((Q(author__username=username) & Q(slug=slug)) | (Q(author__username=slug) & Q(slug=username))).order_by('-created').first()
        else:
            message = Message.objects.filter(slug=slug).order_by('-created').first()
        last_text = message.text
        if last_text is None:
            last_text = 'No Message'
        return last_text
    except AttributeError:
        return ''


@register.simple_tag
def online_status(slug):
    try:
        user_online_status = UserOnlineStatus.objects.get(user__username=slug)
        return user_online_status.online_status
    except UserOnlineStatus.DoesNotExist:
        return None


@register.filter
def gravatar(email, size="75"):
    """
    <img src='{{ request.user.email|gravatar:"75" }}'>
    """
    gravatar_url = "//www.gravatar.com/avatar/" + \
        hashlib.md5(email.encode('utf-8')).hexdigest() + "?"
    gravatar_url += urlencode({'d': 'retro', 's': str(size)})
    return gravatar_url


@register.simple_tag
def get_member_email(username):
    try:
        user = User.objects.get(username=username)
        return user.email
    except UserOnlineStatus.DoesNotExist:
        return None
