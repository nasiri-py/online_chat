from django.conf import settings
from django.core.mail import send_mail
import random

from core.models import OtpCode


def send_otp_code(username, email):
    token = random.randint(1111, 9999)

    subject = 'Validation Code'
    message = f'Hi {username},\n your validation code is {token}\n expire time: 3 MIN.'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [email, ]
    send_mail(subject, message, email_from, recipient_list)

    code_instance = OtpCode.objects.filter(email=email)
    if code_instance.exists():
        code_instance.delete()
    OtpCode.objects.create(email=email, code=token)
