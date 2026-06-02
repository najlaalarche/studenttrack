import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

GMAIL_USER = os.environ.get("GMAIL_USER", "studenttrack.esith@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")


def send_email(to: str, subject: str, html: str) -> dict:
    """
    Envoie un email HTML via Gmail SMTP SSL.
    Retourne { success: bool, error: str | None }
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"StudentTrack ESITH <{GMAIL_USER}>"
        msg["To"] = to
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}
