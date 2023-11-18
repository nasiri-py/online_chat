from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

User = get_user_model()


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__exact=email).exists():
            raise ValidationError('A user with that email already exists.')
        return email


class OtpCodeLoginForm(forms.Form):
    email = forms.EmailField()


class ProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):

        # get user from kwargs
        self.user = kwargs.pop('user')
        super(ProfileForm, self).__init__(*args, **kwargs)
        if not self.user.is_staff:
            self.fields['username'].disabled = True

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__icontains=email).exclude(username=self.user.username).exists():
            raise ValidationError('A user with that email already exists.')
        return email
