from __future__ import annotations


def detect_anomalies(queue_metrics: dict[str, dict], crossqueue: dict, caller_threshold: int = 20) -> list[dict]:
    anomalies: list[dict] = []
    for queue_id, metrics in queue_metrics.items():
        for agent in metrics.get("agent_leaderboard", []):
            name = agent.get("agent_name")
            if not name:
                continue
            name = str(name)
            share = _safe_float(agent.get("pct_of_answered", 0.0))
            if _looks_non_human_agent(name):
                anomalies.append({
                    "severity": "high",
                    "kind": "system_agent",
                    "queue_id": queue_id,
                    "description": f"{name} appears in queue {queue_id} agent leaderboard and should be verified as human or system.",
                    "target": {"view": "per-queue", "queue_id": queue_id, "agent_name": name},
                })
            if share > 0.60:
                anomalies.append({
                    "severity": "high",
                    "kind": "single_agent_dependency",
                    "queue_id": queue_id,
                    "description": f"{name} handled more than 60% of answered calls on queue {queue_id}.",
                    "target": {"view": "per-queue", "queue_id": queue_id, "agent_name": name},
                })
        for hour in metrics.get("hourly_volume", []):
            if "hour" not in hour:
                continue
            hour_value = int(hour["hour"])
            if _safe_float(hour.get("no_answer_rate", 0.0)) > 0.50:
                anomalies.append({
                    "severity": "medium",
                    "kind": "hourly_no_answer",
                    "queue_id": queue_id,
                    "description": f"Queue {queue_id} has no-answer rate above 50% at {hour_value:02d}:00.",
                    "target": {"view": "per-queue", "queue_id": queue_id, "hour": hour_value},
                })
    for caller in crossqueue.get("callers", []):
        number = caller.get("caller_number_norm")
        if not number:
            continue
        if int(caller.get("total_calls", 0)) > caller_threshold:
            number = str(number)
            anomalies.append({
                "severity": "medium",
                "kind": "caller_concentration",
                "description": f"Caller {number} exceeded {caller_threshold} cross-queue contacts.",
                "target": {"view": "cross-queue", "entity": number},
            })
    return anomalies


def _looks_non_human_agent(name: str) -> bool:
    normalized = name.casefold()
    system_terms = (
        "auto attendant",
        "builds",
        "csh - builds",
        "ivr",
        "queue",
        "system",
        "voicemail",
    )
    return any(term in normalized for term in system_terms)


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
