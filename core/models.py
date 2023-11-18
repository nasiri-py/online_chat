from django.db import models

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    email = models.EmailField(unique=True)


class OtpCode(models.Model):
    email = models.EmailField(unique=True)
    code = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
