from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import uuid

User = get_user_model()

class EmailBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None or password is None:
            return None
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token[self.user_id_claim]
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise InvalidToken(_('Token contains no recognizable user identification'))
        except (TypeError, ValueError):
            raise InvalidToken(_('Token contains no recognizable user identification'))
        
        if not user.is_active:
            raise InvalidToken(_('User inactive or deleted'))
        
        return user
