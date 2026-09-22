import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# State file location
STATE_FILE_PATH = os.getenv("STATE_FILE_PATH", str(BASE_DIR / "agent_state.json"))

# Alert window: Number of days prior to deadline to send daily alerts
ALERT_WINDOW_DAYS = int(os.getenv("ALERT_WINDOW_DAYS", "14"))

# Gmail API Credentials & Tokens
GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", str(BASE_DIR / "credentials.json"))
GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", str(BASE_DIR / "token.json"))

# Optional SMTP / IMAP direct credentials fallback
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

# Email Addresses
TARGET_EMAIL = os.getenv("TARGET_EMAIL", "orogjay@gmail.com")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "orogjay@gmail.com")
USER_EMAIL = os.getenv("USER_EMAIL", "orogjay@gmail.com")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", TARGET_EMAIL)

# Payment confirmation keywords to search for in email body/subject
CONFIRMATION_KEYWORDS = [
    "paid", "confirm", "confirmed", "filed", "payment done", "settled", "payment complete"
]
