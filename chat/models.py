from django.db import models
import random

from django.contrib.auth import get_user_model

User = get_user_model()


def unique_generator(length=10):
    source = "abcdefghijklmnopqrstuvwxyz"
    result = ""
    for _ in range(length):
        result += source[random.randint(0, length)]
    return result


class GroupChat(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    unique_code = models.CharField(max_length=10, default=unique_generator)
    created = models.DateTimeField(auto_now_add=True)


class Member(models.Model):
    chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class GroupMessage(models.Model):
    chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)


class RoomMessage(models.Model):
    contact = models.ForeignKey(User, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_messages')
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
