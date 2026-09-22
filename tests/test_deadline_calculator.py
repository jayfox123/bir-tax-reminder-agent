import datetime
import pytest
from deadline_calculator import DeadlineCalculator

def test_statutory_deadlines():
    # 2551Q Q1 2026 -> April 25, 2026
    d2551_q1 = DeadlineCalculator.get_statutory_deadline("2551Q", "Q1", 2026)
    assert d2551_q1 == datetime.date(2026, 4, 25)

    # 2551Q Q4 2026 -> January 25, 2027 (succeeding year)
    d2551_q4 = DeadlineCalculator.get_statutory_deadline("2551Q", "Q4", 2026)
    assert d2551_q4 == datetime.date(2027, 1, 25)

    # 1701Q Q1 2026 -> May 15, 2026
    d1701_q1 = DeadlineCalculator.get_statutory_deadline("1701Q", "Q1", 2026)
    assert d1701_q1 == datetime.date(2026, 5, 15)

    # 1701Q Q3 2026 -> November 15, 2026
    d1701_q3 = DeadlineCalculator.get_statutory_deadline("1701Q", "Q3", 2026)
    assert d1701_q3 == datetime.date(2026, 11, 15)

def test_weekend_rollover():
    # Oct 25, 2026 falls on a Sunday. Should roll over to Monday Oct 26, 2026.
    oct25_2026 = datetime.date(2026, 10, 25)
    assert oct25_2026.weekday() == 6  # Sunday
    adjusted = DeadlineCalculator.adjust_for_weekends_and_holidays(oct25_2026)
    assert adjusted == datetime.date(2026, 10, 26)
    assert adjusted.weekday() == 0  # Monday

def test_alert_window():
    # Test date 10 days before adjusted deadline
    target_year = 2026
    deadline = DeadlineCalculator.get_adjusted_deadline("2551Q", "Q3", target_year)
    # Deadline is Oct 26, 2026
    test_date = deadline - datetime.timedelta(days=10)

    is_in_win, days_left, adj_dl = DeadlineCalculator.is_within_alert_window(
        current_date=test_date,
        form_type="2551Q",
        quarter="Q3",
        target_year=target_year,
        alert_window_days=14
    )
    assert is_in_win is True
    assert days_left == 10
    assert adj_dl == deadline
