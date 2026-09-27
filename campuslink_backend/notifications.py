"""
notifications.py — Notification simulator for CampusLink.

In a real system this would send emails/SMS/push notifications. For the
prototype it just logs a message with a timestamp — but every call site
is already wired up in main.py, so swapping in a real email/SMS service
later only means changing what's inside notify(), not every place that
calls it.
"""

import logging

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
