from pipeline.metrics_queue import compute_queue_metrics


def test_compute_queue_metrics_headlines(curated_sample):
    metrics = compute_queue_metrics(curated_sample, "8020")
    assert metrics["queue_id"] == "8020"
    assert metrics["total_calls"] == 3
    assert metrics["handled_calls"] == 2
    assert metrics["no_agent_calls"] == 1
    assert metrics["no_agent_rate"] == 1 / 3
    assert metrics["days_with_calls"] == 2
    assert metrics["busiest_day"] == {"date": "2026-04-01", "calls": 2}
    assert metrics["quietest_day"] == {"date": "2026-04-02", "calls": 1}


def test_compute_queue_metrics_series_and_leaderboards(curated_sample):
    metrics = compute_queue_metrics(curated_sample, "8020")
    assert metrics["daily_volume"][0] == {"date": "2026-04-01", "calls": 2}
    assert metrics["hourly_volume"][1]["hour"] == 9
    assert metrics["hourly_volume"][1]["calls"] == 2
    assert metrics["hourly_volume"][1]["no_answer_rate"] == 0.5
    assert metrics["agent_leaderboard"][0]["agent_name"] == "Alicia"
    assert metrics["agent_leaderboard"][0]["calls"] == 2
    assert metrics["top_callers"][0]["caller_number_norm"] == "9052833500"
    assert metrics["top_callers"][0]["calls"] == 2
