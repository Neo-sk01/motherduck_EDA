# NeoLore Queue Analytics

Batch analytics pipeline and dashboard data foundation for four NeoLore CSR queues.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
cp .env.example .env
```

Put secrets only in `.env`. Do not commit secrets.

## CSV Run

Place the four SONAR Queue Detail CSV files in `data/csv-uploads/`, then run:

```bash
python3 -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30
```

## Tests

```bash
pytest
```
