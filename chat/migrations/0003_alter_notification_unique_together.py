# Generated by Django 4.2.4 on 2023-11-27 21:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_message_is_seen'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='notification',
            unique_together=set(),
        ),
    ]
