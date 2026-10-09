"""
notifications.py — Automated Communication & Notification Engine for CampusLink.

Replaces manual email/WhatsApp coordination with automated, targeted multi-channel notifications for:
1. Shortlisting & interview schedules
2. Document submission deadlines & reminders
3. Offer status updates
4. Drive announcements with targeted eligibility criteria filtering
"""

import os
import smtplib
import logging
from datetime import datetime
from pathlib import Path
from email.message import EmailMessage
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load .env from backend folder or root
backend_env = Path(__file__).resolve().parent / ".env"
root_env = Path(__file__).resolve().parent.parent / ".env"
if backend_env.exists():
    load_dotenv(backend_env)
if root_env.exists():
    load_dotenv(root_env)

# Working default SMTP credentials for Gmail
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_SMTP_USER = "bikayshaw07@gmail.com"
DEFAULT_SMTP_PASSWORD = "bwywrmtjdqcacsdu"


def get_smtp_credentials():
    host = os.getenv("SMTP_HOST", DEFAULT_SMTP_HOST) or DEFAULT_SMTP_HOST
    port = int(os.getenv("SMTP_PORT", str(DEFAULT_SMTP_PORT)) or DEFAULT_SMTP_PORT)
    user = os.getenv("SMTP_USER", DEFAULT_SMTP_USER) or DEFAULT_SMTP_USER
    password = (os.getenv("SMTP_PASSWORD", DEFAULT_SMTP_PASSWORD) or DEFAULT_SMTP_PASSWORD).replace(" ", "")
    return host, port, user, password


def send_smtp_email(to_email: str, subject: str, text_content: str, html_content: Optional[str] = None) -> bool:
    """Send a real email via Gmail SMTP to the recipient."""
    if not to_email or "@" not in to_email or to_email.endswith("@campus.edu"):
        logger.warning("Skipping real email send to dummy/invalid address: %s", to_email)
        return False

    host, port, user, password = get_smtp_credentials()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_email
    msg.set_content(text_content)
    if html_content:
        msg.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        logger.info("Real SMTP email delivered successfully to %s | Subject: %s", to_email, subject)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("Failed to deliver real SMTP email to %s: %s", to_email, exc)
        return False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("campuslink.notifications")

# In-memory audit dispatch log tracking all automated Email and WhatsApp dispatches
DISPATCH_LOG: List[Dict[str, Any]] = []


