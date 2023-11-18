import pytz
from django.shortcuts import render, redirect, reverse
from django.views import generic, View
from django.contrib.auth.views import PasswordResetConfirmView, PasswordChangeView
from django.contrib.auth import get_user_model
from .forms import RegisterForm, OtpCodeLoginForm, ProfileForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from utils import send_otp_code
from .models import OtpCode
from django.contrib import messages
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse
from django.conf import settings
from django.core.mail import send_mail

User = get_user_model()


class RegisterView(generic.CreateView):
    form_class = RegisterForm
    template_name = 'registration/register.html'

    def form_valid(self, form):
        if form.is_valid():
            cd = form.cleaned_data
            send_otp_code(cd['username'], cd['email'])
            self.request.session['user_registration'] = {
                'username': cd['username'],
                'email': cd['email'],
                'password': cd['password1'],
                'url': self.request.path
            }
            messages.success(self.request, f"your Validation Code sent To {cd['email']}")
            return redirect('accounts:verify')
        return redirect('accounts:register')


class VerifyView(generic.CreateView):
    model = OtpCode
    fields = ['code']
    template_name = 'registration/verify.html'

    def get(self, request, *args, **kwargs):
        try:

            # user can be redirected here only from specific views (RegisterView, ResendCodeView, OtpCodeLoginView, Profile)
            user_session = request.session['user_registration']
            if user_session['url']:
                del user_session['url']
                request.session.modified = True
                return super().get(request, *args, **kwargs)
        except Exception:
            return redirect('accounts:login')

    def form_valid(self, form):
        user_session = self.request.session['user_registration']
        try:

            # check otp code time out
            code_instance = OtpCode.objects.get(email__icontains=user_session['email'])
            if code_instance.created + timedelta(minutes=3) < datetime.now(pytz.UTC):
                code_instance.delete()
                messages.error(self.request, 'your Validation Code has been expired')
                return redirect('accounts:login')

            if form.is_valid():
                cd = form.cleaned_data
                # check received code from user
                if int(cd['code']) == int(code_instance.code):
                    # for login by otp code
                    if User.objects.filter(email__icontains=user_session['email']).exists():
                        user = User.objects.get(email__icontains=user_session['email'])
                    # for change email
                    elif 'email_old' in user_session:
                        user = User.objects.get(email__icontains=user_session['email_old'])
                        user.email = user_session['email']
                        user.first_name = user_session['f_name']
                        user.last_name = user_session['l_name']
                        user.save()
                        messages.success(self.request, f'your Profile updated successfully')
                        return redirect('accounts:profile')
                    # for crate user
                    else:
                        user = User.objects.create_user(user_session['username'], user_session['email'],
                                                        user_session['password'])
                    del user_session
                    code_instance.delete()
                    if user is not None:
                        user.backend = 'django.contrib.auth.backends.ModelBackend'
                        login(self.request, user)
                        return redirect('accounts:profile')
                return redirect('accounts:verify')
        except Exception:
            messages.error(self.request, 'your Validation Code has been expired. Please try again')
            return redirect('accounts:login')


def verify_check_view(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        res = None
        code = request.POST.get('code')
        qs = OtpCode.objects.filter(code__exact=code)
        if len(code) != 4:
            res = 'Validation Code is 4 digits '
        elif qs.exists():
            res = 'TrueAccess'
        else:
            res = 'your Validation Code not corrected'
        return JsonResponse({'data': res})
    return JsonResponse({})


class ResendCodeView(View):
    def get(self, request):
        return redirect('accounts:login')

    def post(self, request):

        # user can request only by resend code form (input name = access)
        if request.POST['access']:
            user_session = self.request.session['user_registration']
            user_session['url'] = self.request.path
            self.request.session.modified = True
            send_otp_code(user_session['username'], user_session['email'])
            messages.success(self.request, f"your Validation Code sent To {user_session['email']}")
            return redirect('accounts:verify')
        return redirect('accounts:login')


class OtpCodeLoginView(View):
    form_class = OtpCodeLoginForm
    template_name = 'registration/otp_code_login.html'

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST or None)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                user = User.objects.get(email__icontains=cd['email'])
                send_otp_code(user.username, cd['email'])
                request.session['user_registration'] = {
                    'username': user.username,
                    'email': cd['email'],
                    'url': request.path
                }
                messages.success(self.request, f"your Validation Code sent To {cd['email']}")
                return redirect('accounts:verify')
            except User.DoesNotExist:
                messages.error(self.request, f"There is no user with {cd['email']}")
                return redirect('accounts:otp-code-login')
        return render(request, self.template_name, {'form': form})


class PasswordResetView(View):
    form_class = OtpCodeLoginForm
    token_generator = PasswordResetTokenGenerator

    def get(self, request):
        form = self.form_class()
        return render(request, 'registration/password_reset.html', {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email__icontains=email)
            except User.DoesNotExist:
                messages.error(self.request, f"There is no user with {email}")
                return redirect('accounts:password-reset')

            # send password reset address to user
            current_site = get_current_site(self.request)
            token_generator = self.token_generator()
            message = render_to_string('registration/password_reset_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': token_generator.make_token(user),
            })
            email_from = settings.EMAIL_HOST_USER
            send_mail('Password Reset', message, email_from, [email, ] )
            messages.success(request, f'We`ve emailed you instructions for setting your password. You should receive the email shortly!')
            return redirect('accounts:login')
        return render(request, 'registration/password_reset.html', {'form': form})


class PasswordResetConfirm(PasswordResetConfirmView):
    def get_success_url(self):
        messages.success(self.request, 'your Password changed successfully')
        return reverse('accounts:login')


class Profile(LoginRequiredMixin, generic.UpdateView):
    template_name = 'registration/profile.html'
    form_class = ProfileForm

    def get_object(self):
        return User.objects.get(pk=self.request.user.pk)

    def get_form_kwargs(self):
        # send user to kwargs
        kwargs = super(Profile, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def form_valid(self, form):
        if form.is_valid():
            email_new = form.cleaned_data['email']
            email_old = self.request.user.email

            # if user change email, redirect to VerifyView
            if email_new != email_old:
                self.request.session['user_registration'] = {
                    'email': email_new,
                    'email_old': email_old,
                    'f_name': form.cleaned_data['first_name'],
                    'l_name': form.cleaned_data['last_name'],
                    'url': self.request.path,
                }
                send_otp_code(self.request.user.username, email_new)
                messages.success(self.request, f'your Validation Code sent To {email_new}')
                return redirect('accounts:verify')

            form.save()
            messages.success(self.request, 'your Profile updated successfully')
            return redirect('accounts:profile')
        return render(self.request, self.template_name, {'form': form})


class PasswordChange(LoginRequiredMixin, PasswordChangeView):

    def form_valid(self, form):
        form.save()

        # change password
        update_session_auth_hash(self.request, form.user)
        messages.success(self.request, 'your Password changed Successfully')
        return redirect('accounts:profile')
