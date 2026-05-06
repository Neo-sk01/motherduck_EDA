# Static Analytics Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` when delegation is explicitly authorized, or `superpowers:executing-plans` for inline execution. Track progress by updating each `- [ ]` checkbox as work completes.

**Goal:** Build the approved NeoLore Queue Analytics dashboard as a static React + Vite + TypeScript application under `dashboard/`, using the validated report JSON produced by the data foundation.

**Architecture:** The dashboard reads `metrics.json` from a static path, validates the report shape, falls back to a checked-in April 2026 fixture during local development, and renders four analytical views: Overview, Per Queue, Cross Queue, and Funnel Detail. All MotherDuck and Versature access remains in the existing Python pipeline for v1; the frontend has no secrets and no write path.

**Tech Stack:** React, Vite, TypeScript, Vitest, Testing Library, Recharts, lucide-react, html-to-image.

---

## Scope Boundary

This plan implements Phase 1 and Phase 2 of `docs/superpowers/specs/2026-05-06-static-dashboard-design.md`:

- React + Vite dashboard scaffold.
- Static `metrics.json` data loading with local April fixture fallback.
- Four dashboard views matching the approved information architecture.
- CSV exports for visible table/chart data.
- PNG exports for chart frames.
- Desktop and mobile browser verification.
- Functional validation against the April 2026 reference numbers.

This plan does not implement:

- Browser-side MotherDuck access.
- Backend API routes.
- Authentication.
- Live Versature reads.
- ConnectWise matching.
- Forecasts or ML recommendations.

## Source Data Contract

The frontend must load the report emitted by `pipeline.report.write_report_bundle`:

```text
data/reports/{period}_{start}_{end}/metrics.json
```

The default v1 report path is:

```text
/data/reports/month_2026-04-01_2026-04-30/metrics.json
```

Minimum renderable shape:

```ts
{
  period: string;
  date_range: { start: string; end: string };
  generated_at?: string;
  queues: Record<string, QueueMetrics>;
  crossqueue: {
    funnels: Record<"English" | "French", FunnelMetrics>;
    agents: ConsolidatedAgent[];
    callers: ConsolidatedCaller[];
    same_hour_no_answer: SameHourNoAnswerPoint[];
    same_day_volume: SameDayVolumePoint[];
  };
  anomalies: Anomaly[];
  source_gaps: SourceGap[];
  validation: { status?: string; [key: string]: unknown };
}
```

April 2026 must visibly render:

- Queue totals: `1181 / 66 / 343 / 30`.
- English routing match `98.8%`, effective answer rate `84.7%`.
- French routing match `88.2%`, effective answer rate `87.9%`.
- Gabriel Hubert total `299`.
- Caller `9052833500` total `63`.

## Visual Direction

The accepted design direction is an operational analytics workspace:

- Light neutral background.
- One compact app shell, not a landing page.
- Tabs for the four top-level views.
- 8px maximum card radius.
- No nested cards.
- No decorative blobs, gradient orbs, or bokeh.
- Queue colors:
  - `8020`: `#0F4C5C`
  - `8021`: `#B5341A`
  - `8030`: `#185FA5`
  - `8031`: `#993C1D`
  - loss/no-answer: `#A32D2D`
- Display headings use a serif fallback stack.
- Labels, axes, and numeric callouts use a small monospace fallback stack.
- Every chart frame includes a one-line italic takeaway caption.

## File Map

