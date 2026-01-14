from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_otp_email(email, otp):
    send_mail(
        subject="Verify your email - TaskVault",
        message=f"Your OTP for email verification is {otp}. It is valid for 5 minutes.",
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )
