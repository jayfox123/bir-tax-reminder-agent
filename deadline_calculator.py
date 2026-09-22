import datetime
from typing import Tuple, Optional, Set

try:
    import holidays
    HAS_HOLIDAYS_PKG = True
except ImportError:
    HAS_HOLIDAYS_PKG = False

# BIR statutory deadline definitions (month, day)
STATUTORY_DEADLINES = {
    "2551Q": {
        "Q1": (4, 25),
        "Q2": (7, 25),
        "Q3": (10, 25),
        "Q4": (1, 25),  # Note: due in succeeding year!
    },
    "1701Q": {
        "Q1": (5, 15),
        "Q2": (8, 15),
        "Q3": (11, 15),
    }
}

class DeadlineCalculator:
    """Calculates official BIR tax filing deadlines and applies weekend/PH holiday rollover rules."""

    def __init__(self):
        pass

    @staticmethod
    def get_ph_holidays(year: int) -> Set[datetime.date]:
        """Returns set of Philippine national holidays for a given year."""
        ph_holidays = set()
        if HAS_HOLIDAYS_PKG:
            ph_hols = holidays.PH(years=year)
            for date_obj in ph_hols.keys():
                ph_holidays.add(date_obj)
        else:
            # Basic fallback for major fixed PH holidays if package is unavailable
            fixed_dates = [
                (1, 1),   # New Year's Day
                (4, 9),   # Araw ng Kagitingan
                (5, 1),   # Labor Day
                (6, 12),  # Independence Day
                (8, 21),  # Ninoy Aquino Day
                (11, 1),  # All Saints Day
                (11, 30), # Bonifacio Day
                (12, 8),  # Feast of Immaculate Conception
                (12, 25), # Christmas Day
                (12, 30), # Rizal Day
                (12, 31)  # Last Day of Year
            ]
            for m, d in fixed_dates:
                try:
                    ph_holidays.add(datetime.date(year, m, d))
                except ValueError:
                    pass
        return ph_holidays

    @classmethod
    def get_statutory_deadline(cls, form_type: str, quarter: str, target_year: int) -> datetime.date:
        """Returns statutory date before weekend/holiday rollover logic."""
        if form_type not in STATUTORY_DEADLINES:
            raise ValueError(f"Unknown form type: {form_type}")
        if quarter not in STATUTORY_DEADLINES[form_type]:
            raise ValueError(f"Unknown quarter '{quarter}' for form '{form_type}'")

        month, day = STATUTORY_DEADLINES[form_type][quarter]

        # For 2551Q Q4, the target_year refers to the tax year, but deadline is Jan 25 of the succeeding year
        actual_year = target_year + 1 if (form_type == "2551Q" and quarter == "Q4") else target_year
        return datetime.date(actual_year, month, day)

    @classmethod
    def adjust_for_weekends_and_holidays(cls, date_obj: datetime.date) -> datetime.date:
        """Rolls statutory deadline forward to next regular business day if falling on weekend/holiday."""
        curr_date = date_obj
        # Fetch holidays for relevant years
        ph_holidays = cls.get_ph_holidays(curr_date.year)
        ph_holidays.update(cls.get_ph_holidays(curr_date.year + 1))

        while True:
            # Check weekend (5 = Saturday, 6 = Sunday)
            is_weekend = curr_date.weekday() in (5, 6)
            is_holiday = curr_date in ph_holidays

            if is_weekend or is_holiday:
                curr_date += datetime.timedelta(days=1)
            else:
                break

        return curr_date

    @classmethod
    def get_adjusted_deadline(cls, form_type: str, quarter: str, target_year: int) -> datetime.date:
        """Gets final adjusted business day deadline for form, quarter, and tax year."""
        statutory = cls.get_statutory_deadline(form_type, quarter, target_year)
        return cls.adjust_for_weekends_and_holidays(statutory)

    @classmethod
    def is_within_alert_window(
        cls,
        current_date: datetime.date,
        form_type: str,
        quarter: str,
        target_year: int,
        alert_window_days: int = 14
    ) -> Tuple[bool, int, datetime.date]:
        """Checks if current_date is within the alert window prior to adjusted deadline.

        Returns: (is_within_window, days_remaining, adjusted_deadline)
        """
        deadline = cls.get_adjusted_deadline(form_type, quarter, target_year)
        days_remaining = (deadline - current_date).days

        # Alert window: when current_date is between (deadline - alert_window_days) and deadline (inclusive or slightly past)
        # We trigger daily alerts if 0 <= days_remaining <= alert_window_days
        is_in_window = 0 <= days_remaining <= alert_window_days
        return is_in_window, days_remaining, deadline
