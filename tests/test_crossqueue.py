import pandas as pd
import pytest

from pipeline.crossqueue import compute_crossqueue_metrics


def test_compute_crossqueue_metrics_funnel_and_consolidation():
    df = pd.DataFrame(
        [
            {
                "queue_id": "8020",
                "language": "English",
                "role": "primary",
                "call_id": "en1",
                "agent_name": "Gabriel Hubert",
                "caller_number_norm": "9052833500",
                "date": "2026-04-01",
                "hour": 8,
                "handled_flag": "Handled",
            },
            {
                "queue_id": "8020",
                "language": "English",
                "role": "primary",
                "call_id": "en2",
                "agent_name": None,
                "caller_number_norm": "9052833500",
                "date": "2026-04-01",
                "hour": 9,
                "handled_flag": "No Agent",
            },
            {
                "queue_id": "8020",
                "language": "English",
                "role": "primary",
                "call_id": "en3",
                "agent_name": None,
                "caller_number_norm": "2223334444",
                "date": "2026-04-01",
                "hour": 10,
                "handled_flag": "No Agent",
            },
            {
                "queue_id": "8030",
                "language": "English",
                "role": "overflow",
                "call_id": "en2o",
                "agent_name": None,
                "caller_number_norm": "9052833500",
                "date": "2026-04-01",
                "hour": 9,
                "handled_flag": "No Agent",
            },
            {
                "queue_id": "8021",
                "language": "French",
                "role": "primary",
                "call_id": "fr1",
                "agent_name": None,
                "caller_number_norm": "8197908197",
                "date": "2026-04-01",
                "hour": 8,
                "handled_flag": "No Agent",
            },
            {
                "queue_id": "8031",
                "language": "French",
                "role": "overflow",
                "call_id": "fr1o",
                "agent_name": "Gabriel Hubert",
                "caller_number_norm": "8197908197",
                "date": "2026-04-01",
                "hour": 8,
                "handled_flag": "Handled",
            },
        ]
    )
    metrics = compute_crossqueue_metrics(df)
    english = metrics["funnels"]["English"]
    assert english["primary_calls"] == 3
    assert english["primary_answered"] == 1
    assert english["primary_failed"] == 2
    assert english["overflow_received"] == 1
    assert english["overflow_failed"] == 1
    assert english["unaccounted"] == 1
    assert english["lost"] == 1
    assert english["lost_rate"] == 1 / 3
    assert english["effective_answer_rate"] == pytest.approx(2 / 3)
    assert english["drop_definition"] == "final_dropped_after_overflow"
    assert english["final_dropped_calls"] == 1
    assert metrics["agents"][0]["agent_name"] == "Gabriel Hubert"
    assert metrics["agents"][0]["total_calls"] == 2
    assert metrics["callers"][0]["caller_number_norm"] == "9052833500"
    assert metrics["callers"][0]["total_calls"] == 3


def test_compute_crossqueue_metrics_labels_primary_only_no_agent_when_overflow_missing():
    df = pd.DataFrame(
        [
            {
                "queue_id": "8020",
                "language": "English",
                "role": "primary",
                "call_id": "answered",
                "agent_name": "Alicia",
                "caller_number_norm": "9052833500",
                "date": "2026-01-02",
                "hour": 8,
                "agent_sec": 120.0,
            },
            {
                "queue_id": "8020",
                "language": "English",
                "role": "primary",
                "call_id": "handoff",
                "agent_name": None,
                "caller_number_norm": "6135551212",
                "date": "2026-01-02",
                "hour": 9,
                "agent_sec": 0.0,
            },
        ]
    )

    english = compute_crossqueue_metrics(df)["funnels"]["English"]

    assert english["primary_calls"] == 2
    assert english["primary_no_agent_calls"] == 1
    assert english["final_dropped_available"] is False
    assert english["final_dropped_calls"] is None
    assert english["drop_definition"] == "primary_no_agent_handoff_candidates_overflow_missing"
    assert english["lost"] == 1
