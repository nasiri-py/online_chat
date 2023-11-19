from django.contrib import admin

from .models import GroupChat, Member, Message


admin.site.register(GroupChat)
admin.site.register(Member)
admin.site.register(Message)
