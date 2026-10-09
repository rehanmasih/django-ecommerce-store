from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Authenticate with a username or an email address (case-insensitive)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if not username or password is None:
            return None
        user = User.objects.filter(username__iexact=username).first()
        if user is None:
            matches = list(User.objects.filter(email__iexact=username)[:2])
            user = matches[0] if len(matches) == 1 else None  # ambiguous email -> refuse
        if user is not None and user.check_password(password) and self.user_can_authenticate(user):
            return user
        User().set_password(password)  # equalise timing for unknown users
        return None