- Create `dashboard/package.json`: npm scripts and frontend dependencies.
- Create `dashboard/package-lock.json`: locked dependency versions after install.
- Create `dashboard/index.html`: Vite mount point.
- Create `dashboard/vite.config.ts`: Vite, React, and Vitest config.
- Create `dashboard/tsconfig.json`: app TypeScript config.
- Create `dashboard/tsconfig.node.json`: Vite config TypeScript config.
- Create `dashboard/src/main.tsx`: React entrypoint.
- Create `dashboard/src/App.tsx`: app state, data load, and view composition.
- Create `dashboard/src/App.test.tsx`: smoke and April reference render tests.
- Create `dashboard/src/data/reportTypes.ts`: report contract types and queue metadata.
- Create `dashboard/src/data/reportLoader.ts`: fetch/fallback/validation logic.
- Create `dashboard/src/data/reportLoader.test.ts`: loader and shape-validation tests.
- Create `dashboard/src/data/selectors.ts`: derived metrics used across views.
- Create `dashboard/src/data/selectors.test.ts`: funnel, top entity, and chart selector tests.
- Create `dashboard/src/fixtures/april-2026-metrics.json`: checked-in April reference fixture.
- Create `dashboard/public/data/reports/month_2026-04-01_2026-04-30/metrics.json`: static-served default report copy for local dev.
- Create `dashboard/src/components/AppShell.tsx`: title, tabs, report controls, status.
- Create `dashboard/src/components/MetricCard.tsx`: compact KPI cards.
- Create `dashboard/src/components/QueueCard.tsx`: overview queue summary card.
- Create `dashboard/src/components/ChartFrame.tsx`: chart wrapper with caption and PNG export.
- Create `dashboard/src/components/ExportButton.tsx`: icon button with accessible label.
- Create `dashboard/src/components/DataTable.tsx`: sortable table for agents/callers.
- Create `dashboard/src/components/EmptyState.tsx`: missing/invalid report guidance.
- Create `dashboard/src/views/OverviewView.tsx`: executive snapshot.
- Create `dashboard/src/views/PerQueueView.tsx`: selected queue drilldown.
- Create `dashboard/src/views/CrossQueueView.tsx`: consolidated agents/callers and overlays.
- Create `dashboard/src/views/FunnelDetailView.tsx`: primary-to-overflow routing detail.
- Create `dashboard/src/charts/FunnelChart.tsx`: proportional funnel bars.
- Create `dashboard/src/charts/DailyVolumeChart.tsx`: daily bar/sparkline chart.
- Create `dashboard/src/charts/HourlyNoAnswerChart.tsx`: calls plus no-answer rate.
- Create `dashboard/src/charts/DowChart.tsx`: day-of-week bars.
- Create `dashboard/src/charts/ReleaseReasonsChart.tsx`: horizontal reason bars.
- Create `dashboard/src/charts/OverlayCharts.tsx`: cross-queue hourly/day overlays.
- Create `dashboard/src/utils/format.ts`: number, percent, date, duration helpers.
- Create `dashboard/src/utils/exportCsv.ts`: CSV serialization and download helper.
- Create `dashboard/src/utils/exportCsv.test.ts`: CSV escaping and column tests.
- Create `dashboard/src/utils/exportPng.ts`: chart-frame PNG capture.
- Create `dashboard/src/styles/tokens.css`: color, type, spacing, elevation tokens.
- Create `dashboard/src/styles/app.css`: layout, responsive rules, component styling.
- Update `README.md`: dashboard setup and run instructions.
- Update `.gitignore`: ignore `dashboard/node_modules/`, `dashboard/dist/`, generated screenshots if any.

---

### Task 0: Visual Concept Checkpoint

**Files:**
- No required file changes.

- [ ] **Step 1: Create or confirm the visual reference before coding**

Before writing dashboard UI code, produce one static visual concept from the approved design spec using the image generation workflow, then inspect it and keep it as the visual reference for spacing, density, color balance, and information hierarchy.

If the user explicitly opts out of a generated visual concept, record that the approved text spec is the visual contract and continue. Do not block implementation on multiple design rounds.

- [ ] **Step 2: Apply the concept constraints during implementation**

Use the concept and spec to keep the UI:

- operational and data-first;
- light neutral, not dark;
- visually balanced across the four queue colors;
- free of decorative blobs, orbs, bokeh, and marketing hero treatment;
- readable at desktop and mobile widths.

