from __future__ import annotations


def detect_anomalies(queue_metrics: dict[str, dict], crossqueue: dict, caller_threshold: int = 20) -> list[dict]:
    anomalies: list[dict] = []
    for queue_id, metrics in queue_metrics.items():
        for agent in metrics.get("agent_leaderboard", []):
            name = str(agent["agent_name"])
            share = float(agent.get("pct_of_answered", 0.0))
            if _looks_non_human_agent(name):
                anomalies.append({
                    "severity": "high",
                    "kind": "system_agent",
                    "queue_id": queue_id,
                    "description": f"{name} appears in queue {queue_id} agent leaderboard and should be verified as human or system.",
                    "target": {"view": "per-queue", "queue_id": queue_id},
                })
            if share > 0.60:
                anomalies.append({
                    "severity": "high",
                    "kind": "single_agent_dependency",
                    "queue_id": queue_id,
                    "description": f"{name} handled more than 60% of answered calls on queue {queue_id}.",
                    "target": {"view": "per-queue", "queue_id": queue_id},
                })
        for hour in metrics.get("hourly_volume", []):
            if float(hour.get("no_answer_rate", 0.0)) > 0.50:
                anomalies.append({
                    "severity": "medium",
                    "kind": "hourly_no_answer",
                    "queue_id": queue_id,
                    "description": f"Queue {queue_id} has no-answer rate above 50% at {int(hour['hour']):02d}:00.",
                    "target": {"view": "per-queue", "queue_id": queue_id},
                })
    for caller in crossqueue.get("callers", []):
        if int(caller.get("total_calls", 0)) > caller_threshold:
            number = str(caller["caller_number_norm"])
            anomalies.append({
                "severity": "medium",
                "kind": "caller_concentration",
                "description": f"Caller {number} exceeded {caller_threshold} cross-queue contacts.",
                "target": {"view": "cross-queue", "entity": number},
            })
    return anomalies


def _looks_non_human_agent(name: str) -> bool:
    words = [part for part in name.replace("-", " ").split() if part]
    return "-" in name or any(len(word) >= 3 and word.isupper() for word in words)
