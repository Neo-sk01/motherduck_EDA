import pandas as pd
import pytest


@pytest.fixture
def curated_sample() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"queue_id": "8020", "date": "2026-04-01", "hour": 8, "dow": "Wednesday", "call_id": "a", "agent_name": "Alicia", "agent_sec": 244.0, "queue_sec": 9.0, "hold_sec": 0.0, "caller_number_norm": "9052833500", "queue_release_reason": "Orig: Bye", "agent_release_reason": "Orig: Bye", "handled_flag": "Handled"},
            {"queue_id": "8020", "date": "2026-04-01", "hour": 9, "dow": "Wednesday", "call_id": "b", "agent_name": None, "agent_sec": 0.0, "queue_sec": 10.0, "hold_sec": 0.0, "caller_number_norm": "1112223333", "queue_release_reason": "No Answer", "agent_release_reason": "No Answer", "handled_flag": "No Talk Time"},
            {"queue_id": "8020", "date": "2026-04-02", "hour": 9, "dow": "Thursday", "call_id": "c", "agent_name": "Alicia", "agent_sec": 300.0, "queue_sec": 7.0, "hold_sec": 20.0, "caller_number_norm": "9052833500", "queue_release_reason": "Term: Bye", "agent_release_reason": "Term: Bye", "handled_flag": "Handled"},
            {"queue_id": "8020", "date": "2026-04-02", "hour": 10, "dow": "Thursday", "call_id": "d", "agent_name": None, "agent_sec": 0.0, "queue_sec": 8.0, "hold_sec": 0.0, "caller_number_norm": "__restricted__:d", "queue_release_reason": "No Answer", "agent_release_reason": "No Answer", "handled_flag": "No Talk Time"},
        ]
    )
