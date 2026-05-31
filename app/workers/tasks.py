"""
Celery background tasks for AuthForge.

All tasks include:
- Automatic retries (3 attempts with exponential backoff)
- Proper logging on success and failure
"""
from celery import shared_task
from app.utils.email import send_email_sync
import logging

logger = logging.getLogger("app.workers.tasks")


@shared_task(
    name="app.workers.tasks.send_verification_email",
    bind=True,
    max_retries=3,
    default_retry_delay=10,  # seconds between retries (exponential: 10, 20, 40)
)
def send_verification_email(self, email: str, otp: str):
    """
    Sends an OTP for email verification.
    Retries up to 3 times on failure with exponential backoff.
    """
    subject = "Verify your AuthForge account"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
        <h2 style="color: #1a1a2e;">Welcome to AuthForge!</h2>
        <p>Please use the following code to verify your email address.</p>
        <div style="background-color: #f0f0f5; padding: 16px; border-radius: 8px; text-align: center; margin: 24px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #1a1a2e;">{otp}</span>
        </div>
        <p style="color: #666; font-size: 14px;">This code expires in <strong>10 minutes</strong>.</p>
        <p style="color: #999; font-size: 12px;">If you didn't create an account, you can safely ignore this email.</p>
    </div>
    """
    try:
        send_email_sync(to_email=email, subject=subject, html_body=html_body)
        logger.info(f"Verification email sent to {email}")
        return f"Verification email sent to {email}"
    except Exception as exc:
        logger.error(f"Failed to send verification email to {email}: {exc}")
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))


from app.config import settings

@shared_task(
    name="app.workers.tasks.send_reset_email",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def send_reset_email(self, email: str, token: str):
    """
    Sends a password reset token as a magic link.
    Retries up to 3 times on failure with exponential backoff.
    """
    import urllib.parse
    encoded_email = urllib.parse.quote(email)
    encoded_token = urllib.parse.quote(token)
    reset_link = f"{settings.FRONTEND_URL}/reset-password?email={encoded_email}&token={encoded_token}"
    
    subject = "Reset your AuthForge password"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
        <h2 style="color: #1a1a2e;">Password Reset Request</h2>
        <p>You requested a password reset. Click the button below to choose a new password.</p>
        <div style="margin: 32px 0; text-align: center;">
            <a href="{reset_link}" style="background-color: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Reset Password</a>
        </div>
        <p style="color: #666; font-size: 14px;">This link expires in <strong>15 minutes</strong>.</p>
        <p style="color: #999; font-size: 12px;">If you didn't request this reset, you can safely ignore this email. Your password will not change.</p>
    </div>
    """
    try:
        send_email_sync(to_email=email, subject=subject, html_body=html_body)
        logger.info(f"Reset email sent to {email}")
        return f"Reset email sent to {email}"
    except Exception as exc:
        logger.error(f"Failed to send reset email to {email}: {exc}")
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))
