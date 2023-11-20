from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db.models import Q
from chat.models import Member, GroupChat
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from .models import RoomMessage

User = get_user_model()


@login_required
def index(request):
    current_user = request.user
    return render(request, 'chat/index.html', {'members':  Member.objects.filter(user_id=current_user.id)})


@login_required
def create_group(request):
    current_user = request.user
    title = request.POST['group_name']
    chat = GroupChat.objects.create(creator_id=current_user.id, title=title)
    Member.objects.create(chat_id=chat.id, user_id=current_user.id)
    return redirect(reverse('chat:group', args=[chat.unique_code]))


@login_required
def group(request, chat_id):
    current_user = request.user
    chat = get_object_or_404(GroupChat, unique_code=chat_id)

    if request.method == "GET":
        if Member.objects.filter(chat_id=chat.id, user_id=current_user.id).count() == 0:
            return render(request, 'chat/join_group.html', {'chatObject': chat})

        return render(request, 'chat/group.html',
                      {'chatObject': chat, 'chat_id_json': mark_safe(json.dumps(chat.unique_code)), 'members': Member.objects.filter(user_id=current_user.id)})
    elif request.method == "POST":
        if Member.objects.filter(chat_id=chat.id, user_id=current_user.id).exists() >= 1:
            Member.objects.filter(chat_id=chat.id, user_id=current_user.id).delete()

        Member.objects.create(chat_id=chat.id, user_id=current_user.id)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.unique_code}",
            {
                'type': 'chat_activity',
                'message': json.dumps({'type': "join", 'username': current_user.username})
            }
        )

        return render(request, 'chat/group.html',
                      {'chatObject': chat, 'chat_id_json': mark_safe(json.dumps(chat.unique_code)), 'members': Member.objects.filter(user_id=current_user.id)})


@login_required
def leave_group(request, chat_id):
    current_user = request.user
    chat = get_object_or_404(GroupChat, unique_code=chat_id)

    if chat.creator_id == current_user.id:
        chat.delete()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.unique_code}",
            {
                'type': 'chat_activity',
                'message': json.dumps({'type': "delete"})
            }
        )

    else:
        Member.objects.filter(chat_id=chat.id, user_id=current_user.id).delete()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.unique_code}",
            {
                'type': 'chat_activity',
                'message': json.dumps({'type': "leave", 'username': current_user.username})
            }
        )

    return redirect('chat:index')


@login_required
def room(request, username):
    contact = get_object_or_404(User, username=username)
    messages = RoomMessage.objects.filter((Q(contact=contact) & Q(author=request.user)) | (Q(contact=request.user) & Q(author=contact))).order_by('created')
    return render(request, 'chat/room.html', {'contact': contact, 'messages': messages,
                                              'contact_json': mark_safe(json.dumps(contact.username)),
                                              'user_json': mark_safe(json.dumps(request.user.username))})
