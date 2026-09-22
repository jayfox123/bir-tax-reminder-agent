# Autonomous BIR Tax Compliance & Reminder Agent

An autonomous Python agent that monitors Philippine Bureau of Internal Revenue (BIR) tax deadlines for **BIR Form 2551Q** (Quarterly Percentage Tax) and **BIR Form 1701Q** (Quarterly Income Tax for Individuals/Sole Proprietors), sends daily email reminder notifications within the alert window, and automatically processes email replies to reset and advance tax filing schedules.

---

## Tax Reference Schedules & Rules

1. **BIR Form 2551Q (Quarterly Percentage Tax)**:
   - **Q1:** April 25
   - **Q2:** July 25
   - **Q3:** October 25
   - **Q4:** January 25 (succeeding calendar year)

2. **BIR Form 1701Q (Quarterly Income Tax)**:
   - **Q1:** May 15
   - **Q2:** August 15
   - **Q3:** November 15
   - *(Note: Q4 is incorporated into the Annual 1701/1701A return due April 15 of the following year).*

3. **Weekend / Holiday Rollover Rule**:
   - If an official deadline falls on a Saturday, Sunday, or official Philippine national holiday, the statutory deadline is rolled forward to the next regular business day.

---

## Core State Model (`agent_state.json`)

The agent maintains persistent state in `agent_state.json`:

```json
{
  "2551Q": {
    "current_quarter": "Q3",
    "target_year": 2026,
    "paid": false
  },
  "1701Q": {
    "current_quarter": "Q3",
    "target_year": 2026,
    "paid": false
  },
  "last_thread_id": null,
  "last_notified_date": null
}
```

---

## Installation & Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration (`.env`)**:
   Create a `.env` file or export environment variables:
   ```env
   RECIPIENT_EMAIL=your_email@example.com
   ALERT_WINDOW_DAYS=14

   # Optional Gmail OAuth Credentials path
   GMAIL_CREDENTIALS_PATH=credentials.json

   # Optional SMTP/IMAP App Password Fallback
   SENDER_EMAIL=your_gmail@gmail.com
   APP_PASSWORD=your_app_password
   ```

---

## CLI Usage

### Check Agent Status & Upcoming Deadlines
```bash
python main.py status
```

### Run Daily Compliance Check
```bash
python main.py run
```

### Simulate Date Execution (e.g. October 20, 2026)
```bash
python main.py simulate --date 2026-10-20
```

### Manually Mark Form as Paid & Advance Quarter
```bash
python main.py mark-paid --form 2551Q
```

### Check Inbox for Payment Replies
```bash
python main.py check-replies
```

---

## Running Automated Tests

Run pytest to verify deadline rollover, quarter transition logic, and state management:
```bash
pytest
```
