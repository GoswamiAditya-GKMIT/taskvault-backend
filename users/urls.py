from django.urls import path
from .views import RegisterAPIView , LoginAPIView , ResetPasswordAPIView , LogoutAPIView , TokenRefreshAPIView , UserListCreateAPIView, UserDetailUpdateDeleteAPIView , OrganizationCreateAPIView , ResendVerificationLinkAPIView , LoginOTPVerifyAPIView , reset_password_view ,ForgotPasswordAPIView , VerifyUserTokenAPIView , InviteUserAPIView , InviteRegisterAPIView , ResendLoginOTPAPIView, OrganizationDetailAPIView, UserRestoreAPIView


urlpatterns = [
    path("auth/tenant/<uuid:tenant_id>/register/", RegisterAPIView.as_view(), name="register"),
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/login/verify-otp/", LoginOTPVerifyAPIView.as_view(), name="login_otp_verify"),
    path("auth/login/resend-otp/", ResendLoginOTPAPIView.as_view(), name="resend_login_otp"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("auth/refresh/", TokenRefreshAPIView.as_view(), name="token_refresh"),
    path("auth/email-verification/resend/", ResendVerificationLinkAPIView.as_view(), name="resend_verification_link"),
    path("auth/invite/<str:token>/register/", InviteRegisterAPIView.as_view(), name="invite_register"),
    path("auth/forgot-password/", ForgotPasswordAPIView.as_view(), name="forgot_password"),
    path("auth/reset-password/<str:token>/", reset_password_view, name="reset_password_view"),
    path("auth/email-verification/verify/", VerifyUserTokenAPIView.as_view(), name="verify_email"),

    path("users/", UserListCreateAPIView.as_view(), name="user-list-create"),
    path("users/change-password/", ResetPasswordAPIView.as_view(), name="reset_password"),
    path("users/<uuid:id>/" , UserDetailUpdateDeleteAPIView.as_view(), name="user-detail-update-delete"),
    path("users/<uuid:id>/restore/", UserRestoreAPIView.as_view(), name="user-restore"),
    path("users/invite/", InviteUserAPIView.as_view(), name="invite_user"),

    path("organizations/" , OrganizationCreateAPIView.as_view(), name="organization-list-create"),
    path("organizations/<uuid:id>/" , OrganizationDetailAPIView.as_view(), name="organization-detail-update-delete")
]
