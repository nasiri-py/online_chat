from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend:
    def authenticate(self, request, username=None, password=None):
        try:
            user = User.objects.get(email__icontains=username) or User.objects.get(username=username)
            if user.check_password(password):
                return user
            return None
        except User.DoesNotExist:
            return None

    def get_user(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None
