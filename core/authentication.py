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
