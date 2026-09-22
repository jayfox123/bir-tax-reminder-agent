import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple, Optional, List, Dict, Any
import logging

import config

logger = logging.getLogger("bir_agent.email")

# Try importing Google API Client libraries
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import base64
    HAS_GMAIL_API = True
except ImportError:
    HAS_GMAIL_API = False

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

class EmailService:
    """Handles sending tax reminder alerts and monitoring incoming replies via Gmail API or SMTP/IMAP."""

    def __init__(self):
        self.gmail_service = None
        self.mode = "mock"

        # Attempt to initialize Gmail API if credentials exist
        if HAS_GMAIL_API and os.path.exists(config.GMAIL_CREDENTIALS_PATH):
            try:
                self.gmail_service = self._init_gmail_api()
                if self.gmail_service:
                    self.mode = "gmail_api"
            except Exception as e:
                logger.warning(f"Failed to initialize Gmail API: {e}")

        # Fallback to SMTP/IMAP if app password is provided
        if self.mode == "mock" and config.SENDER_EMAIL and config.APP_PASSWORD:
            self.mode = "smtp_imap"

        logger.info(f"EmailService initialized in '{self.mode}' mode (Target user: {config.USER_EMAIL}).")

    def _init_gmail_api(self):
        creds = None
        token_path = config.GMAIL_TOKEN_PATH
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(config.GMAIL_CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)

    def send_reminder(
        self,
        recipient: Optional[str] = None,
        subject: str = "",
        body_text: str = "",
        body_html: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Sends reminder email to target recipient. Returns (success_flag, thread_id)."""
        target = recipient or config.TARGET_EMAIL or config.RECIPIENT_EMAIL or config.USER_EMAIL

        if not target:
            logger.warning("[Mock Email] No recipient specified. Printing alert to stdout:")
            print(f"\n--- [EMAIL ALERT MOCK] ---\nTo: {target}\nSubject: {subject}\n\n{body_text}\n--------------------------\n")
            return True, "mock-thread-id-123"

        if self.mode == "gmail_api":
            return self._send_via_gmail_api(target, subject, body_text, body_html)
        elif self.mode == "smtp_imap":
            return self._send_via_smtp(target, subject, body_text, body_html)
        else:
            logger.info(f"[Mock Mode] Simulating sending email to {target}")
            print(f"\n--- [EMAIL ALERT MOCK] ---\nTo: {target}\nSubject: {subject}\n\n{body_text}\n--------------------------\n")
            return True, "mock-thread-id-123"

    def _send_via_gmail_api(self, recipient: str, subject: str, body_text: str, body_html: Optional[str]) -> Tuple[bool, Optional[str]]:
        try:
            message = MIMEMultipart("alternative")
            message["to"] = recipient
            message["subject"] = subject

            part1 = MIMEText(body_text, "plain")
            message.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, "html")
                message.attach(part2)

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            body = {"raw": raw}

            sent_msg = self.gmail_service.users().messages().send(userId="me", body=body).execute()
            thread_id = sent_msg.get("threadId")
            logger.info(f"Email sent successfully via Gmail API to {recipient}. Thread ID: {thread_id}")
            return True, thread_id
        except Exception as e:
            logger.error(f"Failed to send email via Gmail API: {e}")
            return False, None

    def _send_via_smtp(self, recipient: str, subject: str, body_text: str, body_html: Optional[str]) -> Tuple[bool, Optional[str]]:
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = config.SENDER_EMAIL
            msg["To"] = recipient
            msg["Subject"] = subject

            msg.attach(MIMEText(body_text, "plain"))
            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
                server.starttls()
                server.login(config.SENDER_EMAIL, config.APP_PASSWORD)
                server.sendmail(config.SENDER_EMAIL, recipient, msg.as_string())

            logger.info(f"Email sent successfully via SMTP to {recipient}")
            return True, "smtp-thread-id"
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return False, None

    def check_for_payment_replies(
        self,
        form_type: str,
        quarter: str,
        target_year: int,
        last_thread_id: Optional[str] = None
    ) -> bool:
        """Checks inbox for replies confirming tax payment for the specified form & quarter.
        
        Enforces authorized sender validation: message must originate from config.USER_EMAIL.
        """
        keywords = config.CONFIRMATION_KEYWORDS
        authorized_email = config.USER_EMAIL.strip().lower()

        if self.mode == "gmail_api":
            return self._check_replies_gmail_api(form_type, quarter, target_year, last_thread_id, keywords, authorized_email)
        elif self.mode == "smtp_imap":
            return self._check_replies_imap(form_type, quarter, target_year, keywords, authorized_email)
        else:
            logger.info("[Mock Mode] No active Gmail/IMAP connection. Reply check skipped.")
            return False

    def _check_replies_gmail_api(
        self,
        form_type: str,
        quarter: str,
        target_year: int,
        last_thread_id: Optional[str],
        keywords: List[str],
        authorized_email: str
    ) -> bool:
        try:
            query = f"{form_type} {quarter} {target_year}"
            if last_thread_id:
                query = f"threadId:{last_thread_id}"

            results = self.gmail_service.users().messages().list(userId="me", q=query).execute()
            messages = results.get("messages", [])

            for msg_meta in messages:
                msg = self.gmail_service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()
                headers = msg.get("payload", {}).get("headers", [])
                sender_from = next((h.get("value", "") for h in headers if h.get("name", "").lower() == "from"), "")

                # Validate sender matches authorized email
                if authorized_email not in sender_from.lower():
                    logger.info(f"Ignored message {msg_meta['id']} from unauthorized sender: '{sender_from}' (Expected: '{authorized_email}')")
                    continue

                snippet = msg.get("snippet", "").lower()
                body = self._extract_gmail_body(msg).lower()
                content = f"{snippet} {body}"

                for kw in keywords:
                    if kw in content:
                        logger.info(f"Authorized payment confirmation keyword '{kw}' found from sender '{sender_from}' in message {msg_meta['id']}")
                        return True
        except Exception as e:
            logger.error(f"Error checking Gmail API replies: {e}")

        return False

    def _extract_gmail_body(self, msg: Dict[str, Any]) -> str:
        payload = msg.get("payload", {})
        parts = payload.get("parts", [])
        body_str = ""

        if not parts:
            data = payload.get("body", {}).get("data", "")
            if data:
                body_str = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        else:
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body_str += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        return body_str

    def _check_replies_imap(
        self,
        form_type: str,
        quarter: str,
        target_year: int,
        keywords: List[str],
        authorized_email: str
    ) -> bool:
        try:
            mail = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT)
            mail.login(config.SENDER_EMAIL, config.APP_PASSWORD)
            mail.select("inbox")

            search_criterion = f'(SUBJECT "{form_type}")'
            _, data = mail.search(None, search_criterion)
            mail_ids = data[0].split()

            for m_id in mail_ids[-10:]:
                _, msg_data = mail.fetch(m_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        sender_from = msg.get("From", "").lower()

                        if authorized_email not in sender_from:
                            logger.info(f"Ignored IMAP message {m_id} from unauthorized sender: '{sender_from}'")
                            continue

                        subject = msg.get("subject", "").lower()
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        else:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                        content = f"{subject} {body.lower()}"
                        if f"{form_type.lower()}" in content and f"{quarter.lower()}" in content:
                            for kw in keywords:
                                if kw in content:
                                    logger.info(f"Authorized payment confirmation keyword '{kw}' found via IMAP from '{sender_from}' in email ID {m_id}")
                                    mail.logout()
                                    return True
            mail.logout()
        except Exception as e:
            logger.error(f"Error checking IMAP replies: {e}")

        return False
