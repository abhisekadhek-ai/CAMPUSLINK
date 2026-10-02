"""
notifications.py — Notification simulator for CampusLink.

In a real system this would send emails/SMS/push notifications. For the
prototype it just logs a message with a timestamp — but every call site
is already wired up in main.py, so swapping in a real email/SMS service
later only means changing what's inside notify(), not every place that
calls it.
"""

import os
import smtplib
import logging
from pathlib import Path
from email.message import EmailMessage
from dotenv import load_dotenv

# Load .env from the backend folder
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("campuslink.notifications")

def notify(recipient: str, event: str) -> str:
    """Core simulator: logs 'Notification sent to [recipient] about [event]'."""
    message = f"Notification sent to {recipient} about {event}"
    logger.info(message)
    return message


def notify_shortlist(student_name: str, role: str, company: str) -> str:
    return notify(student_name, f"being shortlisted for '{role}' at {company}")


def notify_drive_announcement(company: str, role: str, date: str, venue: str) -> str:
    return notify(
        "all eligible students",
        f"a new drive announcement: {company} ({role}) on {date} at {venue}",
    )


def notify_offer_status(student_name: str, status: str, company: str) -> str:
    return notify(student_name, f"their offer status changing to '{status}' at {company}")






def send_welcome_email(
    recipient_email: str,
    student_name: str,
    student_id: int,
) -> bool:
    """Send the Campus Link registration welcome email."""

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_host, smtp_user, smtp_password]):
        logging.error("Email settings are missing from .env")
        return False

    msg = EmailMessage()
    msg["Subject"] = "Welcome to Campus Link!"
    msg["From"] = smtp_user
    msg["To"] = recipient_email

    msg.set_content(
        f"""Hello {student_name},

Welcome to Campus Link!

Your student registration has been received.

Your Student ID is: {student_id}

Please keep your Student ID safe. Use the password
you created during registration to log in.

Thank you,
Campus Link Team
"""
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logging.info("Welcome email sent to %s", recipient_email)
        return True

    except (OSError, smtplib.SMTPException) as exc:
        logging.exception("Could not send welcome email: %s", exc)
        return False

def send_password_reset_otp(
    recipient_email: str,
    otp: str,
) -> bool:
    """Send a password-reset OTP to the student's registered email."""

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_host, smtp_user, smtp_password]):
        logging.error("Email settings are missing from .env")
        return False

    msg = EmailMessage()
    msg["Subject"] = "Campus Link Password Reset OTP"
    msg["From"] = smtp_user
    msg["To"] = recipient_email

    msg.set_content(
        f"""Hello,

We received a request to reset your Campus Link password.

Your OTP is:

{otp}

This OTP is valid for 10 minutes.

If you did not request a password reset, please ignore this email.

Thank you,
Campus Link Team
"""
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logging.info("Password reset OTP sent to %s", recipient_email)
        return True

    except (OSError, smtplib.SMTPException) as exc:
        logging.exception(
            "Could not send password reset OTP: %s",
            exc,
        )
        return False
