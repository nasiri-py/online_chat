from django.shortcuts import render
from django.utils.safestring import mark_safe
import json


def join_chat(request, username):
    return render(request, 'chat/join_chat.html', {'username_json': mark_safe(json.dumps(username))})
