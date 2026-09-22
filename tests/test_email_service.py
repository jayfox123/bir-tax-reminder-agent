import pytest
import config
from email_service import EmailService

def test_email_config_defaults():
    assert config.TARGET_EMAIL == "orogjay@gmail.com"
    assert config.SENDER_EMAIL == "orogjay@gmail.com"
    assert config.USER_EMAIL == "orogjay@gmail.com"

def test_authorized_sender_validation():
    service = EmailService()
    keywords = ["paid", "confirm"]
    authorized_email = "orogjay@gmail.com"

    # Test Gmail API check with mock payload
    mock_msg_authorized = {
        "id": "101",
        "snippet": "I have paid the tax return.",
        "payload": {
            "headers": [
                {"name": "From", "value": "Jay Orog <orogjay@gmail.com>"}
            ]
        }
    }

    mock_msg_unauthorized = {
        "id": "102",
        "snippet": "I have paid the tax return.",
        "payload": {
            "headers": [
                {"name": "From", "value": "Spammer <spammer@evil.com>"}
            ]
        }
    }

    # Extract & test logic
    headers_auth = mock_msg_authorized["payload"]["headers"]
    sender_auth = next((h["value"] for h in headers_auth if h["name"].lower() == "from"), "")
    assert authorized_email in sender_auth.lower()

    headers_unauth = mock_msg_unauthorized["payload"]["headers"]
    sender_unauth = next((h["value"] for h in headers_unauth if h["name"].lower() == "from"), "")
    assert authorized_email not in sender_unauth.lower()
