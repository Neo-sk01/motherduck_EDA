from pipeline.config import AppConfig, QueueConfig, build_default_queues, parse_source_mode


def test_default_queues_match_brief(monkeypatch):
    for key in ("QUEUE_ENGLISH", "QUEUE_FRENCH", "QUEUE_AI_OVERFLOW_EN", "QUEUE_AI_OVERFLOW_FR"):
        monkeypatch.delenv(key, raising=False)

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


def test_app_config_from_env_reads_queue_overrides(monkeypatch):
    monkeypatch.setenv("QUEUE_ENGLISH", "9001")
    monkeypatch.setenv("QUEUE_FRENCH", "9002")
    monkeypatch.setenv("QUEUE_AI_OVERFLOW_EN", "9010")
    monkeypatch.setenv("QUEUE_AI_OVERFLOW_FR", "9011")

    cfg = AppConfig.from_env()

    assert [queue.queue_id for queue in cfg.queues] == ["9001", "9002", "9010", "9011"]
    assert [queue.name for queue in cfg.queues] == [
        "CSR English",
        "CSR French",
        "CSR Overflow English",
        "CSR Overflow French",
    ]


def test_app_config_from_env_loads_dotenv(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATA_DIR", raising=False)
    (tmp_path / ".env").write_text("DATA_DIR=./from-dotenv\n")

    cfg = AppConfig.from_env()

    assert str(cfg.data_dir).endswith("from-dotenv")
