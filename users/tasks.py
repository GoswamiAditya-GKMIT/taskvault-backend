from celery import shared_task
from django.core.mail import send_mail


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 10})
def send_user_verification_otp(self, email, otp):
    send_mail(
        subject="Verify your TaskVault account",
        message=f"Your OTP for account verification is {otp}. It is valid for 5 minutes.",
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