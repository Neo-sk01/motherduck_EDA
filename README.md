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

Place the four SONAR Queue Detail CSV files in `data/csv-uploads/`, then run:

```bash
python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30
```

The default command writes report JSON only. To also replace the matching period in MotherDuck/DuckDB tables, set `MOTHERDUCK_TOKEN_RW` and opt in explicitly:

```bash
python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30 --write-store
```

Backfills support arbitrary `--start` and `--end` dates. If a CSV export contains a broader range, rows outside the requested period are filtered before deduplication and metric computation.

## Tests

```bash
pytest
```

## Dashboard

```bash
cd dashboard
npm install
npm run dev
```

The dashboard defaults to:

```text
/data/reports/month_2026-04-01_2026-04-30/metrics.json
```

For local static serving, copy a generated report bundle into:

```text
dashboard/public/data/reports/
```

To refresh the April report:

```bash
python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30
```
