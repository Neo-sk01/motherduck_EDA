# Static Analytics Dashboard Design

Date: 2026-05-06

## Source Of Truth

This dashboard design follows `AI_AGENT_PROMPT_unified_dashboard.md`, Revision 3, May 5, 2026, and the validated data foundation now committed on `main`.

The dashboard must preserve the four-queue topology:

| Queue ID | Name | Role | Language | Accent |
|---|---|---|---|---|
| 8020 | CSR English | Primary | English | Deep teal `#0F4C5C` |
| 8021 | CSR French | Primary | French | Rust `#B5341A` |
| 8030 | CSR Overflow English | Overflow | English | Blue `#185FA5` |
| 8031 | CSR Overflow French | Overflow | French | Coral `#993C1D` |

The first accepted dashboard target is the static report contract:

- `data/reports/{period}_{start}_{end}/metrics.json`
- `data/reports/{period}_{start}_{end}/metrics_{queue_id}.json`

The April 2026 report is the canonical v1 reference. The UI must visibly match these validated values when pointed at `month_2026-04-01_2026-04-30`:

- Queue totals: 8020 `1,181`, 8021 `66`, 8030 `343`, 8031 `30`.
- English routing match `98.8%`, effective answer rate `84.7%`.
- French routing match `88.2%`, effective answer rate `87.9%`.
- Gabriel Hubert total `299`.
- Caller `9052833500` total `63`.

## Approved Approach

Build a `dashboard/` React + Vite + TypeScript app that reads generated report JSON directly. No backend API is required for v1.

Reasons:

- It uses the validated report output without introducing another correctness layer.
- It is static-deployable and can run locally or behind a simple static host.
- The data-loader boundary can later swap from file fetches to a MotherDuck-backed API without rewriting the UI components.

Alternatives considered:

- **Backend API first:** Better for live MotherDuck reads, but adds more moving parts before the UI is proven.
- **Streamlit:** Fast for Python-native exploration, but weaker fit for a polished multi-view web app and future frontend deployment.

## Goals

The dashboard must answer:

1. What happened on each of the four queues for the selected period?
2. What happened end-to-end from primary queues to overflow queues?
3. Which agents, callers, hours, and routing gaps create operational risk?

The first screen is the dashboard itself. Do not build a landing page, marketing hero, or explanatory wrapper.

## Non-Goals

- No live Versature API reads in the browser.
- No write operations from the dashboard.
- No authentication in v1.
- No real-time streaming.
- No forecasts or ML recommendations.
- No ConnectWise ticket matching.

## Information Architecture

The app has one shell with four top-level views:

1. **Overview**
2. **Per Queue**
3. **Cross Queue**
4. **Funnel Detail**

The app shell includes:

- Compact brand/title area: `NeoLore Queue Analytics`.
- Top navigation tabs for the four views.
- Persistent report selector/date controls.
- Status text showing loaded report period and validation state.
- Export controls where supported.

The default report is April 2026 when the report exists. If no report exists, show a useful empty state with the expected report path and the CLI command to generate it.

## Data Loading

Create a dashboard data layer under `dashboard/src/data/`.

Required behavior:

- Load `metrics.json` from a configurable base path.
- Default path: `/data/reports/month_2026-04-01_2026-04-30/metrics.json`.
- Allow a local fallback fixture checked into `dashboard/src/fixtures/april-2026-metrics.json` if static file fetch fails in development.
- Validate the minimum expected shape before rendering:
  - `period`
  - `date_range`
  - `queues`
  - `crossqueue.funnels`
  - `crossqueue.agents`
  - `crossqueue.callers`
  - `anomalies`
- Surface source gaps and validation metadata from `metrics.source_gaps` and `metrics.validation`.

The data layer must keep the UI isolated from the report source. Later, an API-backed loader can implement the same interface.

## Visual System

The UI is operational and analytical: quiet, dense enough for repeated use, and polished without feeling like a marketing page.

Visual rules:

- Background: clean light neutral, no dark mode for v1.
- Cards: 8px radius or less.
- No nested cards.
- No decorative blobs, gradient orbs, or bokeh.
- Typography:
  - Display headings use a serif display family such as `Newsreader`, `Fraunces`, or a local fallback.
  - UI labels, chart axes, and numeric callouts use a small mono style such as `JetBrains Mono`, `IBM Plex Mono`, or fallback monospace.
  - Body/UI chrome uses a clean system sans fallback.
- Color:
  - Primary English `#0F4C5C`.
  - Primary French `#B5341A`.
  - Overflow English `#185FA5`.
  - Overflow French `#993C1D`.
  - Loss/no-answer `#A32D2D`.
  - Busiest highlight muted gold.
  - Quietest highlight muted red.
- Every chart has one italic one-line takeaway caption.
- Controls use familiar UI affordances:
  - Tabs for views.
  - Segmented controls for report/date presets.
  - Select menu for queue choice.
  - Icon buttons for export/download.

## Overview View

Purpose: executive snapshot of period health.

Widgets:

- **Language funnel widget:** English and French side-by-side, showing primary calls, primary answered, primary failed, overflow received, overflow answered, lost, routing match, and effective answer rate. Lost uses the no-answer/loss accent.
- **Effective answer rate cards:** one per language, large percent plus supporting counts.
- **Four queue cards:** 2x2 desktop grid, single column mobile. Each card shows total calls, no-agent rate, busiest hour, top agent, and a daily-volume sparkline.
- **Anomaly strip:** horizontal row of anomaly cards with severity, kind, description, and click-through target.

