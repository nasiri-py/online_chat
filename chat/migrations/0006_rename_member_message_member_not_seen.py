# Generated by Django 4.2.4 on 2023-11-29 13:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0005_message_member_alter_message_author'),
    ]

    operations = [
        migrations.RenameField(
            model_name='message',
            old_name='member',
            new_name='member_not_seen',
        ),
    ]
