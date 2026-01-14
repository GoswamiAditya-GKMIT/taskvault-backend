from django.urls import path
from .views import RegisterAPIView , LoginAPIView , ResetPasswordAPIView , LogoutAPIView , TokenRefreshAPIView , UserListAPIView, UserDetailUpdateDeleteAPIView , VerifyEmailAPIView

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view()),
    path("auth/login/", LoginAPIView.as_view()),
    path("auth/logout/", LogoutAPIView.as_view()),
    path("auth/refresh/", TokenRefreshAPIView.as_view()),
    path("auth/verify-email/", VerifyEmailAPIView.as_view()),


    path("users/" , UserListAPIView.as_view()),
    path("users/reset-password/", ResetPasswordAPIView.as_view()),
    path("users/<uuid:id>/" , UserDetailUpdateDeleteAPIView.as_view())
]