---

### Task 1: Worktree And Dashboard App Scaffold

**Files:**
- Create: `dashboard/package.json`
- Create: `dashboard/index.html`
- Create: `dashboard/vite.config.ts`
- Create: `dashboard/tsconfig.json`
- Create: `dashboard/tsconfig.node.json`
- Create: `dashboard/src/main.tsx`
- Create: `dashboard/src/App.tsx`
- Create: `dashboard/src/styles/tokens.css`
- Create: `dashboard/src/styles/app.css`
- Update: `.gitignore`
- Update: `README.md`

- [ ] **Step 1: Create an isolated implementation branch/worktree**

Use a feature branch such as `dashboard-static-v1`. If working in a worktree, create it from the clean `main` branch:

```bash
git switch main
git pull --ff-only
mkdir -p .worktrees
git worktree add .worktrees/dashboard-static-v1 -b dashboard-static-v1
```

Expected: the worktree opens on `dashboard-static-v1` with a clean status.

- [ ] **Step 2: Add the Vite React scaffold**

Create `dashboard/package.json`:

```json
{
  "name": "neolore-queue-dashboard",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc -b && vite build",
    "preview": "vite preview --host 127.0.0.1",
    "test": "vitest --environment jsdom"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^5.0.0",
    "html-to-image": "^1.11.13",
    "lucide-react": "^0.468.0",
    "recharts": "^2.15.0",
    "vite": "^6.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.1.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript": "^5.7.0",
    "vitest": "^2.1.0"
  }
}
```

Create `dashboard/index.html` with one `#root` mount and a title of `NeoLore Queue Analytics`.

Create `dashboard/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles/tokens.css";
import "./styles/app.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

Create a temporary `App.tsx` that renders the app title and four tabs as static labels. This is only to prove the scaffold; later tasks replace it with the real shell and data flow.

- [ ] **Step 3: Install and verify the scaffold**

From `dashboard/`:

```bash
npm install
npm run test -- --run
npm run build
```

Expected:

- `package-lock.json` is created.
- Vitest passes.
- Vite build emits `dashboard/dist/`.

- [ ] **Step 4: Commit scaffold**

```bash
git add dashboard .gitignore README.md
git commit -m "chore: scaffold dashboard app"
```

---

### Task 2: April Fixture And Static Report Copy

**Files:**
- Create: `dashboard/src/fixtures/april-2026-metrics.json`
- Create: `dashboard/public/data/reports/month_2026-04-01_2026-04-30/metrics.json`

- [ ] **Step 1: Generate the April report from the existing pipeline if needed**

If `data/reports/month_2026-04-01_2026-04-30/metrics.json` is not present, run:

```bash
python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30
```

Expected: the pipeline emits `data/reports/month_2026-04-01_2026-04-30/metrics.json`. If the full April CSV source set is unavailable, stop and ask the user for the four source files because the fixture must be the validated reference, not synthetic data.

- [ ] **Step 2: Copy the validated April report into dashboard locations**

Copy the generated `metrics.json` to:

```text
dashboard/src/fixtures/april-2026-metrics.json
dashboard/public/data/reports/month_2026-04-01_2026-04-30/metrics.json
```

Do not edit numeric values by hand.

- [ ] **Step 3: Verify the fixture reference values**

Run a short read-only check that asserts:

```text
queues.8020.total_calls = 1181
queues.8021.total_calls = 66
queues.8030.total_calls = 343
queues.8031.total_calls = 30
crossqueue.funnels.English.routing_match ~= 0.988
crossqueue.funnels.English.effective_answer_rate ~= 0.847
crossqueue.funnels.French.routing_match ~= 0.882
crossqueue.funnels.French.effective_answer_rate ~= 0.879
Gabriel Hubert total_calls = 299
caller 9052833500 total_calls = 63
```

Expected: all values match the existing April reference test.

- [ ] **Step 4: Commit fixture**

```bash
git add dashboard/src/fixtures dashboard/public/data
git commit -m "test: add april dashboard fixture"
```

---

### Task 3: Report Types, Validation, And Loader

**Files:**
- Create: `dashboard/src/data/reportTypes.ts`
- Create: `dashboard/src/data/reportLoader.ts`
- Create: `dashboard/src/data/reportLoader.test.ts`

- [ ] **Step 1: Write loader tests first**

Create tests for:

- Valid fixture passes `validateReport`.
- Missing `crossqueue.funnels` throws `ReportValidationError`.
- `loadReport` returns `{ status: "loaded", source: "remote" }` when fetch succeeds.
- `loadReport` returns `{ status: "loaded", source: "fixture" }` when fetch fails and fallback is enabled.
- Invalid JSON returns `{ status: "error" }` with the attempted path.

Use mocked `fetch` responses in `reportLoader.test.ts`; do not depend on the dev server.

- [ ] **Step 2: Define the TypeScript report contract**

Create discriminated types for:

- `QueueId = "8020" | "8021" | "8030" | "8031"`.
- `QueueMetadata`.
- `QueueMetrics`.
- `FunnelMetrics`.
- `ConsolidatedAgent`.
- `ConsolidatedCaller`.
- `SameHourNoAnswerPoint`.
- `SameDayVolumePoint`.
- `Anomaly`.
- `DashboardReport`.
- `ReportLoadResult`.

Define `QUEUE_META` with the exact names, roles, languages, and colors from the design spec.

- [ ] **Step 3: Implement validation and loading**

`reportLoader.ts` should export:

```ts
export const DEFAULT_REPORT_PATH =
  "/data/reports/month_2026-04-01_2026-04-30/metrics.json";

