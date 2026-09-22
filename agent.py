import datetime
import logging
from typing import Optional, Dict, Any, List

import config
from state_manager import StateManager
from deadline_calculator import DeadlineCalculator
from email_service import EmailService

logger = logging.getLogger("bir_agent.core")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

class TaxReminderAgent:
    """Core BIR Tax Compliance & Reminder Agent."""

    def __init__(self, state_file_path: Optional[str] = None):
        self.state_manager = StateManager(state_file_path)
        self.deadline_calculator = DeadlineCalculator()
        self.email_service = EmailService()

    def check_and_process_replies(self) -> Dict[str, bool]:
        """Checks inbox for user replies confirming tax payments for unpaid forms."""
        results = {}
        last_thread_id = self.state_manager.state.get("last_thread_id")

        for form_type in ["2551Q", "1701Q"]:
            form_state = self.state_manager.state.get(form_type, {})
            if not form_state.get("paid", False):
                quarter = form_state.get("current_quarter", "Q1")
                target_year = form_state.get("target_year", datetime.date.today().year)

                logger.info(f"Checking replies for {form_type} {quarter} {target_year}...")
                is_confirmed = self.email_service.check_for_payment_replies(
                    form_type=form_type,
                    quarter=quarter,
                    target_year=target_year,
                    last_thread_id=last_thread_id
                )

                if is_confirmed:
                    logger.info(f"Payment confirmed for {form_type} {quarter} {target_year}! Marking as paid and advancing quarter...")
                    self.state_manager.mark_as_paid(form_type)
                    self.state_manager.advance_quarter(form_type)
                    results[form_type] = True
                else:
                    results[form_type] = False
            else:
                results[form_type] = False

        return results

    def run_daily_check(self, current_date: Optional[datetime.date] = None, recipient_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """Main daily execution check.

        1. Process reply emails for payment confirmation.
        2. Evaluate upcoming tax deadlines.
        3. Dispatch reminder emails if within alert window and unpaid.
        """
        if current_date is None:
            current_date = datetime.date.today()

        recipient = recipient_email or config.TARGET_EMAIL or config.RECIPIENT_EMAIL or config.USER_EMAIL
        logger.info(f"Running daily tax compliance check for date: {current_date}")

        # Step 1: Process replies
        self.check_and_process_replies()

        actions_taken = []
        date_str = current_date.isoformat()

        # Step 2: Check deadlines for each form
        for form_type in ["2551Q", "1701Q"]:
            form_state = self.state_manager.state.get(form_type, {})
            quarter = form_state.get("current_quarter")
            target_year = form_state.get("target_year")
            paid = form_state.get("paid", False)

            if paid:
                logger.info(f"{form_type} {quarter} {target_year} is already marked as PAID. Skipping alert.")
                actions_taken.append({
                    "form_type": form_type,
                    "quarter": quarter,
                    "target_year": target_year,
                    "status": "PAID_SKIPPED"
                })
                continue

            is_in_window, days_left, adjusted_deadline = self.deadline_calculator.is_within_alert_window(
                current_date=current_date,
                form_type=form_type,
                quarter=quarter,
                target_year=target_year,
                alert_window_days=config.ALERT_WINDOW_DAYS
            )

            if is_in_window:
                logger.info(f"ALERT WINDOW ACTIVE: {form_type} {quarter} {target_year} due on {adjusted_deadline} ({days_left} days left).")

                # Format Subject & Body
                subject = f"[BIR TAX REMINDER] Form {form_type} {quarter} {target_year} Payment Due on {adjusted_deadline}"

                days_desc = "TODAY!" if days_left == 0 else (f"in {days_left} days" if days_left > 0 else f"OVERDUE by {abs(days_left)} days!")

                body_plain = (
                    f"BIR Tax Compliance Alert\n"
                    f"------------------------\n"
                    f"Form: BIR Form {form_type}\n"
                    f"Quarter: {quarter}\n"
                    f"Tax Year: {target_year}\n"
                    f"Adjusted Deadline: {adjusted_deadline} ({days_desc})\n\n"
                    f"Action Required: Please file and pay your tax return on or before the deadline.\n"
                    f"Once paid, reply to this email with 'PAID' or 'CONFIRMED' to automatically update your tax schedule.\n"
                )

                body_html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                        <h2 style="color: #d9534f; margin-top: 0;">BIR Tax Compliance Alert</h2>
                        <p>This is a reminder for your upcoming Philippine BIR tax deadline:</p>
                        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                            <tr style="background-color: #f8f9fa;">
                                <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Form Type:</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">BIR Form {form_type}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Quarter / Period:</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{quarter} ({target_year})</td>
                            </tr>
                            <tr style="background-color: #f8f9fa;">
                                <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Adjusted Filing Deadline:</td>
                                <td style="padding: 10px; border: 1px solid #ddd; color: #d9534f; font-weight: bold;">{adjusted_deadline} ({days_desc})</td>
                            </tr>
                        </table>
                        <div style="background-color: #e9f5ff; border-left: 4px solid #007bff; padding: 12px; margin-bottom: 20px;">
                            <strong>Automatic Schedule Reset:</strong> Once you have filed & paid this return, simply reply to this email with <code>PAID</code> or <code>CONFIRMED</code>. The agent will automatically mark this quarter as completed and advance your schedule.
                        </div>
                    </div>
                </body>
                </html>
                """

                success, thread_id = self.email_service.send_reminder(
                    recipient=recipient,
                    subject=subject,
                    body_text=body_plain,
                    body_html=body_html
                )

                if success:
                    if thread_id:
                        self.state_manager.update_last_thread_id(thread_id)
                    self.state_manager.update_last_notified_date(date_str)
                    actions_taken.append({
                        "form_type": form_type,
                        "quarter": quarter,
                        "target_year": target_year,
                        "status": "ALERT_SENT",
                        "adjusted_deadline": str(adjusted_deadline),
                        "days_left": days_left
                    })
                else:
                    actions_taken.append({
                        "form_type": form_type,
                        "quarter": quarter,
                        "target_year": target_year,
                        "status": "ALERT_FAILED"
                    })
            else:
                logger.info(f"{form_type} {quarter} {target_year} deadline ({adjusted_deadline}) is outside alert window ({days_left} days left).")
                actions_taken.append({
                    "form_type": form_type,
                    "quarter": quarter,
                    "target_year": target_year,
                    "status": "OUTSIDE_WINDOW",
                    "adjusted_deadline": str(adjusted_deadline),
                    "days_left": days_left
                })

        return actions_taken
