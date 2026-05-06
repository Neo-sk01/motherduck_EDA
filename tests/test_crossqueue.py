import pandas as pd

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
                "handled_flag": "No Talk Time",
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
                "handled_flag": "No Talk Time",
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
                "handled_flag": "No Talk Time",
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
    assert english["primary_calls"] == 2
    assert english["primary_answered"] == 1
    assert english["primary_failed"] == 1
    assert english["overflow_received"] == 1
    assert english["overflow_failed"] == 1
    assert english["effective_answer_rate"] == 0.5
    assert metrics["agents"][0]["agent_name"] == "Gabriel Hubert"
    assert metrics["agents"][0]["total_calls"] == 2
    assert metrics["callers"][0]["caller_number_norm"] == "9052833500"
    assert metrics["callers"][0]["total_calls"] == 3