export class ReportValidationError extends Error {}

export function validateReport(value: unknown): DashboardReport;

export async function loadReport(options?: {
  path?: string;
  useFixtureFallback?: boolean;
}): Promise<ReportLoadResult>;
```

Validation must check only the fields required to render v1. It should not reject extra report fields.

- [ ] **Step 4: Verify**

From `dashboard/`:

```bash
npm run test -- --run
npm run build
```

Expected: loader tests pass and TypeScript accepts the report contract.

- [ ] **Step 5: Commit loader**

```bash
git add dashboard/src/data
git commit -m "feat: add dashboard report loader"
```

---

### Task 4: Selectors, Formatting, CSV Export, And PNG Export Utilities

**Files:**
- Create: `dashboard/src/data/selectors.ts`
- Create: `dashboard/src/data/selectors.test.ts`
- Create: `dashboard/src/utils/format.ts`
- Create: `dashboard/src/utils/exportCsv.ts`
- Create: `dashboard/src/utils/exportCsv.test.ts`
- Create: `dashboard/src/utils/exportPng.ts`

- [ ] **Step 1: Write selector and CSV tests first**

Selector tests:

- `getQueueSummaries(report)` returns four queues in `8020`, `8021`, `8030`, `8031` order.
- `getTopAgent(report)` returns Gabriel Hubert with `299` for April.
- `getTopCaller(report)` can find `9052833500` with `63`.
- `getLanguageFunnels(report)` formats English and French values without losing raw numbers.
- `getCallerRows(report, { multiQueueOnly: true })` keeps callers with calls in at least two queue columns.

CSV tests:

- Headers are preserved in the requested order.
- Commas, quotes, and newlines are escaped.
- Empty values serialize as blank cells.

- [ ] **Step 2: Implement selectors**

Keep selectors pure and UI-free. They should return sorted rows and chart data with stable keys, but no JSX.

- [ ] **Step 3: Implement format helpers**

Add helpers:

```ts
formatInteger(1181) => "1,181"
formatPercent(0.847, 1) => "84.7%"
formatHour(13) => "13:00"
formatDuration(92) => "1m 32s"
formatDateLabel("2026-04-01") => "Apr 1"
```

- [ ] **Step 4: Implement CSV and PNG utilities**

CSV:

```ts
export function toCsv<T extends Record<string, unknown>>(
  rows: T[],
  columns: Array<{ key: keyof T; header: string }>,
): string;

