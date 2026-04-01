from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from django.core.cache import cache

class CustomJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)
        
        jti = validated_token.get("jti")
        if cache.get(f"blacklisted_access_token:{jti}"):
            raise InvalidToken("Token is blacklisted", code="token_not_valid")
            
        return validated_token

class SubscriptionTokenAuthentication(JWTAuthentication):
    """
    Dedicated authentication class for Subscription UI views.
    Only looks for JWT tokens in the '?token=' query parameter.
    """
    def authenticate(self, request):
        raw_token = request.query_params.get('token')
        if not raw_token:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except Exception:
            return None
