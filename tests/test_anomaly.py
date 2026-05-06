import json

from pipeline.anomaly import detect_anomalies


def test_detect_anomalies_flags_system_agent_high_caller_and_single_point_agent():
    queue_metrics = {
        "8031": {
            "queue_id": "8031",
            "agent_leaderboard": [{"agent_name": "CSH - BUILDS", "calls": 11, "pct_of_answered": 0.50}],
            "hourly_volume": [{"hour": 12, "calls": 10, "no_answer_rate": 0.60}],
        },
        "8021": {
            "queue_id": "8021",
            "agent_leaderboard": [{"agent_name": "Gabriel Hubert", "calls": 24, "pct_of_answered": 0.75}],
            "hourly_volume": [{"hour": 8, "calls": 4, "no_answer_rate": 0.25}],
        },
    }
    crossqueue = {"callers": [{"caller_number_norm": "9052833500", "total_calls": 63}]}
    anomalies = detect_anomalies(queue_metrics, crossqueue, caller_threshold=20)
    descriptions = [a["description"] for a in anomalies]
    assert any("CSH - BUILDS" in d for d in descriptions)
    assert any("9052833500" in d for d in descriptions)
    assert any("Gabriel Hubert" in d and "60%" in d for d in descriptions)
    assert any("12:00" in d and "50%" in d for d in descriptions)
    assert any(a["target"].get("agent_name") == "CSH - BUILDS" for a in anomalies)
    assert any(a["target"].get("agent_name") == "Gabriel Hubert" for a in anomalies)
    assert any(a["target"].get("hour") == 12 for a in anomalies)
    json.dumps(anomalies)


def test_detect_anomalies_tolerates_sparse_rows_and_avoids_hyphenated_human_false_positive():
    queue_metrics = {
        "8020": {
            "agent_leaderboard": [
                {"calls": 1, "pct_of_answered": 0.90},
                {"agent_name": "Anne-Marie Smith", "calls": 4, "pct_of_answered": 0.20},
                {"agent_name": "Auto Attendant", "calls": 4, "pct_of_answered": "bad"},
            ],
            "hourly_volume": [{"calls": 4, "no_answer_rate": 0.90}],
        }
    }
    crossqueue = {"callers": [{"total_calls": 99}]}
    anomalies = detect_anomalies(queue_metrics, crossqueue)
    descriptions = [a["description"] for a in anomalies]
    assert not any("Anne-Marie Smith" in d for d in descriptions)
    assert any("Auto Attendant" in d for d in descriptions)
