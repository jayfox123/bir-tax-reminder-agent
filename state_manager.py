import json
import os
from typing import Dict, Any, Optional
import config

class StateManager:
    """Manages persistent reading, saving, updating, and advancing of agent_state.json."""

    def __init__(self, state_file_path: Optional[str] = None):
        self.state_file_path = state_file_path or config.STATE_FILE_PATH
        self.state: Dict[str, Any] = self.load_state()

    def get_default_state(self) -> Dict[str, Any]:
        return {
            "2551Q": {
                "current_quarter": "Q3",
                "target_year": 2026,
                "paid": False
            },
            "1701Q": {
                "current_quarter": "Q3",
                "target_year": 2026,
                "paid": False
            },
            "last_thread_id": None,
            "last_notified_date": None
        }

    def load_state(self) -> Dict[str, Any]:
        if not os.path.exists(self.state_file_path):
            default_st = self.get_default_state()
            self.save_state(default_st)
            return default_st
        try:
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            default_st = self.get_default_state()
            self.save_state(default_st)
            return default_st

    def save_state(self, state_dict: Optional[Dict[str, Any]] = None) -> None:
        if state_dict is not None:
            self.state = state_dict
        os.makedirs(os.path.dirname(os.path.abspath(self.state_file_path)), exist_ok=True)
        with open(self.state_file_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def mark_as_paid(self, form_type: str) -> None:
        if form_type in self.state and isinstance(self.state[form_type], dict):
            self.state[form_type]["paid"] = True
            self.save_state()

    def advance_quarter(self, form_type: str) -> None:
        """Advances the quarter for a form after payment confirmation.

        For 2551Q: Q1 -> Q2 -> Q3 -> Q4 -> Q1 (year + 1)
        For 1701Q: Q1 -> Q2 -> Q3 -> Q1 (year + 1)
        """
        if form_type not in self.state or not isinstance(self.state[form_type], dict):
            return

        form_data = self.state[form_type]
        curr_q = form_data.get("current_quarter", "Q1")
        year = form_data.get("target_year", 2026)

        if form_type == "2551Q":
            q_order = ["Q1", "Q2", "Q3", "Q4"]
            idx = q_order.index(curr_q) if curr_q in q_order else 0
            if idx == len(q_order) - 1:
                next_q = "Q1"
                next_year = year + 1
            else:
                next_q = q_order[idx + 1]
                next_year = year
        elif form_type == "1701Q":
            q_order = ["Q1", "Q2", "Q3"]
            idx = q_order.index(curr_q) if curr_q in q_order else 0
            if idx == len(q_order) - 1:
                next_q = "Q1"
                next_year = year + 1
            else:
                next_q = q_order[idx + 1]
                next_year = year
        else:
            return

        self.state[form_type]["current_quarter"] = next_q
        self.state[form_type]["target_year"] = next_year
        self.state[form_type]["paid"] = False
        self.save_state()

    def update_last_thread_id(self, thread_id: Optional[str]) -> None:
        self.state["last_thread_id"] = thread_id
        self.save_state()

    def update_last_notified_date(self, date_str: Optional[str]) -> None:
        self.state["last_notified_date"] = date_str
        self.save_state()
