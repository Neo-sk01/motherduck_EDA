from pipeline.api_stats import apply_api_queue_stats
from pipeline.config import build_default_queues


def test_apply_api_queue_stats_keeps_cleaned_metrics_and_records_api_diagnostics():
    queues = tuple(build_default_queues())
    queue_metrics = {
        "8020": {"queue_id": "8020", "total_calls": 720, "handled_calls": 720, "no_agent_calls": 0, "no_agent_rate": 0.0},
        "8021": {"queue_id": "8021", "total_calls": 41, "handled_calls": 41, "no_agent_calls": 0, "no_agent_rate": 0.0},
        "8030": {"queue_id": "8030", "total_calls": 153, "handled_calls": 153, "no_agent_calls": 0, "no_agent_rate": 0.0},
        "8031": {"queue_id": "8031", "total_calls": 8, "handled_calls": 8, "no_agent_calls": 0, "no_agent_rate": 0.0},
    }
    crossqueue = {"funnels": {}, "agents": [], "callers": [], "same_hour_no_answer": [], "same_day_volume": []}
    stats = {
        "8020": {"calls_offered": 767, "calls_forwarded": 157, "abandoned_calls": 14},
        "8021": {"calls_offered": 45, "calls_forwarded": 8, "abandoned_calls": 1},
        "8030": {"calls_offered": 156, "calls_forwarded": 121, "abandoned_calls": 3},
        "8031": {"calls_offered": 8, "calls_forwarded": 5, "abandoned_calls": 2},
    }

    apply_api_queue_stats(queue_metrics, crossqueue, stats, queues)

    assert queue_metrics["8020"]["total_calls"] == 720
    assert queue_metrics["8020"]["no_agent_calls"] == 0
    assert queue_metrics["8020"]["handled_calls"] == 720
    assert queue_metrics["8020"]["api_stats"] == {
        "calls_offered": 767,
        "calls_forwarded": 157,
        "abandoned_calls": 14,
        "calls_handled": 0,
        "call_volume": 0,
        "derived_no_agent_calls": 171,
        "derived_handled_calls": 596,
        "note": "Diagnostic only; cleaned queue metrics are not overwritten.",
    }
    assert queue_metrics["8030"]["handled_calls"] == 153
    assert crossqueue["funnels"] == {}
    assert crossqueue["api_stats_funnels"]["English"] == {
        "primary_calls": 767,
        "primary_answered": 596,
        "primary_failed": 171,
        "primary_no_agent_calls": 171,
        "primary_no_agent_rate": 171 / 767,
        "overflow_received": 156,
        "routing_match": 156 / 171,
        "overflow_answered": 32,
        "overflow_failed": 124,
        "lost": 139,
        "lost_rate": 139 / 767,
        "effective_answer_rate": 1 - (139 / 767),
        "unaccounted": 15,
        "final_dropped_available": True,
        "final_dropped_calls": 139,
        "drop_definition": "final_dropped_after_overflow",
    }