export function downloadCsv(filename: string, csv: string): void;
```

PNG:

```ts
export async function downloadElementPng(
  element: HTMLElement,
  filename: string,
): Promise<void>;
```

Use `html-to-image` in `exportPng.ts`. If chart capture fails in browser verification, stop and ask before hiding PNG export controls.

- [ ] **Step 5: Verify and commit**

```bash
npm run test -- --run
npm run build
git add dashboard/src/data dashboard/src/utils
git commit -m "feat: add dashboard data selectors"
```

---

### Task 5: App Shell, Data States, And Navigation

**Files:**
- Create: `dashboard/src/components/AppShell.tsx`
- Create: `dashboard/src/components/EmptyState.tsx`
- Update: `dashboard/src/App.tsx`
- Create: `dashboard/src/App.test.tsx`
- Update: `dashboard/src/styles/tokens.css`
- Update: `dashboard/src/styles/app.css`

- [ ] **Step 1: Write shell render tests**

Tests should assert:

- The app renders `NeoLore Queue Analytics`.
- The four tabs are present.
- Loaded status shows `2026-04-01` through `2026-04-30` for the April fixture.
- Invalid report state shows the attempted path and pipeline command.
- Keyboard tab selection changes the active view.

- [ ] **Step 2: Implement the shell**

`App.tsx` owns:

- `activeView`.
- `selectedQueueId`, default `8020`.
- `reportPath`, default `DEFAULT_REPORT_PATH`.
- `loadReport` lifecycle.

`AppShell` owns:

- Title.
- View tabs.
- Report path input or compact report selector.
- Loaded/report status.
- Validation/source-gap status.

`EmptyState` shows:

```bash
python -m pipeline.main --source csv --period month --start 2026-04-01 --end 2026-04-30
```

- [ ] **Step 3: Add visual tokens and base layout**

Create token CSS for colors, typography, spacing, borders, focus rings, and chart palette. Use system fallbacks so no network font fetch is required.

Base layout rules:

- No horizontal overflow at `320px` width.
- App shell uses tabs, not a hero page.
- Main sections are unframed layouts; cards are only individual repeated items or chart/table surfaces.

- [ ] **Step 4: Verify and commit**

```bash
npm run test -- --run
npm run build
git add dashboard/src
git commit -m "feat: add dashboard shell"
```

---

### Task 6: Shared Analytical Components

**Files:**
- Create: `dashboard/src/components/MetricCard.tsx`
- Create: `dashboard/src/components/QueueCard.tsx`
- Create: `dashboard/src/components/ChartFrame.tsx`
- Create: `dashboard/src/components/ExportButton.tsx`
- Create: `dashboard/src/components/DataTable.tsx`

- [ ] **Step 1: Implement components with accessible controls**

Components must use plain data props and avoid fetching their own report data.

Requirements:

- `MetricCard`: label, value, optional supporting text, optional tone.
- `QueueCard`: queue metadata, total calls, no-agent rate, busiest hour, top agent, mini daily sparkline.
- `ChartFrame`: title, caption, children, optional PNG export.
- `ExportButton`: lucide icon, accessible label, tooltip/title.
- `DataTable`: sortable column headers, numeric alignment, CSV export hook.

- [ ] **Step 2: Add focused component tests where behavior matters**

Test `DataTable` sorting and accessible button names. Component tests can use tiny inline data; they do not need the whole April fixture.

- [ ] **Step 3: Verify and commit**

```bash
npm run test -- --run
npm run build
git add dashboard/src/components
git commit -m "feat: add dashboard shared components"
```

---

### Task 7: Overview View

**Files:**
- Create: `dashboard/src/views/OverviewView.tsx`
- Create: `dashboard/src/charts/FunnelChart.tsx`
- Create: `dashboard/src/charts/DailyVolumeChart.tsx`
- Update: `dashboard/src/App.tsx`
- Update: `dashboard/src/App.test.tsx`

- [ ] **Step 1: Write overview validation tests**

Tests should render the app with the April fixture and assert visible text for:

- `1,181`
- `66`
- `343`
- `30`
- `98.8%`
- `84.7%`
- `88.2%`
- `87.9%`

- [ ] **Step 2: Implement Overview**

Render:

- English and French funnel widgets.
- Effective answer rate cards.
- Four queue cards in responsive grid.
- Anomaly strip with severity, kind, description, and click target behavior.

Interactions:

- Clicking a queue card switches to Per Queue and selects that queue.
- Clicking an anomaly target switches to the relevant view when `target.view` is known.
- Tooltips show exact chart values, but key values also appear as visible labels.

- [ ] **Step 3: Verify and commit**

```bash
npm run test -- --run
npm run build
git add dashboard/src
git commit -m "feat: add overview dashboard"
```

---

### Task 8: Per Queue View

**Files:**
- Create: `dashboard/src/views/PerQueueView.tsx`
- Create: `dashboard/src/charts/HourlyNoAnswerChart.tsx`
- Create: `dashboard/src/charts/DowChart.tsx`
- Create: `dashboard/src/charts/ReleaseReasonsChart.tsx`
- Update: `dashboard/src/App.tsx`
- Update: `dashboard/src/App.test.tsx`

- [ ] **Step 1: Write per-queue interaction tests**

Tests should assert:

- Selecting queue `8021` displays `CSR French`.
- The six-stat row includes total calls, average active-day calls, busiest day, no-agent rate, top agent, and top caller.
- Agent leaderboard table can export CSV.

- [ ] **Step 2: Implement Per Queue**

Render:

- Queue selector or segmented switcher.
- Queue header with queue ID, name, language, and role badge.
- Six-stat row.
- Daily volume chart with busiest/quietest emphasis.
- Hourly calls plus no-answer rate chart.
- Day-of-week chart.
- Queue and agent release reason bars.
- Agent leaderboard top 10.
- Top callers and repeated caller notes.

Charts must sit in `ChartFrame` with PNG export controls.

- [ ] **Step 3: Verify and commit**

```bash
npm run test -- --run
npm run build
git add dashboard/src
git commit -m "feat: add per-queue drilldown"
```

---

### Task 9: Cross Queue View

**Files:**
- Create: `dashboard/src/views/CrossQueueView.tsx`
- Create: `dashboard/src/charts/OverlayCharts.tsx`
- Update: `dashboard/src/App.tsx`
- Update: `dashboard/src/App.test.tsx`

- [ ] **Step 1: Write cross-queue reference tests**

Tests should assert:

- Gabriel Hubert is visible with total `299`.
- Caller `9052833500` is visible with total `63`.
- Sorting by a queue column changes row order.
- Enabling the two-or-more-queues filter hides single-queue callers and keeps cross-queue callers.

- [ ] **Step 2: Implement Cross Queue**

Render:

- Consolidated agent leaderboard with columns `8020`, `8021`, `8030`, `8031`, `Total`.
- Consolidated caller leaderboard with the same queue column shape.
- Two-or-more-queues caller filter.
- Same-hour no-answer overlay across all queues.
- Same-day volume overlay with raw vs normalized segmented toggle.

Use `DataTable` for sortable and exportable rows.

- [ ] **Step 3: Verify and commit**

```bash
npm run test -- --run
npm run build
git add dashboard/src
git commit -m "feat: add cross-queue analytics"
```

---

### Task 10: Funnel Detail View

**Files:**
- Create: `dashboard/src/views/FunnelDetailView.tsx`
- Update: `dashboard/src/charts/FunnelChart.tsx`
- Update: `dashboard/src/App.tsx`
- Update: `dashboard/src/App.test.tsx`

- [ ] **Step 1: Write funnel detail tests**

Tests should assert:

- English primary failed and overflow received are both visible.
- French unaccounted count is visible.
- English routing match is visible as `98.8%`.
- French routing match is visible as `88.2%`.

- [ ] **Step 2: Implement Funnel Detail**

Render for each language:

- Primary calls.
- Primary answered.
- Primary failed.
- Overflow received.
- Overflow answered.
- Lost.
- Unaccounted.
- Routing match.
- Effective answer rate.

Display rules:

- Bar/box widths are proportional but labels stay readable.
- Lost endpoints use `#A32D2D`.
- Unaccounted is separate from lost.
- The layout remains readable at mobile widths.