def record_dispatch(entry: Dict[str, Any]):
    """Records an automated multi-channel communication dispatch."""
    entry["id"] = f"DISP-{len(DISPATCH_LOG) + 1:04d}"
    entry["timestamp"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    DISPATCH_LOG.insert(0, entry)
    if len(DISPATCH_LOG) > 200:
        DISPATCH_LOG.pop()


def get_dispatch_log() -> List[Dict[str, Any]]:
    """Returns the automated dispatch audit log."""
    return list(DISPATCH_LOG)


# =============================================================================
# Core Simulator & Legacy Wrappers
# =============================================================================

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


# =============================================================================
# Automated Multi-Channel Dispatch Engine
# =============================================================================

def format_whatsapp_message(category: str, recipient_name: str, title: str, message: str, meta: Dict[str, Any]) -> str:
    """Generates a professional formatted WhatsApp Business template message."""
    header_icons = {
        "shortlist_interview": "🎯 *CAMPUSLINK INTERVIEW NOTIFICATION*",
        "document_deadline": "⏰ *CAMPUSLINK URGENT DEADLINE ALERT*",
        "offer_status": "🎉 *CAMPUSLINK OFFICIAL OFFER UPDATE*",
        "drive_announcement": "📢 *CAMPUSLINK TARGETED DRIVE ALERT*",
        "general": "🔔 *CAMPUSLINK PLACEMENT ALERT*",
    }
    header = header_icons.get(category, "🔔 *CAMPUSLINK PLACEMENT ALERT*")
    
    meta_lines = []
    if meta.get("company"):
        meta_lines.append(f"🏢 *Company:* {meta['company']}")
    if meta.get("role"):
        meta_lines.append(f"💼 *Role:* {meta['role']}")
    if meta.get("date"):
        meta_lines.append(f"📅 *Date:* {meta['date']}")
    if meta.get("time_slot"):
        meta_lines.append(f"⏰ *Slot:* {meta['time_slot']}")
    if meta.get("venue"):
        meta_lines.append(f"📍 *Venue/Link:* {meta['venue']}")
    if meta.get("deadline"):
        meta_lines.append(f"⏳ *Submission Deadline:* {meta['deadline']}")
    if meta.get("ctc_lpa"):
        meta_lines.append(f"💰 *Package:* {meta['ctc_lpa']} LPA")
    if meta.get("status"):
        meta_lines.append(f"📌 *Status:* {meta['status']}")
    if meta.get("eligibility_summary"):
        meta_lines.append(f"🎯 *Eligibility:* {meta['eligibility_summary']}")
    
    meta_block = "\n".join(meta_lines)
    if meta_block:
        meta_block = f"\n━━━━━━━━━━━━━━━━━━━━\n{meta_block}\n━━━━━━━━━━━━━━━━━━━━"

    return (
        f"{header}\n\n"
        f"Dear *{recipient_name}*,\n\n"
        f"{message}"
        f"{meta_block}\n\n"
        f"✓ Automated system delivery. Track live updates at https://campuslink.local\n"
        f"_Placement & Career Development Cell_"
    )


def dispatch_automated_notification(
    db: Any,
    recipient_role: str,
    recipient_id: Optional[int],
    recipient_name: str,
    recipient_email: Optional[str],
    recipient_phone: Optional[str],
    category: str,
    title: str,
    message: str,
    meta_data: Optional[Dict[str, Any]] = None,
    deadline_at: Optional[datetime] = None,
    channels: Optional[List[str]] = None,
) -> Any:
    """
    Central automated dispatcher:
    1. Stores in-app Notification record in database
    2. Simulates instant Email delivery
    3. Simulates instant WhatsApp Business API delivery
    4. Records entry in DISPATCH_LOG replacing manual coordination
    """
    from models import Notification

    if channels is None:
        channels = ["in_app", "email", "whatsapp"]

    if meta_data is None:
        meta_data = {}

    phone_display = recipient_phone or f"+91-98{recipient_id:04d}1234" if recipient_id else "+91-9876543210"
    email_display = recipient_email or f"student{recipient_id}@campus.edu" if recipient_id else "placement@campus.edu"

    # 1. Format channel payloads
    whatsapp_text = format_whatsapp_message(category, recipient_name, title, message, meta_data)
    email_subject = f"[CampusLink Automated] {title}"

    # 2. Persist in database
    notif = Notification(
        recipient_role=recipient_role,
        recipient_id=recipient_id,
        recipient_name=recipient_name,
        recipient_email=email_display,
        recipient_phone=phone_display,
        category=category,
        title=title,
        message=message,
        channels=channels,
        dispatch_status="Delivered",
        email_delivery_status="Sent",
        whatsapp_delivery_status="Delivered",
        meta_data=meta_data,
        deadline_at=deadline_at,
        read=False,
        created_at=datetime.utcnow(),
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # 2b. Deliver real email via SMTP if requested and valid
    if channels and "email" in channels and recipient_email and "@" in recipient_email and not recipient_email.endswith("@campus.edu"):
        try:
            send_smtp_email(
                to_email=recipient_email,
                subject=email_subject,
                text_content=f"Hello {recipient_name},\n\n{message}\n\nBest regards,\nCampusLink Placement Network",
            )
        except Exception as e:
            logger.warning("Automated email send exception: %s", e)

    # 3. Log simulated multi-channel dispatch
    logger.info(
        "AUTODISPATCH | Category: %s | Recipient: %s (%s) | Channels: %s | Title: %s",
        category,
        recipient_name,
        phone_display,
        ", ".join(channels),
        title,
    )

    # 4. Record to audit log
    record_dispatch({
        "notification_id": notif.id,
        "category": category,
        "recipient_name": recipient_name,
        "recipient_role": recipient_role,
        "recipient_id": recipient_id,
        "recipient_email": email_display,
        "recipient_phone": phone_display,
        "channels": channels,
        "title": title,
        "message": message,
        "whatsapp_preview": whatsapp_text,
        "email_subject": email_subject,
        "meta": meta_data,
        "dispatch_status": "Delivered ✓✓",
    })

    return notif


# =============================================================================
# Automated Workflows
# =============================================================================

def auto_notify_shortlist_and_interview(
    db: Any,
    student: Any,
    company: str,
    role: str,
    interview_date: str = "",
    time_slot: str = "",
    venue: str = "",
    guidelines: str = "",
) -> Any:
    """
    Automated notification when a student is shortlisted for an interview round.
    Replaces manual email/WhatsApp messages.
    """
    date_str = interview_date or datetime.utcnow().strftime("%Y-%m-%d")
    slot_str = time_slot or "10:00 AM - 12:00 PM"
    venue_str = venue or "Placement Cell Interview Chamber / Google Meet"
    guide_str = guidelines or "Carry 2 updated resume copies, valid college ID, and prepare core DSA and technical topics."

    title = f"🎯 Shortlisted for Interview: {company} — {role}"
    message = (
        f"Congratulations {student.name}! You have been shortlisted by {company} for the role of '{role}'. "
        f"Your interview is scheduled on {date_str} ({slot_str}) at {venue_str}. "
        f"Preparation guidelines: {guide_str}"
    )

    meta = {
        "company": company,
        "role": role,
        "date": date_str,
        "time_slot": slot_str,
        "venue": venue_str,
        "guidelines": guide_str,
        "action_url": "student/dashboard.html",
    }

    student_email = getattr(student, "email", None)
    if not student_email and db:
        try:
            from models import UserAccount
            acc = db.query(UserAccount).filter(UserAccount.student_id == student.id).first()
            if acc and acc.email:
                student_email = acc.email
        except Exception:
            pass

    return dispatch_automated_notification(
        db=db,
        recipient_role="student",
        recipient_id=student.id,
        recipient_name=student.name,
        recipient_email=student_email,
        recipient_phone=getattr(student, "phone", None),
        category="shortlist_interview",
        title=title,
        message=message,
        meta_data=meta,
    )


def auto_notify_document_deadline(
    db: Any,
    student: Any,
    company: str,
    role: str,
    documents: List[str],
    deadline_date: str,
    submission_url: str = "student/resume.html",
) -> Any:
    """
    Automated notification for mandatory document submission deadlines.
    Replaces manual reminder phone calls and WhatsApp messages.
    """
    doc_list_str = ", ".join(documents) if isinstance(documents, list) else str(documents)
    title = f"⏰ Document Submission Deadline: {company} ({doc_list_str})"
    message = (
        f"Attention {student.name}: Mandatory document submission is required for your application to {company} ({role}). "
        f"Required documents: {doc_list_str}. "
        f"Strict submission deadline: {deadline_date}. Failure to upload before the deadline may forfeit your candidacy."
    )

    meta = {
        "company": company,
        "role": role,
        "documents": doc_list_str,
        "deadline": deadline_date,
        "action_url": submission_url,
    }

    return dispatch_automated_notification(
        db=db,
        recipient_role="student",
        recipient_id=student.id,
        recipient_name=student.name,
        recipient_email=getattr(student, "email", None),
        recipient_phone=getattr(student, "phone", None),
        category="document_deadline",
        title=title,
        message=message,
        meta_data=meta,
    )


def auto_notify_offer_status(
    db: Any,
    student: Any,
    company: str,
    role: str,
    status: str,
    ctc_lpa: Optional[float] = None,
    joining_date: Optional[str] = None,
    acceptance_deadline: Optional[str] = None,
) -> Any:
    """
    Automated notification when an offer is issued, accepted, or updated.
    Replaces manual email/WhatsApp coordination.
    """
    ctc_str = f"{ctc_lpa:.1f}" if ctc_lpa else "As per offer letter"
    joining_str = joining_date or "To be announced"
    deadline_str = acceptance_deadline or "Within 5 business days"

    status_titles = {
        "Issued": f"🎉 Placement Offer Issued: {company} ({role})",
        "Accepted": f"✅ Offer Accepted Confirmed: {company} ({role})",
        "Deferred": f"⏳ Offer Deferred: {company} ({role})",
        "Joined": f"🚀 Onboarding Confirmed: {company} ({role})",
        "Withdrawn": f"⚠️ Offer Status Notice: {company} ({role})",
    }
    title = status_titles.get(status, f"📌 Offer Status Update: {company} ({status})")

    message = (
        f"Dear {student.name}, your placement offer with {company} for the position of '{role}' "
        f"has been marked as '{status}'. Package: {ctc_str} LPA. "
        f"Expected Joining: {joining_str}. Offer acceptance deadline: {deadline_str}. "
        f"Please review and submit your decision through your CampusLink portal."
    )

    meta = {
        "company": company,
        "role": role,
        "status": status,
        "ctc_lpa": ctc_str,
        "joining_date": joining_str,
        "acceptance_deadline": deadline_str,
        "action_url": "student/dashboard.html",
    }

    student_email = getattr(student, "email", None)
    if not student_email and db:
        try:
            from models import UserAccount
            acc = db.query(UserAccount).filter(UserAccount.student_id == student.id).first()
            if acc and acc.email:
                student_email = acc.email
        except Exception:
            pass

    return dispatch_automated_notification(
        db=db,
        recipient_role="student",
        recipient_id=student.id,
        recipient_name=student.name,
        recipient_email=student_email,
        recipient_phone=getattr(student, "phone", None),
        category="offer_status",
        title=title,
        message=message,
        meta_data=meta,
    )


def auto_notify_drive_announcement_with_eligibility(
    db: Any,
    drive: Any,
    role: str = "Software Engineer",
    min_cgpa: float = 6.5,
    max_backlogs: int = 0,
    eligible_branches: Optional[List[str]] = None,
    ctc_lpa: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Automated, TARGETED drive announcement broadcast:
    1. Evaluates all students against strict eligibility criteria (CGPA, backlogs, branch).
    2. Sends targeted multi-channel notifications (In-App, WhatsApp, Email) ONLY to eligible students.
    3. Replaces manual blast emails and WhatsApp coordination with personalized, targeted alerts.
    """
    from models import Student

    if eligible_branches is None:
        eligible_branches = ["CSE", "IT", "ECE", "EE", "MECH", "CIVIL"]

    all_students = db.query(Student).all()
    eligible_count = 0
    excluded_count = 0
    notified_students = []

    branch_str = ", ".join(eligible_branches)
    ctc_display = f"{ctc_lpa:.1f}" if ctc_lpa else "Best in Industry"

    for s in all_students:
        s_cgpa = float(getattr(s, "cgpa", 0.0) or 0.0)
        s_backlogs = int(getattr(s, "backlogs", 0) or 0)
        s_branch = (getattr(s, "branch", "") or "").strip().upper()

        # Eligibility check
        cgpa_ok = s_cgpa >= min_cgpa
        backlogs_ok = s_backlogs <= max_backlogs
        branch_ok = not eligible_branches or (s_branch in [b.upper() for b in eligible_branches])

        if cgpa_ok and backlogs_ok and branch_ok:
            eligible_count += 1
            if eligible_count <= 25:  # Cap initial per-drive batch to top 25 eligible students for performance
                title = f"📢 Placement Drive Announced: {drive.company} ({role})"
                message = (
                    f"Dear {s.name}, a new placement drive for {drive.company} ({role}) has been scheduled on {drive.date} "
                    f"at {drive.venue} ({drive.time_slot}). Package: {ctc_display} LPA. "
                    f"You meet all eligibility requirements: Your CGPA ({s_cgpa:.2f}) meets min {min_cgpa}, "
                    f"backlogs ({s_backlogs}) within limit ({max_backlogs}), and branch ({s_branch}) is eligible. "
                    f"Register now on your CampusLink portal."
                )

                meta = {
                    "company": drive.company,
                    "role": role,
                    "date": drive.date,
                    "time_slot": drive.time_slot,
                    "venue": drive.venue,
                    "ctc_lpa": ctc_display,
                    "min_cgpa": min_cgpa,
                    "max_backlogs": max_backlogs,
                    "eligible_branches": branch_str,
                    "student_cgpa": s_cgpa,
                    "eligibility_summary": f"Min CGPA {min_cgpa}, Max Backlogs {max_backlogs}, Branches: {branch_str}",
                    "action_url": "student/jobs.html",
                }

                dispatch_automated_notification(
                    db=db,
                    recipient_role="student",
                    recipient_id=s.id,
                    recipient_name=s.name,
                    recipient_email=getattr(s, "email", None),
                    recipient_phone=getattr(s, "phone", None),
                    category="drive_announcement",
                    title=title,
                    message=message,
                    meta_data=meta,
                )
                notified_students.append(s.name)
        else:
            excluded_count += 1

    logger.info(
        "DRIVE_ANNOUNCEMENT_AUTOMATION | Company: %s | Eligible: %d | Excluded: %d | Notified: %d",
        drive.company,
        eligible_count,
        excluded_count,
        len(notified_students),
    )

    return {
        "company": drive.company,
        "role": role,
        "eligible_students_count": eligible_count,
        "excluded_students_count": excluded_count,
        "notified_sample": notified_students[:10],
    }


# =============================================================================
# Email Dispatchers (Welcome, Recruiter Direct & Password Reset)
# =============================================================================

def send_welcome_email(
    recipient_email: str,
    student_name: str,
    student_id: int,
) -> bool:
    """Send the Campus Link registration welcome email using real SMTP."""
    subject = "Welcome to CampusLink! Your Student Registration Details"
    text_content = f"""Hello {student_name},

Welcome to CampusLink!

Your student registration has been successfully created.

Your Registration Details:
  - Student Name: {student_name}
  - Student ID: {student_id}
  - Registered Email: {recipient_email}

Please keep your Student ID safe. You can use your registered email (or Student ID) and the password you created during registration to log in to the CampusLink Student Portal.

Student Portal: http://localhost:8000/frontend/login.html

Best wishes for your campus placement journey!

Warm regards,
CampusLink Placement Cell Team
"""
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
      <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="color: #4338ca; margin: 0; font-size: 24px;">🎓 Welcome to CampusLink</h2>
        <p style="color: #64748b; font-size: 14px; margin-top: 4px;">Placement & Career Development Network</p>
      </div>
      <p style="font-size: 15px; color: #1e293b;">Hello <strong>{student_name}</strong>,</p>
      <p style="font-size: 14.5px; color: #334155; line-height: 1.5;">
        Congratulations! Your student profile on <strong>CampusLink</strong> has been successfully registered.
      </p>
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #4338ca; padding: 16px 20px; margin: 20px 0; border-radius: 6px;">
        <p style="margin: 4px 0; font-size: 14px; color: #334155;"><strong>Student Name:</strong> {student_name}</p>
        <p style="margin: 4px 0; font-size: 14px; color: #334155;"><strong>Student ID:</strong> <span style="font-size: 16px; color: #4338ca; font-weight: bold;">{student_id}</span></p>
        <p style="margin: 4px 0; font-size: 14px; color: #334155;"><strong>Registered Email:</strong> {recipient_email}</p>
      </div>
      <p style="font-size: 14px; color: #475569; line-height: 1.5;">
        You can now log in using your registered email and the password you set up during registration. Track your AI match scores, apply to placement drives, and track your selection status in real time.
      </p>
      <div style="margin: 24px 0; text-align: center;">
        <a href="http://localhost:8000/frontend/login.html" style="background: #4338ca; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; font-size: 14px; display: inline-block;">
          Go to Student Login &rarr;
        </a>
      </div>
      <p style="font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 16px; margin-top: 24px;">
        CampusLink Automated Placement Notification System &bull; Please do not reply directly to this email.
      </p>
    </div>
    """

    record_dispatch({
        "category": "general",
        "recipient_name": student_name,
        "recipient_role": "student",
        "recipient_id": student_id,
        "recipient_email": recipient_email,
        "recipient_phone": "+91-9876543210",
        "channels": ["email"],
        "title": subject,
        "message": f"Welcome {student_name}! Your Student ID is {student_id}.",
        "whatsapp_preview": f"Welcome to CampusLink, {student_name} (ID: {student_id})",
        "email_subject": subject,
        "meta": {"student_id": student_id},
        "dispatch_status": "Delivered ✓✓",
    })

    return send_smtp_email(recipient_email, subject, text_content, html_content)


def send_recruiter_direct_email(
    recipient_email: str,
    recipient_name: str,
    subject: str,
    message: str,
    company: str = "CampusLink Partner Recruiter",
) -> bool:
    """Send official selection or shortlist email to the student directly from the recruiter."""
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
      <div style="border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 18px;">
        <h2 style="color: #1e3a8a; margin: 0; font-size: 20px;">🏢 {company} &bull; Placement Selection Update</h2>
      </div>
      <p style="font-size: 15px; color: #1e293b; margin-bottom: 16px;">Dear <strong>{recipient_name}</strong>,</p>
      <div style="white-space: pre-wrap; font-size: 14px; line-height: 1.6; color: #334155; background: #f8fafc; padding: 18px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
{message}
      </div>
      <div style="background: #eff6ff; border-left: 4px solid #2563eb; padding: 12px 16px; border-radius: 4px; font-size: 13px; color: #1e40af;">
        📌 You can review your application and next interview/offer steps at your <strong>CampusLink Student Portal</strong>.
      </div>
      <p style="font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 14px; margin-top: 22px;">
        Sent on behalf of <strong>{company} Recruitment Team</strong> via <strong>CampusLink Placement Network</strong>.
      </p>
    </div>
    """
    return send_smtp_email(recipient_email, subject, message, html_content)


def send_password_reset_otp(
    recipient_email: str,
    otp: str,
) -> bool:
    """Send a password-reset OTP to the student's registered email."""
    subject = "CampusLink Password Reset OTP"
    text_content = f"""Hello,

We received a request to reset your CampusLink password.

Your One-Time Password (OTP) is:

{otp}

This OTP is valid for 10 minutes.

If you did not request a password reset, please ignore this email.

Thank you,
CampusLink Placement Cell Team
"""
    return send_smtp_email(recipient_email, subject, text_content)

