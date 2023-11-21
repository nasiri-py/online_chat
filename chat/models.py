from django.db import models
import random
import string

from django.contrib.auth import get_user_model

User = get_user_model()


def unique_generator(length=10):
    source = string.ascii_letters + string.digits
    result = ""
    for _ in range(length):
        result += source[random.randint(0, length)]
    return result


class GroupChat(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    unique_code = models.CharField(max_length=10, default=unique_generator, unique=True)
    created = models.DateTimeField(auto_now_add=True)


class Member(models.Model):
    CATEGORY_CHOICES = (
        ('g', 'group'),
        ('r', 'room')
    )
    title = models.CharField(max_length=150)
    slug = models.CharField(max_length=150)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=1, choices=CATEGORY_CHOICES)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['slug', 'user', 'category']]

    def __str__(self):
        return f'{self.user.username} - {self.slug} - {self.updated}'


class Message(models.Model):
    slug = models.CharField(max_length=150)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    active = models.BooleanField(default=True)
    seen = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)


class Notif(models.Model):
    CATEGORY_CHOICES = (
        ('g', 'group'),
        ('r', 'room')
    )
    slug = models.CharField(max_length=150)
    category = models.CharField(max_length=1, choices=CATEGORY_CHOICES)
    created = models.DateTimeField(auto_now_add=True)
    last_text = models.TextField()
    updated = models.DateTimeField(auto_now=True)


class UserOnlineStatus(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='onlinestatus')
    online_status = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} - {self.online_status}'