- [ ] **Step 3: Verify and commit**

```bash
npm run test -- --run
npm run build
git add dashboard/src
git commit -m "feat: add funnel detail view"
```

---

### Task 11: Responsive Polish, Export Verification, And Browser Checks

**Files:**
- Update: `dashboard/src/styles/app.css`
- Update: dashboard components/views as needed.

- [ ] **Step 1: Run automated verification**

From `dashboard/`:

```bash
npm run test -- --run
npm run build
```

Expected: all tests pass and the production build succeeds.

- [ ] **Step 2: Start the dev server**

```bash
npm run dev -- --port 5173
```

Expected: Vite serves the dashboard at `http://127.0.0.1:5173`.

- [ ] **Step 3: Browser-verify desktop**

Open `http://127.0.0.1:5173` in the browser and verify:

- Overview loads without console-blocking errors.
- April reference numbers are visible.
- Queue-card click opens Per Queue with the selected queue.
- Cross Queue shows Gabriel Hubert `299`.
- Cross Queue shows caller `9052833500` `63`.
- Funnel Detail shows English `98.8%` and French `88.2%`.
- CSV exports download useful data.
- PNG export captures a nonblank chart frame.

- [ ] **Step 4: Browser-verify mobile**

Use a mobile viewport around `390x844` and verify:

