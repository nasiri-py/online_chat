from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db.models import Q
from chat.models import GroupChat, Message, Notification
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

User = get_user_model()


@login_required
def index(request):
    current_user = request.user
    members = Notification.objects.filter(user=current_user).exclude(slug=current_user).order_by('-updated')
    notifications = Notification.objects.filter((Q(slug=request.user.username) | Q(user=request.user)))
    return render(request, 'chat/index.html',
                  {'members': members,'notifications': notifications,
                   'username_json': mark_safe(json.dumps(current_user.username))})


@login_required
def create_group(request):
    current_user = request.user
    title = request.POST['group_name']
    chat = GroupChat.objects.create(creator_id=current_user.id, title=title, member=current_user)
    Notification.objects.create(title=title, slug=chat.unique_code, user_id=current_user.id, category='g')
    return redirect(reverse('chat:group', args=[chat.unique_code]))


@login_required
def group(request, chat_id):
    current_user = request.user
    chat = get_object_or_404(GroupChat, unique_code=chat_id)
    messages = Message.objects.filter(slug=chat_id).order_by('created')
    member = Notification.objects.filter(slug=chat.unique_code, user_id=current_user.id, category='g').order_by('-updated')
    try:
        page_position = Notification.objects.get(user=current_user, slug=chat_id).position
    except Notification.DoesNotExist:
        page_position = ''

    context = {
        'chatObject': chat, 'messages': messages,
        'members': Notification.objects.filter(user_id=request.user.id).order_by('-updated'),
        'notifications': Notification.objects.filter((Q(slug=chat.unique_code) | Q(user=current_user))),
        'chat_id_json': mark_safe(json.dumps(chat.unique_code)),
        'username_json': mark_safe(json.dumps(current_user.username)),
        'page_position': mark_safe(json.dumps(page_position))
    }

    if request.method == "GET":
        if member.exists():
            return render(request, 'chat/group.html', context)
        return render(request, 'chat/join_group.html', {'chatObject': chat})

    elif request.method == "POST":
        if member.exists():
            return redirect('chat:group')
        Notification.objects.create(title=chat.title, slug=chat.unique_code, user_id=current_user.id, category='g')
        chat.member.add(current_user)
        chat.save()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.unique_code}",
            {
                'type': 'chat_activity',
                'message': json.dumps({'type': "join", 'username': current_user.username})
            }
        )

        return render(request, 'chat/group.html', context)


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
        Notification.objects.filter(slug=chat.unique_code, user_id=current_user.id, category='g').delete()

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
    current_user = request.user
    contact = get_object_or_404(User, username=username)
    messages = Message.objects.filter((Q(slug=contact.username) & Q(author=current_user)) | (Q(slug=current_user.username) & Q(author=contact)), active=True).order_by('created')
    members = Notification.objects.filter(user_id=current_user.id).order_by('-updated')
    notifications = Notification.objects.filter((Q(slug=current_user.username) | Q(user=current_user)))
    try:
        page_position = Notification.objects.get(user=current_user, slug=contact.username).position
    except Notification.DoesNotExist:
        page_position = ''
    return render(request, 'chat/room.html', {'contact': contact, 'messages': messages, 'members': members, 'notification': notifications,
                                              'contact_json': mark_safe(json.dumps(contact.username)),
                                              'user_json': mark_safe(json.dumps(current_user.username)),
                                              'username_json': mark_safe(json.dumps(current_user.username)),
                                              'page_position': mark_safe(json.dumps(page_position))})
