import argparse
import datetime
import json
import sys
from typing import Optional

from agent import TaxReminderAgent
from deadline_calculator import DeadlineCalculator

def parse_date(date_str: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid date format '{date_str}'. Expected format YYYY-MM-DD.")
        sys.exit(1)

def cmd_status(agent: TaxReminderAgent):
    print("\n==========================================")
    print("      BIR TAX REMINDER AGENT STATUS       ")
    print("==========================================")
    state = agent.state_manager.state
    print(f"Last Notified Date : {state.get('last_notified_date')}")
    print(f"Last Thread ID     : {state.get('last_thread_id')}\n")

    today = datetime.date.today()
    print(f"Current System Date: {today.isoformat()}\n")

    for form in ["2551Q", "1701Q"]:
        fdata = state.get(form, {})
        q = fdata.get("current_quarter")
        yr = fdata.get("target_year")
        paid = fdata.get("paid")

        deadline = DeadlineCalculator.get_adjusted_deadline(form, q, yr)
        statutory = DeadlineCalculator.get_statutory_deadline(form, q, yr)
        days_left = (deadline - today).days

        status_str = "PAID [COMPLETED]" if paid else f"UNPAID ({days_left} days remaining)"
        print(f"--- Form {form} ---")
        print(f"  Current Quarter   : {q}")
        print(f"  Tax Year          : {yr}")
        print(f"  Statutory Deadline: {statutory}")
        print(f"  Adjusted Deadline : {deadline} (Rollover logic applied)")
        print(f"  Status            : {status_str}\n")
    print("==========================================\n")

def cmd_run(agent: TaxReminderAgent, date_override: Optional[datetime.date] = None, recipient: Optional[str] = None):
    run_date = date_override or datetime.date.today()
    print(f"Executing daily check for date: {run_date}")
    actions = agent.run_daily_check(current_date=run_date, recipient_email=recipient)
    print("\nExecution Summary:")
    print(json.dumps(actions, indent=2))

def cmd_mark_paid(agent: TaxReminderAgent, form_type: str):
    if form_type not in ["2551Q", "1701Q"]:
        print("Error: Form type must be either '2551Q' or '1701Q'.")
        sys.exit(1)

    print(f"Marking {form_type} as PAID and advancing quarter...")
    agent.state_manager.mark_as_paid(form_type)
    agent.state_manager.advance_quarter(form_type)
    print(f"Updated state for {form_type}:")
    print(json.dumps(agent.state_manager.state[form_type], indent=2))

def cmd_check_replies(agent: TaxReminderAgent):
    print("Checking inbox for payment confirmation replies...")
    results = agent.check_and_process_replies()
    print("Reply Check Results:")
    print(json.dumps(results, indent=2))

def main():
    parser = argparse.ArgumentParser(description="BIR Tax Compliance & Reminder Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Agent command to execute")

    # Status command
    subparsers.add_parser("status", help="Display current agent state and upcoming tax deadlines")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run daily compliance check & send alerts if needed")
    run_parser.add_argument("--date", type=str, help="Simulate execution date (YYYY-MM-DD)", default=None)
    run_parser.add_argument("--recipient", type=str, help="Override recipient email address", default=None)

    # Mark paid command
    paid_parser = subparsers.add_parser("mark-paid", help="Manually mark form as paid & advance quarter")
    paid_parser.add_argument("--form", type=str, required=True, choices=["2551Q", "1701Q"], help="Form type")

    # Check replies command
    subparsers.add_parser("check-replies", help="Check inbox for payment reply confirmations")

    # Simulate command
    sim_parser = subparsers.add_parser("simulate", help="Simulate agent run on a specific target date")
    sim_parser.add_argument("--date", type=str, required=True, help="Target date (YYYY-MM-DD)")
    sim_parser.add_argument("--recipient", type=str, help="Recipient email address", default=None)

    args = parser.parse_args()

    agent = TaxReminderAgent()

    if args.command == "status":
        cmd_status(agent)
    elif args.command == "run":
        run_date = parse_date(args.date) if args.date else None
        cmd_run(agent, date_override=run_date, recipient=args.recipient)
    elif args.command == "mark-paid":
        cmd_mark_paid(agent, args.form)
    elif args.command == "check-replies":
        cmd_check_replies(agent)
    elif args.command == "simulate":
        sim_date = parse_date(args.date)
        cmd_run(agent, date_override=sim_date, recipient=args.recipient)
    else:
        cmd_status(agent)

if __name__ == "__main__":
    main()
