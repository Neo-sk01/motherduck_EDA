from pipeline.metrics_queue import compute_queue_metrics


def test_compute_queue_metrics_headlines(curated_sample):
    metrics = compute_queue_metrics(curated_sample, "8020")
    assert metrics["queue_id"] == "8020"
    assert metrics["total_calls"] == 5
    assert metrics["handled_calls"] == 3
    assert metrics["no_agent_calls"] == 2
    assert metrics["no_agent_rate"] == 0.4
    assert metrics["days_with_calls"] == 2
    assert metrics["busiest_day"] == {"date": "2026-04-02", "calls": 3}
    assert metrics["quietest_day"] == {"date": "2026-04-01", "calls": 2}


def test_compute_queue_metrics_series_and_leaderboards(curated_sample):
    metrics = compute_queue_metrics(curated_sample, "8020")
    assert metrics["daily_volume"][0] == {"date": "2026-04-01", "calls": 2}
    assert metrics["hourly_volume"][1]["hour"] == 9
    assert metrics["hourly_volume"][1]["calls"] == 2
    assert metrics["hourly_volume"][1]["no_answer_rate"] == 0.5
    assert metrics["hourly_volume"][2]["hour"] == 10
    assert metrics["hourly_volume"][2]["calls"] == 2
    assert metrics["hourly_volume"][2]["no_answer_rate"] == 0.5
    assert metrics["dow_volume"] == [
        {"dow": "Thursday", "calls": 3},
        {"dow": "Wednesday", "calls": 2},
    ]
    assert metrics["duration_distributions"]["queue_sec"]["count"] == 5
    assert metrics["duration_distributions"]["queue_sec"]["median"] == 9.0
    assert metrics["duration_distributions"]["agent_sec"]["count"] == 3
    assert metrics["duration_distributions"]["agent_sec"]["median"] == 244.0
    assert metrics["duration_distributions"]["hold_sec"]["count"] == 1
    assert metrics["duration_distributions"]["hold_sec"]["median"] == 20.0
    assert metrics["release_reasons"]["queue"] == [
        {"reason": "No Answer", "calls": 3},
        {"reason": "Orig: Bye", "calls": 1},
        {"reason": "Term: Bye", "calls": 1},
    ]
    assert metrics["release_reasons"]["agent"] == [
        {"reason": "No Answer", "calls": 3},
        {"reason": "Orig: Bye", "calls": 1},
        {"reason": "Term: Bye", "calls": 1},
    ]
    assert metrics["agent_leaderboard"][0]["agent_name"] == "Alicia"
    assert metrics["agent_leaderboard"][0]["calls"] == 2
    assert metrics["agent_leaderboard"][0]["avg_sec"] == 272.0
    assert metrics["agent_leaderboard"][0]["median_sec"] == 272.0
    assert metrics["agent_leaderboard"][0]["total_sec"] == 544.0
    assert metrics["agent_leaderboard"][0]["pct_of_answered"] == 2 / 3
    assert metrics["agent_leaderboard"][1]["agent_name"] == "Named Zero"
    assert metrics["agent_leaderboard"][1]["calls"] == 1
    assert metrics["top_callers"][0]["caller_number_norm"] == "9052833500"
    assert metrics["top_callers"][0]["calls"] == 2
    assert all(not row["caller_number_norm"].startswith("__restricted__:") for row in metrics["top_callers"])


def test_compute_queue_metrics_returns_empty_payload_for_unknown_queue(curated_sample):
    metrics = compute_queue_metrics(curated_sample, "9999")
    assert metrics["queue_id"] == "9999"
    assert metrics["total_calls"] == 0
    assert metrics["handled_calls"] == 0
    assert metrics["no_agent_calls"] == 0
    assert metrics["no_agent_rate"] == 0.0
    assert metrics["days_with_calls"] == 0
    assert metrics["avg_calls_per_active_day"] == 0.0
    assert metrics["busiest_day"] is None
    assert metrics["quietest_day"] is None
    assert metrics["daily_volume"] == []
    assert metrics["hourly_volume"] == []
    assert metrics["dow_volume"] == []
    assert metrics["duration_distributions"]["queue_sec"]["count"] == 0
    assert metrics["release_reasons"] == {"queue": [], "agent": []}
    assert metrics["agent_leaderboard"] == []
    assert metrics["top_callers"] == []