Interactions:

- Clicking a queue card opens Per Queue with that queue selected.
- Clicking an anomaly target opens the relevant view and queue/hour/agent context when available.
- Hovering charts/tooltips reveals exact values.

## Per Queue View

Purpose: standard EDA drilldown for a selected queue.

Controls:

- Queue select or segmented queue switcher with all four queues.

Widgets:

- Queue header with queue ID, queue name, language, and role badge.
- Six-stat row:
  - total calls
  - average calls per active day
  - busiest day
  - no-agent percentage
  - unique/top agents from leaderboard
  - top caller
- Daily volume bar chart. Highlight busiest and quietest days.
- Hourly volume plus no-answer line chart.
- Day-of-week bar chart.
- Release-reason horizontal bars for queue reasons and agent reasons.
- Agent leaderboard top 10 with proportional bars and percent of answered.
- Caller observations:
  - top callers
  - restricted caller note if present
  - repeated caller emphasis when calls are high

Interactions:

- Hover chart values.
- Export chart PNG.
- Export visible table data CSV.

## Cross Queue View

Purpose: show workload and caller behavior that only appears when queues are consolidated.

Widgets:

- Consolidated agent leaderboard:
  - columns for `8020`, `8021`, `8030`, `8031`, and total.
  - default sort by total descending.
  - Gabriel Hubert must be visibly easy to find and show total `299` in April.
- Cross-queue caller leaderboard:
  - same column shape as agents.
  - quick filter for callers appearing on two or more queues.
  - caller `9052833500` must show total `63` in April.
- Same-hour no-answer overlay:
  - all four queues on one plot.
  - line or compact grouped bars acceptable.
- Same-day volume overlay:
  - toggle raw vs normalized view.

Interactions:

- Sort leaderboards by any numeric column.
- Toggle caller filter.
- Export tables as CSV.

## Funnel Detail View

Purpose: explain primary-to-overflow routing behavior clearly.

Widgets:

- English funnel diagram.
- French funnel diagram.
- Routing-match diagnostic:
  - `primary_failed`
  - `overflow_received`
  - `unaccounted`
- Lost/effective answer summary.

Display rules:

- Box widths must be proportional enough to reveal scale, but labels must remain readable.
- Lost endpoints are red.
- The `unaccounted` bucket is shown separately from `lost`.
- For April, English shows routing match `98.8%`; French shows `88.2%`.

## Exports

Required v1 export support:

- CSV export for visible leaderboards and table-shaped chart data.
- PNG export for chart frames.

Implementation can use `html-to-image` or a similar client-side capture library for chart PNG export. Production must not show inert or disabled export controls. If PNG export cannot be made reliable during implementation, stop and ask before narrowing the export scope.

## Error And Empty States

The dashboard must handle:

- Report file missing.
- Invalid JSON.
- Missing required report fields.
- `source_gaps` present.
- Empty queues or absent chart series.

Error states are operational, not dramatic. They show:

- What failed.
- Which report path was attempted.
- How to generate the report using the pipeline CLI.

## Accessibility And Responsiveness

Requirements:

- Desktop-first, but fully usable at mobile widths.
- No horizontal overflow on mobile.
- Keyboard-accessible tabs, buttons, selects, and table sorting.
- Tooltips must not be the only way to access exact values; core values are visible in labels/tables.
- Text must not overlap or truncate critical numbers.
- Use semantic headings and landmarks.

## Component Boundaries

Recommended structure:

```text
dashboard/
  src/
    App.tsx
    main.tsx
    data/
      reportLoader.ts
      reportTypes.ts
    components/
      AppShell.tsx
      MetricCard.tsx
      QueueCard.tsx
      ChartFrame.tsx
      ExportButton.tsx
    views/
      OverviewView.tsx
      PerQueueView.tsx
      CrossQueueView.tsx
      FunnelDetailView.tsx
    charts/
      FunnelChart.tsx
      DailyVolumeChart.tsx
      HourlyNoAnswerChart.tsx
      DowChart.tsx
      ReleaseReasonsChart.tsx
      OverlayCharts.tsx
    fixtures/
      april-2026-metrics.json
    styles/
      tokens.css
      app.css
```

Keep `App.tsx` as composition and state glue. Do not build the dashboard as one monolithic component.

## Testing And Verification

Implementation must include:

- Unit tests for data loading and report-shape validation.
- Component tests or focused render tests for the major views where practical.
- Full build verification.
- Browser verification on desktop and mobile viewports.
- Visual/fidelity check against the approved text design and generated concept if one is used before coding.

Functional validation must confirm that the April report visibly renders:

- queue totals `1181 / 66 / 343 / 30`
- English `98.8%` routing and `84.7%` effective answer
- French `88.2%` routing and `87.9%` effective answer
- Gabriel Hubert `299`
- caller `9052833500` `63`

## Rollout

Phase 1:

- Scaffold React + Vite dashboard.
- Add fixture/report loader.
- Build all four views using static JSON.
- Verify locally.

Phase 2:

- Add exports and polish interactions.
- Copy generated report files into a static-served location or document how to publish them.

Phase 3:

- Add optional backend/MotherDuck API loader that implements the same report-loader interface.
