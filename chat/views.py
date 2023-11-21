from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db.models import Q
from chat.models import Member, GroupChat, Message, Notif, UserOnlineStatus
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

User = get_user_model()


@login_required
def index(request):
    return render(request, 'chat/index.html',
                  {'members': Member.objects.filter(user_id=request.user.id).order_by('-updated'), 'notifs': Notif.objects.all(),
                   'username_json': mark_safe(json.dumps(request.user.username))})


@login_required
def create_group(request):
    current_user = request.user
    title = request.POST['group_name']
    chat = GroupChat.objects.create(creator_id=current_user.id, title=title)
    Member.objects.create(title=title, slug=chat.unique_code, user_id=current_user.id, category='g')
    return redirect(reverse('chat:group', args=[chat.unique_code]))


@login_required
def group(request, chat_id):
    current_user = request.user
    chat = get_object_or_404(GroupChat, unique_code=chat_id)
    messages = Message.objects.filter(slug=chat_id).order_by('created')
    member = Member.objects.filter(slug=chat.unique_code, user_id=current_user.id, category='g')

    if request.method == "GET":
        if member.exists():
            return render(request, 'chat/group.html',
                          {'chatObject': chat, 'messages': messages, 'chat_id_json': mark_safe(json.dumps(chat.unique_code)),
                           'members': Member.objects.filter(user_id=request.user.id).order_by('-updated'), 'notifs': Notif.objects.all(), 'username_json': mark_safe(json.dumps(request.user.username))})
        return render(request, 'chat/join_group.html', {'chatObject': chat})

    elif request.method == "POST":
        if member.exists():
            return render(request, 'chat/group.html',
                          {'chatObject': chat, 'messages': messages, 'chat_id_json': mark_safe(json.dumps(chat.unique_code)),
                           'members': Member.objects.filter(user_id=request.user.id).order_by('-updated'), 'notifs': Notif.objects.all(), 'username_json': mark_safe(json.dumps(request.user.username))})
        Member.objects.create(title=chat.title, slug=chat.unique_code, user_id=current_user.id, category='g')

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.unique_code}",
            {
                'type': 'chat_activity',
                'message': json.dumps({'type': "join", 'username': current_user.username})
            }
        )

        return render(request, 'chat/group.html',
                      {'chatObject': chat, 'messages': messages, 'chat_id_json': mark_safe(json.dumps(chat.unique_code)), 'members': Member.objects.filter(user_id=request.user.id).order_by('-updated'), 'notifs': Notif.objects.all(), 'username_json': mark_safe(json.dumps(request.user.username))})


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
        Member.objects.filter(slug=chat.unique_code, user_id=current_user.id, category='g').delete()

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
    try:
        Member.objects.get(slug=username, user_id=request.user.id, category='r')
    except Member.DoesNotExist:
        Member.objects.create(title=username, slug=username, user_id=request.user.id, category='r')
    messages = Message.objects.filter((Q(slug=contact.username) & Q(author=request.user)) | (Q(slug=request.user.username) & Q(author=contact)), active=True).order_by('created')
    members = Member.objects.filter(user_id=request.user.id).order_by('-updated')
    notifs = Notif.objects.all()
    return render(request, 'chat/room.html', {'contact': contact, 'messages': messages, 'members': members, 'notifs': notifs,
                                              'contact_json': mark_safe(json.dumps(contact.username)),
                                              'user_json': mark_safe(json.dumps(request.user.username)), 'username_json': mark_safe(json.dumps(request.user.username))})
