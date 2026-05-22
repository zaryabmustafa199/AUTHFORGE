"""
Email utility — sends emails via SMTP.

Supports both MailHog (dev, no auth/TLS) and production SMTP
providers (SendGrid, AWS SES, Gmail — with auth + TLS).
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

# Connection timeout — prevents hanging if SMTP server is unreachable
SMTP_TIMEOUT_SECONDS = 10


def send_email_sync(to_email: str, subject: str, html_body: str) -> None:
    """
    Sends an email synchronously. Designed to be called from Celery tasks
    (which run in their own process, not the async event loop).

    Raises:
        smtplib.SMTPException: On any SMTP-level failure (connection,
            auth, recipient rejected, etc.)
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_FROM
    msg["To"] = to_email

    msg.attach(MIMEText(html_body, "html"))

    if settings.MAIL_USE_TLS:
        # Production SMTP — TLS + authentication
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
            server.starttls(context=context)
            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.sendmail(settings.MAIL_FROM, to_email, msg.as_string())
    else:
        # Development SMTP (MailHog) — no auth, no TLS
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
            server.sendmail(settings.MAIL_FROM, to_email, msg.as_string())
