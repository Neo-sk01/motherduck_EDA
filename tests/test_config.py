from pipeline.config import AppConfig, QueueConfig, build_default_queues, parse_source_mode


def test_default_queues_match_brief():
    queues = build_default_queues()
    assert [q.queue_id for q in queues] == ["8020", "8021", "8030", "8031"]
    assert queues[0] == QueueConfig("8020", "CSR English", "English", "primary")
    assert queues[1] == QueueConfig("8021", "CSR French", "French", "primary")
    assert queues[2] == QueueConfig("8030", "CSR Overflow English", "English", "overflow")
    assert queues[3] == QueueConfig("8031", "CSR Overflow French", "French", "overflow")


def test_source_mode_is_restricted():
    assert parse_source_mode("csv") == "csv"
    assert parse_source_mode("api") == "api"
    assert parse_source_mode("hybrid") == "hybrid"


def test_source_mode_rejects_unknown_value():
    try:
        parse_source_mode("live")
    except ValueError as exc:
        assert "SOURCE must be one of" in str(exc)
    else:
        raise AssertionError("unknown source mode should raise ValueError")


def test_app_config_from_env(monkeypatch):
    monkeypatch.setenv("MOTHERDUCK_DATABASE", "csh_analytics_v2")
    monkeypatch.setenv("SOURCE", "csv")
    monkeypatch.setenv("CSV_DIR", "./data/csv-uploads")
    monkeypatch.setenv("DATA_DIR", "./data")
    monkeypatch.setenv("TIMEZONE", "America/Toronto")
    cfg = AppConfig.from_env()
    assert cfg.motherduck_database == "csh_analytics_v2"
    assert cfg.source == "csv"
    assert str(cfg.csv_dir).endswith("data/csv-uploads")
    assert str(cfg.data_dir).endswith("data")
    assert cfg.timezone == "America/Toronto"
