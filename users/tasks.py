from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

User = get_user_model()


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 10})
def send_user_verification_otp(self, email, otp):
    send_mail(
        subject="Verify your TaskVault account Login",
        message=f"Your OTP for account Login is {otp}. It is valid for 5 minutes.",
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )




@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def send_user_invite_email(self, email, invite_link):
    send_mail(
        subject="You're invited to TaskVault",
        message=f"""
        You have been invited to join TaskVault.

        Click the link below to accept the invitation:
        {invite_link}

        This link will expire in 24 hours.
        """,
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )
    

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def send_password_reset_email(self, email, reset_link):
    send_mail(
        subject="Reset your TaskVault password",
        message=f"""
        You requested a password reset.

        Click the link below to reset your password:
        {reset_link}

        This link will expire in 15 minutes.
        If you did not request this, ignore this email.
        """,
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def send_verification_link_email(self, email, link):
    send_mail(
        subject="Verify your TaskVault account",
        message=f"""
        You have been registered on TaskVault.

        Click the link below to verify your email and activate your account:
        {link}

        This link will expire in 24 hours.
        """,
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )


@shared_task
def hard_delete_unverified_users():
    """
    Task to hard delete users who haven't verified their email within 7 days.
    """
    threshold = timezone.now() - timedelta(days=7)
    unverified_users = User.objects.filter(
        is_email_verified=False,
        date_joined__lt=threshold
    )
    count = unverified_users.count()
    unverified_users.delete()
    return f"Hard deleted {count} unverified users."


@shared_task
def clear_blacklisted_tokens():
    """
    Purge expired blacklisted tokens from the database.
    This uses functionality provided by djangorestframework-simplejwt correctly.
    """
    # Flushes expired tokens from the database
    # OutstandingToken objects where expires_at < now
    now = timezone.now()
    expired_count = OutstandingToken.objects.filter(expires_at__lt=now).count()
    OutstandingToken.objects.filter(expires_at__lt=now).delete()
    return f"Purged {expired_count} expired tokens."