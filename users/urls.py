from django.urls import path
from users.views import RegisterAPIView , LoginAPIView , ResetPasswordAPIView , LogoutAPIView , TokenRefreshAPIView

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view()),
    path("auth/login/", LoginAPIView.as_view()),
    path("auth/reset-password/", ResetPasswordAPIView.as_view()),
    path("auth/logout/", LogoutAPIView.as_view()),
    path("auth/refresh/", TokenRefreshAPIView.as_view()),
]


