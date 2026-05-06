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
