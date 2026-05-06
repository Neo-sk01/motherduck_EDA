# NeoLore Queue Analytics

Batch analytics pipeline and dashboard data foundation for four NeoLore CSR queues.

## Local Setup

Use Python 3.11 or newer. On this machine, `python3` is older than the project requirement, so `uv` is the easiest local setup path:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
```

Put secrets only in `.env`. Do not commit secrets.

## CSV Run

Available after the pipeline modules are implemented.

Place the four SONAR Queue Detail CSV files in `data/csv-uploads/`, then run:

```bash
python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30
```

## Tests

```bash
pytest
```
