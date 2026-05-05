# Unified Call Queue Analytics Dashboard Design

Date: 2026-05-05

## Source Of Truth

This design follows `AI_AGENT_PROMPT_unified_dashboard.md`, Revision 3, May 5, 2026. The application must match that document's four-queue topology, deduplication rules, parsing rules, metrics, dashboard views, validation references, acceptance criteria, and out-of-scope boundaries.

The supplied `queue_details_april_2026_eda_report (1).xlsx` is a useful queue 8020 reference workbook, but it is not the full v1 source of truth. Full v1 covers all four NeoLore queues:

| Queue ID | Name | Role | Language |
|---|---|---|---|
| 8020 | CSR English | Primary | English |
| 8021 | CSR French | Primary | French |
| 8030 | CSR Overflow English | Overflow | English |
| 8031 | CSR Overflow French | Overflow | French |

## Goals

Build a recurring batch analytics pipeline plus a unified web dashboard that answers:

1. What happened on each queue for the selected period?
2. What happened end-to-end from primary queue to overflow queue?
3. Where are operational risks across agents, callers, hours, and routing?

The system is not real-time. It runs scheduled daily, weekly, and monthly batches. The dashboard reads cached outputs and MotherDuck-backed analytical tables.

## Architecture

Use the selected option 1 architecture:

- `pipeline/`: Python analytics pipeline for CSV, API, and hybrid ingestion.
- MotherDuck: durable analytical warehouse for raw, curated, and metrics tables.
- `api/`: thin backend API that reads MotherDuck/report outputs and serves dashboard JSON and exports.
- `dashboard/`: React + Vite + Recharts dashboard matching the four-view UX in the brief.
- `data/reports/{period}_{key}/`: emitted cached report artifacts, including `metrics.json` and per-queue metrics files, as required by the brief.

MotherDuck is the warehouse layer. It must not change the metric logic from the brief. The pipeline computes the validated metrics; the backend reads them.

## Secrets And Environment

Secrets must remain in local environment files or deployment secret stores. They must not be committed.

The implementation should use these environment variable names where relevant:

- `MOTHERDUCK_TOKEN_RW`: pipeline/write path only.
- `MOTHERDUCK_TOKEN_RO`: backend/dashboard read path only.
- `MOTHERDUCK_DATABASE`: target MotherDuck database.
- `VERSATURE_BASE_URL`
- `VERSATURE_CLIENT_ID`
- `VERSATURE_CLIENT_SECRET`
- `VERSATURE_API_VERSION`
- `VERSATURE_ACCESS_TOKEN`, if the auth flow yields or requires a bearer token.
- `SOURCE=csv|api|hybrid`
- `CSV_DIR`
- `DATA_DIR`
- `TIMEZONE=America/Toronto`
- `QUEUE_ENGLISH=8020`
- `QUEUE_FRENCH=8021`
- `QUEUE_AI_OVERFLOW_EN=8030`
- `QUEUE_AI_OVERFLOW_FR=8031`
- `DNIS_PRIMARY=16135949199`
- `DNIS_SECONDARY=6135949199`

ConnectWise settings are out of scope for v1 unless a future ticket-matching requirement is explicitly added.

## Data Sources

### CSV Mode

CSV mode is the first accepted implementation path. It loads four SONAR Queue Detail exports for the selected period. The pipeline must drop `Unnamed: 0` and `Unnamed: 17` before deduplication.

### API Mode

API mode uses Versature API v1.10.0. It must respect:

- `GET /call_queues/`
- `GET /cdrs/users/?start_date={ISO}&end_date={ISO}&cursor={cursor}`
- `GET /call_queues/{q}/stats/`
- `GET /call_queues/{q}/reports/splits/?period={hour|day|month}`
- `GET /call_queues/{q}/reports/dialled_numbers/`

The CDR response array is at top-level `result`, with cursor pagination controlled by `cursor` and `more`.

### Hybrid Mode

Hybrid mode remains available until the API field inventory confirms that operational fields are complete enough to replace CSV inputs.

## Data Model

MotherDuck tables:

- `queue_dim`: four queues with role and language.
- `report_runs`: batch run metadata, source mode, date range, status, validation result.
- `raw_call_legs`: raw CSV/API call-leg rows, preserving duplicates.
- `curated_calls`: deduped one-row-per-call records.
- `queue_period_metrics`: per-queue headline metrics by period.
- `queue_daily_metrics`: chart-ready daily volume/no-answer metrics.
- `queue_hourly_metrics`: chart-ready hourly volume/no-answer metrics.
- `queue_dow_metrics`: day-of-week counts.
- `agent_queue_metrics`: per-agent, per-queue workload.
- `caller_queue_metrics`: per-caller, per-queue frequency.
- `release_reason_metrics`: queue and agent release reason distributions.
- `funnel_language_metrics`: English/French primary-to-overflow counts, routing match, lost calls, and effective answer rate.
- `crossqueue_agent_metrics`: consolidated agent leaderboard.
- `crossqueue_caller_metrics`: consolidated caller leaderboard.
- `comparative_series`: same-hour and same-day cross-queue series.
- `anomalies`: generated anomaly flags and drill-through targets.
- `cdr_field_inventory`: first-run API field inventory for schema drift checks.

Report files:

- `data/reports/{period}_{key}/metrics.json`
- `data/reports/{period}_{key}/metrics_{queue_id}.json`

## Pipeline

The pipeline runs in this order:

1. Load four queue sources for the selected period.
2. Store raw rows in MotherDuck.
3. Drop CSV junk columns.
4. Parse timestamps and durations exactly per the brief.
5. Deduplicate with `keep='last'`.
6. Write `curated_calls`.
7. Compute per-queue metrics.
8. Compute cross-queue funnel, consolidated agents, callers, comparative series, and anomalies.
9. Write dashboard tables to MotherDuck.
10. Emit `metrics.json` and per-queue JSON files.
11. Run April 2026 validation tests against Section 11 of the brief.

Stop-the-line failures:

- Dedup row counts are wrong.
- Funnel numbers are wrong.
- Gabriel Hubert's cross-queue total is wrong.
- Caller `9052833500` cross-queue total is wrong.

## Deduplication

Do not improvise. Follow the brief exactly:

- CSV dedup key: `Orig CallID`
- API dedup key: `from.call_id`
- Keep last occurrence after leg-chronological ordering.
- For API, sort by `to.call_id` if available. First-run verification must confirm that `to.call_id` ordering matches `start_time`; otherwise sort by `start_time`.

## Parsing

CSV timestamps use `MM/DD/YYYY H:MM am|pm` and should be parsed into the `America/Toronto` reporting context.

CSV durations in `Time in Queue`, `Agent Time`, and `Hold Time` may be `MM:SS` or `HH:MM:SS`. Values ending in `ms` are artifacts and should be treated as missing.

API timestamps are ISO 8601. If timezone-naive, the first run must confirm whether they are UTC or `America/Toronto`.

## Metrics

Per-queue metrics must include every item from Section 7 of the brief:

- Headline counts.
- Abandonment/no-answer.
- Duration distributions.
- Daily, hourly, and day-of-week time series.
- Agent leaderboard.
- Caller analysis.

Cross-queue metrics must include every item from Section 8:

- English and French primary-to-overflow funnel analysis.
- Cross-queue agent workload.
- Cross-queue caller analysis.
- Same-hour no-answer overlay.
- Same-day volume overlay.
- Effective answer rate over time.
- Lightweight anomaly detection.

## Dashboard UX

Use React + Vite + Recharts.

Top navigation:

- Overview
- Per Queue
- Cross Queue
- Funnel Detail

A persistent date-range selector appears on every view and defaults to the previous calendar month.

### Overview

- Full-width funnel widget with English and French side by side.
- Four queue cards in a 2x2 grid.
- Full-width anomaly strip.
- Effective answer rate cards for English and French.

### Per Queue

- Queue header with ID, name, and role badge.
- Six-stat row.
- Daily volume bar chart with busiest day highlighted in gold and quietest in red.
- Hourly volume plus no-answer combo chart.
- Day-of-week distribution.
- Release-reason horizontal bars.
- Agent leaderboard.
- Caller observations.

### Cross Queue

- Consolidated agent leaderboard with per-queue columns and total.
- Cross-queue caller leaderboard with a 2+ queues filter.
- Same-hour no-answer overlay chart.
- Same-day volume overlay chart with raw/normalized toggle.

### Funnel Detail

- Per-language funnel diagrams with counts and percentages.
- Routing-match diagnostic with explicit unaccounted bucket.
- Effective-answer-rate time series.

### Visual Style

Follow the brief:

- Primary English: `#0F4C5C`
- Primary French: `#B5341A`
- Overflow English: `#185FA5`
- Overflow French: `#993C1D`
- No-answer/loss: `#A32D2D`
- Small 10-11px monospace labels for axes and numeric callouts.
- Editorial display headings using a serif display family such as Fraunces, Newsreader, or DM Serif Display.
- Light card-based layout with generous whitespace.
- No dark mode for v1.
- Every chart gets one italicized takeaway caption.

## Interactivity And Exports

Required:

- Date presets: yesterday, last 7 days, last 30 days, this month, last month, custom.
- Per-chart hover tooltips with exact values.
- Click-through from overview anomalies into relevant detail views.
- PNG export at chart level.
- CSV export at data level.

Optional after required scope:

- Agent drill-through view.

## Validation

The validation suite must encode every expected April 2026 reference number from Section 11 of the brief, including:

- All four queue raw and dedup counts.
- Busiest and quietest days.
- No-agent/no-answer metrics.
- Queue and agent duration medians.
- Agent/caller leaderboards.
- Day-of-week totals.
- Worst no-answer hours.
- English and French routing match.
- English and French end-to-end lost and effective answer rates.
- Gabriel Hubert total of 299 calls.
- Caller `9052833500` total of 63 calls.
- API exploration sample expectations.

Acceptance requires CSV mode to work end-to-end before API integration is considered complete.

## Known Unknowns To Document In The App

The implementation must explicitly handle or document the brief's pending verification items:

- API field inventory completeness.
- Caller number field name.
- Restricted caller representation.
- API leg ordering.
- Queue ID type in API paths.
- Token refresh behavior.
- API timestamp timezone.
- `CSH - BUILDS` identity.
- English routing gap.
- Restricted caller non-aggregation.

## Out Of Scope

Match the brief:

- Real-time or streaming ingestion.
- Forecasting or machine-learning routing recommendations.
- Write operations against the Versature API.
- Alerting or paging integrations.
- Multi-tenancy.
- Historical backfill earlier than 2026-04-01.

## Open Data Requirement

The workspace currently includes a queue 8020 workbook reference. Full v1 acceptance requires the remaining April 2026 queue source files for 8021, 8030, and 8031, or verified API access that can reproduce the Section 11 reference set.

