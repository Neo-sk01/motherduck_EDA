import json
from pathlib import Path


def test_april_dashboard_bundle_aligns_with_excel_report():
    metrics_path = Path("dashboard/public/data/reports/month_2026-04-01_2026-04-30/metrics.json")
    metrics = json.loads(metrics_path.read_text())
    assert metrics["source_mode"] == "excel_reference_overlay"
    assert metrics["validation"]["excel_reference_queues"] == ["8020", "8021", "8030", "8031"]

    assert {
        queue_id: {
            "total_calls": row["total_calls"],
            "handled_calls": row["handled_calls"],
            "no_agent_calls": row["no_agent_calls"],
        }
        for queue_id, row in metrics["queues"].items()
    } == {
        "8020": {"total_calls": 1181, "handled_calls": 832, "no_agent_calls": 349},
        "8021": {"total_calls": 66, "handled_calls": 32, "no_agent_calls": 34},
        "8030": {"total_calls": 343, "handled_calls": 162, "no_agent_calls": 181},
        "8031": {"total_calls": 30, "handled_calls": 22, "no_agent_calls": 8},
    }

    for queue_id, queue in metrics["queues"].items():
        assert sum(row["calls"] for row in queue["daily_volume"]) == queue["total_calls"], queue_id
        assert sum(row["calls"] for row in queue["hourly_volume"]) == queue["total_calls"], queue_id

    queue_8020 = metrics["queues"]["8020"]
    assert queue_8020["busiest_day"] == {"date": "2026-04-16", "calls": 100}
    assert max(queue_8020["hourly_volume"], key=lambda row: row["calls"]) == {
        "hour": 10,
        "calls": 181,
        "no_answer_count": 59,
        "no_answer_rate": 59 / 181,
        "avg_agent_sec": queue_8020["hourly_volume"][2]["avg_agent_sec"],
    }

    assert queue_8020["release_reasons"]["queue"][:7] == [
        {"reason": "Orig: Bye", "calls": 426},
        {"reason": "Term: Bye", "calls": 397},
        {"reason": "No Answer", "calls": 342},
        {"reason": "Transferred", "calls": 9},
        {"reason": "Abandoned", "calls": 4},
        {"reason": "Term: 503", "calls": 2},
        {"reason": "No Dial Rule", "calls": 1},
    ]
    assert queue_8020["top_callers"][:5] == [
        {"caller_number_norm": "9052833500", "calls": 45},
        {"caller_number_norm": "6042941500", "calls": 23},
        {"caller_number_norm": "4256352970", "calls": 19},
        {"caller_number_norm": "Restricted", "calls": 18},
        {"caller_number_norm": "6132836772", "calls": 17},
    ]
    assert queue_8020["agent_leaderboard"][:5] == [
        {
            "agent_name": "Alicia Yameen",
            "avg_sec": 229.0,
            "calls": 221,
            "median_sec": 184.0,
            "pct_of_answered": 0.2656,
            "total_sec": 50620.0,
        },
        {
            "agent_name": "Aqsa Razzaq",
            "avg_sec": 382.0,
            "calls": 174,
            "median_sec": 240.0,
            "pct_of_answered": 0.2091,
            "total_sec": 66473.0,
        },
        {
            "agent_name": "Gabriel Hubert",
            "avg_sec": 261.0,
            "calls": 73,
            "median_sec": 248.0,
            "pct_of_answered": 0.0877,
            "total_sec": 19072.0,
        },
        {
            "agent_name": "Luke Deschenes",
            "avg_sec": 607.0,
            "calls": 36,
            "median_sec": 322.0,
            "pct_of_answered": 0.0433,
            "total_sec": 21851.0,
        },
        {
            "agent_name": "Rao Arslan",
            "avg_sec": 362.0,
            "calls": 31,
            "median_sec": 292.0,
            "pct_of_answered": 0.0373,
            "total_sec": 11209.0,
        },
    ]

    queue_8021 = metrics["queues"]["8021"]
    assert queue_8021["release_reasons"]["queue"][:5] == [
        {"reason": "No Answer", "calls": 30},
        {"reason": "Term: Bye", "calls": 17},
        {"reason": "Orig: Bye", "calls": 14},
        {"reason": "Abandoned", "calls": 4},
        {"reason": "Transferred", "calls": 1},
    ]
    assert [(row["agent_name"], row["calls"]) for row in queue_8021["agent_leaderboard"][:5]] == [
        ("Gabriel Hubert", 12),
        ("Diego Villegas", 5),
        ("Aymen Zayet", 3),
        ("Luke Deschenes", 3),
        ("Florian Nsabiyumva", 2),
    ]
    assert queue_8021["top_callers"][:5] == [
        {"caller_number_norm": "8197908197", "calls": 4},
        {"caller_number_norm": "6134470814", "calls": 3},
        {"caller_number_norm": "Restricted", "calls": 3},
        {"caller_number_norm": "3432023236", "calls": 2},
        {"caller_number_norm": "6135664744", "calls": 2},
    ]

    assert metrics["queues"]["8030"]["release_reasons"]["queue"][:4] == [
        {"reason": "ForwardNoAns", "calls": 178},
        {"reason": "Term: Bye", "calls": 61},
        {"reason": "Transferred", "calls": 58},
        {"reason": "Orig: Bye", "calls": 42},
    ]
    assert metrics["queues"]["8031"]["top_callers"][:3] == [
        {"caller_number_norm": "6134470814", "calls": 3},
        {"caller_number_norm": "Restricted", "calls": 3},
        {"caller_number_norm": "3432023236", "calls": 2},
    ]
