import os
import json
import pytest
from state_manager import StateManager

@pytest.fixture
def temp_state_file(tmp_path):
    file_path = tmp_path / "test_agent_state.json"
    initial_data = {
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
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)
    return str(file_path)

def test_load_state(temp_state_file):
    sm = StateManager(temp_state_file)
    assert sm.state["2551Q"]["current_quarter"] == "Q3"
    assert sm.state["1701Q"]["current_quarter"] == "Q3"

def test_mark_as_paid(temp_state_file):
    sm = StateManager(temp_state_file)
    sm.mark_as_paid("2551Q")
    assert sm.state["2551Q"]["paid"] is True

def test_advance_quarter_2551Q(temp_state_file):
    sm = StateManager(temp_state_file)

    # Q3 2026 -> advance to Q4 2026
    sm.advance_quarter("2551Q")
    assert sm.state["2551Q"]["current_quarter"] == "Q4"
    assert sm.state["2551Q"]["target_year"] == 2026
    assert sm.state["2551Q"]["paid"] is False

    # Q4 2026 -> advance to Q1 2027
    sm.advance_quarter("2551Q")
    assert sm.state["2551Q"]["current_quarter"] == "Q1"
    assert sm.state["2551Q"]["target_year"] == 2027

def test_advance_quarter_1701Q(temp_state_file):
    sm = StateManager(temp_state_file)

    # Q3 2026 -> advance to Q1 2027 (since 1701Q has no Q4 return, only Q1, Q2, Q3)
    sm.advance_quarter("1701Q")
    assert sm.state["1701Q"]["current_quarter"] == "Q1"
    assert sm.state["1701Q"]["target_year"] == 2027
    assert sm.state["1701Q"]["paid"] is False
