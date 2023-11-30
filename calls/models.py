from django.db import models
from datetime import datetime

from django.contrib.auth import get_user_model

User = get_user_model()


class VideoCall(models.Model):
    STATUS_CHOICES = {
        0: 'Connecting',
        1: 'Not available',
        2: 'Accepted',
        3: 'Rejected',
        4: 'Busy',
        5: 'Processing',
        6: 'Ended',
        7: 'Cancel'
    }
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='caller_user')
    callee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='callee_user')
    status = models.IntegerField(default=0)
    started = models.DateTimeField(default=datetime.now)
    ended = models.DateTimeField(default=datetime.now)
    created = models.DateTimeField(default=datetime.now)

    @property
    def status_name(self):
        return self.STATUS_CHOICES[self.status]

    @property
    def duration(self):
        return self.ended - self.started
