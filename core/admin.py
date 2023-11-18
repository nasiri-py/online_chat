from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OtpCode


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff']
    search_fields = ['username', 'email']


admin.site.register(OtpCode)
