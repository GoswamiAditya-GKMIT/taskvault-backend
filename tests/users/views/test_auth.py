import pytest
from rest_framework import status
from django.urls import reverse
from django.core.cache import cache
from tests.factories import UserFactory, NormalUserFactory, TenantAdminFactory
from tests.factories import OrganizationFactory
from tests.factories import UserPayloadFactory, LoginPayloadFactory

@pytest.mark.django_db
class TestRegistrationAPI:
    """
    Test suite for user self-registration behavior.
    """

    def test_registration_success(self, api_client, mocker):
        """
        Verify that a user can successfully register with valid data and an active organization.
        """
        mock_send = mocker.patch('users.views.auth.send_verification_link_email.delay')
        org = OrganizationFactory(is_active=True)
        url = reverse('register', kwargs={'tenant_id': org.id})
        payload = UserPayloadFactory()
        
        response = api_client.post(url, payload)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "success"
        assert "Registration successful" in response.data["message"]
        mock_send.assert_called_once()

    def test_registration_passwords_mismatch(self, api_client):
        """
        Verify that registration fails if password and confirm_password do not match.
        """
        org = OrganizationFactory()
        url = reverse('register', kwargs={'tenant_id': org.id})
        payload = UserPayloadFactory(confirm_password="DifferentPassword123!")
        
        response = api_client.post(url, payload)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Passwords do not match." in str(response.data["error"]["confirm_password"])

    def test_registration_inactive_org(self, api_client):
        """
        Verify that registration fails if the target organization is inactive.
        """
        org = OrganizationFactory(is_active=False)
        url = reverse('register', kwargs={'tenant_id': org.id})
        payload = UserPayloadFactory()
        
        response = api_client.post(url, payload)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid or inactive organization." in str(response.data["error"]["organization"])

    def test_registration_duplicate_email_verified(self, api_client):
        """
        Verify that registration fails for an already verified email.
        """
        org = OrganizationFactory(is_active=True)
        NormalUserFactory(email="already@exists.com", is_email_verified=True)
        url = reverse('register', kwargs={'tenant_id': org.id})
        payload = UserPayloadFactory(email="already@exists.com")
        
        response = api_client.post(url, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email already exists" in str(response.data["error"]["email"])

    def test_registration_pending_verification(self, api_client):
        """
        Verify that registration fails if verification is already pending.
        """
        org = OrganizationFactory(is_active=True)
        user = NormalUserFactory(email="pending@exists.com", is_email_verified=False)
        cache.set(f"user_verification_active_token:{user.id}", "some-token", timeout=300)
        
        url = reverse('register', kwargs={'tenant_id': org.id})
        payload = UserPayloadFactory(email="pending@exists.com")
        
        response = api_client.post(url, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "verification is already pending" in str(response.data["error"]["email"])

@pytest.mark.django_db
class TestLoginAPI:
    """
    Test suite for authentication (Login) behavior.
    """

    def test_login_success_triggers_otp(self, api_client, mocker):
        """
        Verify that valid credentials result in an OTP being sent.
        """
        mock_send = mocker.patch('users.serializers.auth.send_user_verification_otp.delay')
        user = NormalUserFactory(is_active=True, is_email_verified=True)
        # Force password to match factory expected usage if needed, but NormalUserFactory uses 'testpass123' by default
        url = reverse('login')
        payload = {
            "username": user.username,
            "password": "StrongPassword@2026!"
        }
        
        response = api_client.post(url, payload)
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "OTP sent to your email" in response.data["message"]
        mock_send.assert_called_once()

    def test_login_invalid_credentials(self, api_client):
        """
        Verify that invalid credentials return an authentication failed error.
        """
        user = NormalUserFactory(is_active=True, is_email_verified=True)
        url = reverse('login')
        payload = {
            "username": user.username,
            "password": "WrongPassword123"
        }
        
        response = api_client.post(url, payload)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["message"] == "Authentication failed"
        assert response.data["error"]["detail"] == "Invalid username or password"

    def test_login_unverified_email(self, api_client):
        """
        Verify that users with unverified emails are forbidden from logging in.
        """
        user = NormalUserFactory(is_active=True, is_email_verified=False)
        url = reverse('login')
        payload = {
            "username": user.username,
            "password": "StrongPassword@2026!"
        }
        
        response = api_client.post(url, payload)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["message"] == "Permission denied"
        assert response.data["error"]["detail"] == "Email verification pending."

    def test_login_rate_limit(self, api_client):
        """
        Verify that multiple login attempts trigger OTP cooldown.
        """
        user = NormalUserFactory(is_active=True, is_email_verified=True)
        cache.set(f"login_otp_cooldown:{user.id}", True, timeout=60)
        url = reverse('login')
        payload = {
            "username": user.username,
            "password": "StrongPassword@2026!"
        }
        
        response = api_client.post(url, payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "OTP already sent" in str(response.data["error"]["detail"])


@pytest.mark.django_db
class TestLoginOTPVerifyAPI:
    """
    Test suite for Login OTP verification.
    """

    def test_otp_verification_success(self, api_client):
        """
        Verify that a valid OTP results in successful login and issuance of tokens.
        """
        user = NormalUserFactory(is_active=True, is_email_verified=True)
        otp = "123456"
        cache.set(f"login_otp:{user.id}", {"otp": otp}, timeout=300)
        
        url = reverse('login_otp_verify')
        payload = {
            "username": user.username,
            "otp": otp
        }
        
        response = api_client.post(url, payload)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Login successful"
        assert "access" in response.data["data"]

    def test_otp_verification_invalid(self, api_client):
        """
        Verify that an incorrect OTP returns an authentication failed error.
        """
        user = NormalUserFactory(is_active=True, is_email_verified=True)
        cache.set(f"login_otp:{user.id}", {"otp": "123456"}, timeout=300)
        
        url = reverse('login_otp_verify')
        payload = {
            "username": user.username,
            "otp": "000000"
        }
        
        response = api_client.post(url, payload)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["message"] == "Authentication failed"
        assert response.data["error"]["detail"] == "Invalid OTP"

    def test_otp_verification_expired(self, api_client):
        """
        Verify that an expired OTP (not in cache) returns an error.
        """
        user = NormalUserFactory(is_active=True, is_email_verified=True)
        # OTP not set in cache
        
        url = reverse('login_otp_verify')
        payload = {
            "username": user.username,
            "otp": "123456"
        }
        
        response = api_client.post(url, payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "OTP expired or invalid" in str(response.data["error"]["detail"])

@pytest.mark.django_db
class TestResetPasswordAPI:
    """
    Test suite for password reset behavior.
    """

    def test_reset_password_success(self, user_client, normal_user):
        """
        Verify that an authenticated user can reset their password with correct current password.
        """
        url = reverse('reset_password')
        payload = {
            "current_password": "StrongPassword@2026!", # default in factory
            "new_password": "NewStrongPass1!",
            "confirm_new_password": "NewStrongPass1!"
        }
        
        response = user_client.post(url, payload)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Password changed successfully"
        normal_user.refresh_from_db()
        assert normal_user.check_password("NewStrongPass1!")

    def test_reset_password_incorrect_current(self, user_client):
        """
        Verify that password reset fails if the current password is incorrect.
        """
        url = reverse('reset_password')
        payload = {
            "current_password": "WrongCurrentPassword",
            "new_password": "NewStrongPass1!",
            "confirm_new_password": "NewStrongPass1!"
        }
        
        response = user_client.post(url, payload)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Current password is incorrect" in str(response.data["error"]["current_password"])

@pytest.mark.django_db
class TestLogoutAPI:
    """
    Test suite for session termination (Logout) behavior.
    """

    def test_logout_success(self, api_client, normal_user):
        """
        Verify that an authenticated user can logout using a valid refresh token.
        """
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(normal_user)
        access_token = refresh.access_token
        jti = access_token.payload['jti']
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('logout')
        payload = {"refresh": str(refresh)}
    
        response = api_client.post(url, payload)
    
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Logout successful"
    
        # Verify blacklisting
        assert cache.get(f"blacklisted_access_token:{jti}") is True

@pytest.mark.django_db
class TestResendAuthAPI:
    """
    Test suite for resending authentication codes and links.
    """

    def test_resend_login_otp_success(self, api_client, mocker):
        """
        Verify that a user can resend their login OTP if a session exists.
        """
        mock_send = mocker.patch('users.views.auth.send_user_verification_otp.delay')
        user = NormalUserFactory(is_active=True, is_email_verified=True)
        # Session must exist
        cache.set(f"login_otp:{user.id}", {"otp": "111111"}, timeout=300)
        
        url = reverse('resend_login_otp')
        payload = {"username": user.username}
        
        response = api_client.post(url, payload)
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "new OTP has been sent" in response.data["message"]
        mock_send.assert_called_once()

    def test_resend_verification_link_success(self, api_client, mocker):
        """
        Verify that an unverified user can request a fresh verification link.
        """
        mock_send = mocker.patch('users.views.auth.send_verification_link_email.delay')
        user = NormalUserFactory(is_active=False, is_email_verified=False)
        
        url = reverse('resend_verification_link')
        payload = {"email": user.email}
        
        response = api_client.post(url, payload)
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "Verification link has been resent" in response.data["message"]
        mock_send.assert_called_once()
