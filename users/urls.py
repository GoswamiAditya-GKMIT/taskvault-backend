from django.urls import path
from .views import RegisterAPIView , LoginAPIView , ResetPasswordAPIView , LogoutAPIView , TokenRefreshAPIView , UserListCreateAPIView, UserDetailUpdateDeleteAPIView , OrganizationCreateAPIView , ResendVerificationLinkAPIView , LoginOTPVerifyAPIView , reset_password_view ,ForgotPasswordAPIView , VerifyUserTokenAPIView , InviteUserAPIView , InviteRegisterAPIView , ResendLoginOTPAPIView, OrganizationDetailAPIView, UserRestoreAPIView


urlpatterns = [
    path("auth/tenant/<uuid:tenant_id>/register/", RegisterAPIView.as_view()),
    path("auth/login/", LoginAPIView.as_view()),
    path("auth/login/verify-otp/", LoginOTPVerifyAPIView.as_view()),
    path("auth/login/resend-otp/", ResendLoginOTPAPIView.as_view()),
    path("auth/logout/", LogoutAPIView.as_view()),
    path("auth/refresh/", TokenRefreshAPIView.as_view()),
    path("auth/email-verification/resend/", ResendVerificationLinkAPIView.as_view()),
    path("auth/invite/<str:token>/register/", InviteRegisterAPIView.as_view()),
    path("auth/forgot-password/", ForgotPasswordAPIView.as_view()),
    path("auth/reset-password/<str:token>/", reset_password_view),
    path("auth/email-verification/verify/", VerifyUserTokenAPIView.as_view()),

    path("users/", UserListCreateAPIView.as_view()),
    path("users/change-password/", ResetPasswordAPIView.as_view()),
    path("users/<uuid:id>/" , UserDetailUpdateDeleteAPIView.as_view()),
    path("users/<uuid:id>/restore/", UserRestoreAPIView.as_view()),
    path("users/invite/", InviteUserAPIView.as_view()),

    path("organizations/" , OrganizationCreateAPIView.as_view()),
    path("organizations/<uuid:id>/" , OrganizationDetailAPIView.as_view())
]