- No horizontal overflow.
- Tabs and controls remain usable.
- Tables scroll or adapt without clipping important values.
- Chart labels do not overlap critical numbers.
- Funnel labels remain readable.

- [ ] **Step 5: Capture final visual check**

Capture at least one desktop and one mobile screenshot for inspection. Before claiming completion, inspect the latest screenshot and, if a generated visual concept was used, inspect that concept as well.

- [ ] **Step 6: Commit polish**

```bash
git add dashboard
git commit -m "polish: verify dashboard responsive exports"
```

---

### Task 12: Documentation And Final Integration

**Files:**
- Update: `README.md`

- [ ] **Step 1: Document dashboard usage**

Add a `Dashboard` section to `README.md` with these exact commands and paths:

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

- [ ] **Step 2: Final verification**

Run from repo root:

```bash
pytest
```

Run from `dashboard/`:

```bash
npm run test -- --run
npm run build
```

Expected:

- Existing Python pipeline tests still pass.
- Dashboard tests pass.
- Dashboard build succeeds.

- [ ] **Step 3: Merge/push workflow**

If implementation happened in a worktree/branch:

```bash
git status --short
git log --oneline --decorate -5
```

Then merge or push according to the current GitHub workflow. Do not rewrite unrelated history or revert user changes.

---

## Completion Criteria

The dashboard is complete only when:

- The app runs locally from `dashboard/`.
- The first screen is the analytics dashboard, not a landing page.
- All four views are implemented.
- April reference values are visible in the UI.
- CSV exports work for visible tables/chart-shaped data.
- PNG export captures chart frames reliably.
- Empty/error/source-gap states are implemented.
- Desktop and mobile browser checks pass.
- `pytest`, `npm run test -- --run`, and `npm run build` pass.
- Changes are committed with focused commit messages.
