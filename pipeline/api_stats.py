from __future__ import annotations

from typing import Any

from pipeline.config import QueueConfig


def apply_api_queue_stats(
    queue_metrics: dict[str, dict[str, Any]],
    crossqueue: dict[str, Any],
    stats_by_queue: dict[str, dict[str, Any]],
    queues: tuple[QueueConfig, ...],
) -> None:
    for queue in queues:
        stats = stats_by_queue.get(str(queue.queue_id))
        metrics = queue_metrics.get(str(queue.queue_id))
        if stats is None or metrics is None:
            continue
        offered = _int(stats.get("calls_offered"))
        forwarded = _int(stats.get("calls_forwarded"))
        abandoned = _int(stats.get("abandoned_calls"))
        no_agent = min(offered, forwarded + abandoned)
        metrics["api_stats"] = {
            "calls_offered": offered,
            "calls_forwarded": forwarded,
            "abandoned_calls": abandoned,
            "calls_handled": _int(stats.get("calls_handled")),
            "call_volume": _int(stats.get("call_volume")),
            "derived_no_agent_calls": no_agent,
            "derived_handled_calls": max(0, offered - no_agent),
            "note": "Diagnostic only; cleaned queue metrics are not overwritten.",
        }

    crossqueue["api_stats_funnels"] = {
        "English": _language_funnel_from_stats(stats_by_queue, "8020", "8030"),
        "French": _language_funnel_from_stats(stats_by_queue, "8021", "8031"),
    }


def _language_funnel_from_stats(
    stats_by_queue: dict[str, dict[str, Any]],
    primary_queue_id: str,
    overflow_queue_id: str,
) -> dict[str, int | float]:
    primary = stats_by_queue.get(primary_queue_id, {})
    overflow = stats_by_queue.get(overflow_queue_id, {})
    primary_calls = _int(primary.get("calls_offered"))
    primary_failed = min(
        primary_calls,
        _int(primary.get("calls_forwarded")) + _int(primary.get("abandoned_calls")),
    )
    primary_answered = max(0, primary_calls - primary_failed)
    overflow_received = _int(overflow.get("calls_offered"))
    overflow_failed = min(
        overflow_received,
        _int(overflow.get("calls_forwarded")) + _int(overflow.get("abandoned_calls")),
    )
    overflow_answered = max(0, overflow_received - overflow_failed)
    unaccounted = primary_failed - overflow_received
    lost = max(0, primary_failed - overflow_answered)
    return {
        "primary_calls": primary_calls,
        "primary_answered": primary_answered,
        "primary_failed": primary_failed,
        "primary_no_agent_calls": primary_failed,
        "primary_no_agent_rate": float(primary_failed / primary_calls) if primary_calls else 0.0,
        "overflow_received": overflow_received,
        "routing_match": float(overflow_received / primary_failed) if primary_failed else 0.0,
        "overflow_answered": overflow_answered,
        "overflow_failed": overflow_failed,
        "lost": lost,
        "lost_rate": float(lost / primary_calls) if primary_calls else 0.0,
        "effective_answer_rate": float(1 - (lost / primary_calls)) if primary_calls else 0.0,
        "unaccounted": unaccounted,
        "final_dropped_available": True,
        "final_dropped_calls": lost,
        "drop_definition": "final_dropped_after_overflow",
    }


def _int(value: Any) -> int:
    if value is None:
        return 0
    return int(float(value))
