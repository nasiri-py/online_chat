from django.urls import path

from . import views


app_name = 'chat'
urlpatterns = [
    path('chat/', views.index, name='index'),
    path('create_group/', views.create_group, name='create_group'),
    path('group/<str:chat_id>/', views.group, name='group'),
    path('group/<str:chat_id>/leave/', views.leave_group, name='leave_group'),
    path('room/<str:username>/', views.room, name='room'),
]
