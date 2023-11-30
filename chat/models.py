from django.db import models
import random
import string
from datetime import datetime

from django.contrib.auth import get_user_model

User = get_user_model()


def unique_generator(length=10):
    source = string.ascii_letters + string.digits
    result = ""
    for _ in range(length):
        result += source[random.randint(0, length)]
    return result


class GroupChat(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_chats')
    member = models.ManyToManyField(User)
    title = models.CharField(max_length=150)
    unique_code = models.CharField(max_length=10, default=unique_generator, unique=True)
    created = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    slug = models.CharField(max_length=150)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    member_not_seen = models.ManyToManyField(User)
    text = models.TextField()
    is_seen = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    CATEGORY_CHOICES = (
        ('g', 'group'),
        ('r', 'room')
    )
    title = models.CharField(max_length=150)
    slug = models.CharField(max_length=150)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=1, choices=CATEGORY_CHOICES)
    last_text = models.TextField(null=True, blank=True)
    position = models.CharField(max_length=255, blank=True)
    not_seen_count = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['slug', 'user', 'category']]

    def __str__(self):
        return f'{self.user.username} - {self.slug} - {self.not_seen_count}'


class UserOnlineStatus(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='onlinestatus')
    online_status = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} - {self.online_status}'
