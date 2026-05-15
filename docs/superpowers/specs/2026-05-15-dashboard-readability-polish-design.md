# Dashboard Readability Polish Design

Date: 2026-05-15

## Context

The static analytics dashboard (`dashboard/`, React + Vite) ships the data correctly but reads like an engineering surface: monospace labels everywhere, jargon terms (`Routing match`, `No-Agent Rate`, `Unaccounted`), queue extensions used as titles, and a permanently-visible debug status strip. Internal analysts read it daily.

This spec is a **surgical readability pass**: keep the existing shell, layout, palette, and topography decisions. Layer in plain-English labels, a top-of-page summary, threshold badges with tooltips, and an in-place funnel restructure. No new tabs, no new dependencies, no extra report fetches.

## Goals

After this work, an internal analyst opening the dashboard for the selected period can answer, without leaving the Overview tab:

1. What was the headline result for the period? (total calls, reach rate, anomaly count)
2. What does every metric mean, in plain English, without asking a teammate?
3. Where is the period in trouble vs healthy — at a glance, not by squinting at border tints?
4. What does the routing funnel actually do to a call?

## Non-Goals

- No deltas or sparklines on metric cards (rejected — would require fetching additional months).
- No new top-level tabs.
- No tab reorganization or "Insights" view.
- No palette overhaul. Editorial green/serif identity stays.
- No backend or report-shape changes.
- No new charting library.

## Audience

Internal NeoLore staff (operations / analysts). They know the terms; the goal is faster scanning and lower onboarding cost, not translation for outsiders. We still favour plain English broadly so the dashboard reads as a product, not a SQL view.

## Approved Approach

Four coordinated changes, all in `dashboard/src`:

1. **Plain-language labels + glossary tooltips.**
2. **Period summary strip** at the top of the Overview view.
3. **Threshold badges + tooltips** on `MetricCard`, with centralized threshold rules.
4. **Polish + funnel redesign in place** (typography, reference chips, status strip behavior, restructured `FunnelChart`).

The four are independent enough to ship sequentially without breaking the dashboard at any commit, and small enough to land in one branch.

## Section 1 — Plain-language Labels & Glossary

### Tab renames (`components/AppShell.tsx`)

- `Per Queue` → `By Queue`
- `Cross Queue` → `Across Queues`
- `Funnel Detail` → `Routing Funnel`
- `Overview` unchanged.

The `ViewKey` type values (`overview`, `per-queue`, `cross-queue`, `funnel-detail`) are unchanged. Only the display labels move.

### Queue identity flip

Today the UI leads with the extension (`8020`) and treats the human name (`CSR English`) as secondary. Flip in:

- `OverviewView` reference row — lead with `CSR English` not `Queue 8020`.
- `QueueCard` — replace the extension chip content with a compact language/role tag (`EN · Pri`, `EN · Ovr`, `FR · Pri`, `FR · Ovr`). Extension stays as a small subtitle under the name.
- `PerQueueView.view-heading` — `{meta.name}` already leads; no change.
- `PerQueueView` segmented queue picker — keep extensions (analysts use them as compact IDs there).
- `CrossQueueView` table column headers — keep extensions (compact table headers).

### Metric / funnel label rewrites

Display strings only; data keys, prop names, and selector field names unchanged.

| Code reference | Current display | New display |
|---|---|---|
| `FunnelChart` rates pill | `Routing 86.5%` | `Right-language routing 86.5%` |
| `FunnelChart` rates pill | `Effective 92.1%` | `Reached an agent 92.1%` |
| `FunnelChart` step | `Primary calls` | `Calls in` |
| `FunnelChart` step | `Primary answered` | `Answered on primary` |
| `FunnelChart` step | `Primary failed` | `Missed on primary` |
| `FunnelChart` step | `Overflow received` | `Sent to overflow` |
| `FunnelChart` step | `Overflow answered` | `Answered on overflow` |
| `FunnelChart` step | `Lost` | `Never connected` |
| `FunnelChart` step | `Unaccounted` | `Untracked` |
| `OverviewView` MetricCard | `English Effective Answer` | `English: reached an agent` |
| `OverviewView` MetricCard | `French Effective Answer` | `French: reached an agent` |
| `PerQueueView` MetricCard | `Total Calls` | `Total calls` |
| `PerQueueView` MetricCard | `Avg Active Day` | `Avg per active day` |
| `PerQueueView` MetricCard | `Busiest Day` | `Busiest day` |
| `PerQueueView` MetricCard | `No-Agent Rate` | `Missed-call rate` |
| `PerQueueView` MetricCard | `Busiest Hour` | `Peak hour` |
| `PerQueueView` MetricCard | `Top Caller` | `Top caller` |
| `QueueCard` dt | `No-agent` | `Missed-call rate` |
| `QueueCard` dt | `Busiest hour` | `Peak hour` |
| `QueueCard` dt | `Top agent` | `Top agent` (unchanged) |

The Section 4 funnel rebuild may collapse some of these step rows (`Primary calls` becomes a hero number, the outcome strip replaces `Lost`/`Unaccounted`). The labels above are still the canonical strings for any place they survive.

### Anomaly kinds

In `OverviewView`, replace `titleCase(anomaly.kind)` with a `humanizeAnomalyKind(kind)` lookup in `utils/format.ts`:

```
volume_spike → "Volume spike"
volume_drop → "Volume drop"
cross_queue_caller → "Caller hit multiple queues"
no_agent_outlier → "Unusual missed-call rate"
routing_mismatch → "Wrong-language routing"
```

Falls back to `titleCase(kind)` for unknown kinds so future server-side anomaly types render gracefully.

### Glossary tooltips

A new `src/data/glossary.ts` exports a single `GLOSSARY: Record<string, string>` map, keyed by metric ID. Initial entries:

- `reached_an_agent`: "Share of calls that reached a live agent on the primary queue or after overflow."
- `right_language_routing`: "Share of calls placed on the queue that matches the caller's spoken language."
- `missed_call_rate`: "Share of calls that ended without ever reaching an agent."
- `untracked`: "Calls present in raw logs but not assignable to a known outcome — usually log gaps."

The glossary is consumed by Section 3's tooltip-enabled `MetricCard` and by the relabeled funnel rates pills (which gain a `?` affordance).

## Section 2 — Period Summary Strip

### Placement

New section inserted between `view-heading` and `funnel-grid` in `OverviewView` only. Other views unchanged.

### Component

New `src/components/PeriodSummary.tsx`. Same surface treatment as `metric-card` (white background, soft shadow, `--border`, `--radius`) so it sits inside the existing visual system. Internally a 4-cell horizontal grid that wraps to 2x2 on narrow widths.

### Cells

1. **Headline.** `{Month YYYY} — {N} calls handled` in display serif. E.g., `April 2026 — 1,620 calls handled`.
2. **Reach rate.** `{NN}% reached an agent` with a Good/Watch/At-risk pill from Section 3's threshold module.
3. **Anomalies.** `{N} anomalies flagged`. If `N > 0`, the cell is a button that scrolls to the existing anomaly strip (add `id="anomaly-strip"` to the strip section and use `scrollIntoView`). If `N === 0`, plain text `No anomalies flagged.`.
4. **Coverage caveat.** `{N} source gap{s}` if `report.source_gaps.length > 0`, otherwise the cell collapses (visibility-only — keeps grid layout). Uses `var(--loss)` text tone.

### Selector

Add `getPeriodSummary(report: DashboardReport): PeriodSummary` to `src/data/selectors.ts`:

```
PeriodSummary {
  periodLabel: string              // "April 2026" from report.date_range.start
  totalCalls: number               // sum over report.queues[*].total_calls
  reachedRate: number              // (Σ primary_answered + Σ overflow_answered) / Σ primary_calls across both languages
  anomalyCount: number             // report.anomalies.length
  sourceGapCount: number           // report.source_gaps.length
}
```

The `reachedRate` weights by total primary calls, not by language average — so a small French queue can't drag the overall rate.

**Denominator note.** `totalCalls` (sum of all four queue `total_calls`, including overflow queues) and `reachedRate` (computed from funnel `primary_calls`) use different denominators by design. For the April fixture: `totalCalls = 1,620` (1,181 + 66 + 343 + 30) and the reach rate's funnel denominator is `1,247` (1,181 English + 66 French primary calls). The "calls handled" headline answers *how much traffic moved through the system*; the reach rate answers *of the calls that entered the primary queues, how many got to an agent (with or without overflow)*. Document this in the `getPeriodSummary` JSDoc.

### Tests

In `src/data/selectors.test.ts`, add a `getPeriodSummary` test against the existing `april-2026-metrics.json` fixture, asserting numeric values reproduce the reference values quoted in the v1 spec (Queue 8020 `1,181`, etc.).

## Section 3 — Threshold Badges + Tooltips on `MetricCard`

### Component changes

`src/components/MetricCard.tsx` gets two new optional props:

```
interface MetricCardProps {
  label: string;
  value: string;
  support?: string;
  status?: "good" | "watch" | "at-risk";   // replaces `tone`
  metricId?: string;                        // when set, ? icon + tooltip on the label
}
```

The existing `tone` prop is removed; all existing call sites in `OverviewView` and `PerQueueView` migrate to `status` in the same commit (no aliasing layer — per project convention against backwards-compat hacks).

Visual: status pill in the top-right of the card. `Good` on green, `Watch` on gold, `At risk` on rust. Pill colors come from new `--badge-good-bg / --badge-good-fg`, `--badge-watch-bg / --badge-watch-fg`, `--badge-risk-bg / --badge-risk-fg` tokens added to `styles/tokens.css`. Card border tint stays — pill is additive, not a replacement.

### Threshold module

New `src/data/thresholds.ts` centralizes the rules:

```
THRESHOLDS = {
  reached_an_agent:        { good: ≥ 0.90, watch: 0.80–0.90, at-risk: < 0.80 },
  missed_call_rate:        { good: ≤ 0.05, watch: 0.05–0.10, at-risk: > 0.10 },
  right_language_routing:  { good: ≥ 0.95, watch: 0.85–0.95, at-risk: < 0.85 },
}

statusFor(metricId, value) → "good" | "watch" | "at-risk" | undefined
```

This promotes the existing `>= 0.85` effective-answer split to a three-band system; 0.85 now lands in "Watch" rather than reading as "Good". Unit tested in `thresholds.test.ts`.

### Tooltip component

New `src/components/Tooltip.tsx`. Minimal, no library:

- Renders a `<button type="button" aria-describedby={id}>` containing the `?` icon (`lucide-react`'s `HelpCircle` at 12px).
- Popover positioned with CSS `position: absolute` above the icon. Single placement — no auto-flip.
- Visible on `:hover` and `:focus-visible` on the trigger button. Escape closes when focused.
- One instance per metric. No global tooltip manager.

`MetricCard` renders the tooltip next to the `eyebrow` label when `metricId` is provided and a matching glossary entry exists.

### Call-site updates

- `OverviewView`: English/French "reached an agent" cards get `metricId="reached_an_agent"` and `status` from `statusFor("reached_an_agent", funnel.effective_answer_rate)`.
- `PerQueueView`: `Missed-call rate` card gets `metricId="missed_call_rate"` and `status` from `statusFor("missed_call_rate", metrics.no_agent_rate)`. Other cards stay statusless.
- `FunnelChart` rates pills (Section 1) gain a `?` icon using the same glossary lookup. They're not `MetricCard`s, so the tooltip is wired directly there.

## Section 4 — Polish + Funnel Redesign

### 4a. Typography

In `styles/app.css`:

- Move from `var(--mono-font)` to `var(--sans-font)`: `.tabs button`, `.segmented-control button`, `.report-controls label`, `.eyebrow`, `.text-button`, `.queue-card dt`, `.metric-card span` (support text).
- Keep `var(--mono-font)` on: `.metric-card strong`, `.queue-card strong`, `.data-table-wrap td/th` (numeric cells), `.funnel-row strong`, `.status-strip`, `.reference-row span` (value line only — see 4b).
- `.metric-card strong`: font-size 28px → 32px; line-height tightened to 1.0.
- `.eyebrow`: `text-transform: uppercase` removed, font-weight 500, letter-spacing 0.

### 4b. Reference chips (`OverviewView` + `CrossQueueView`)

`reference-row > span` becomes a small stacked card:

```
[eyebrow muted sans 11px]
[value mono 14px]
[support muted sans 12px]
```

Implementation: replace the inline `<span>{...}</span>` content with a small structured component (or inline JSX with three children). The chip shape, border, and pill radius stay.

Add `formatPhone(value: string): string` to `utils/format.ts`. Best-effort NANP grouping: `+1XXXXXXXXXX` → `+1 (XXX) XXX-XXXX`. Falls back to the raw string for non-NANP inputs.

The Overview reference row's three chips become (values shown for the April 2026 fixture):

1. Eyebrow `English primary queue` / value `1,181` / support `CSR English · 8020`. (Source: `report.queues["8020"].total_calls`. The chip stays scoped to queue 8020 as it is today.)
2. Eyebrow `Top agent` / value `Gabriel Hubert` / support `299 calls`.
3. Eyebrow `Top caller` / value `+1 (905) 283-3500` / support `63 calls`.

The CrossQueueView reference row gets a similar two-chip treatment for top agent / top caller.

### 4c. Status strip

In `components/AppShell.tsx`, restructure the status strip:

- **Healthy** (`loadResult.status === "loaded"`, no `warning`, `report.source_gaps.length === 0`, `validation.status` in `{"ok", "pending"}`): collapsed to a single muted line: `Loaded · {period label} · Source: {source}`. A small chevron button toggles to the expanded view on demand.
- **Degraded** (any of: `source_gaps.length > 0`, `warning` present, `validation.status === "failed"`): fully expanded by default, with `var(--loss)` tone on the offending field(s).

Default state is collapsed when healthy, expanded when degraded. User can toggle either way.

### 4d. Funnel chart redesign (in place)

Rebuild `charts/FunnelChart.tsx` to a layered structure instead of seven equal bars. Same props, same data, same `aria-label`, same export filename.

New layout, top to bottom:

1. **Hero row.** `Calls in` (sans, 11px, muted eyebrow) above `{primary_calls}` in display serif at 28px. Replaces today's `Primary calls` row.
2. **Rates pills row** (relabeled in Section 1) — moves immediately under the hero. `Right-language routing X%` and `Reached an agent Y%` each with `?` tooltip.
3. **Primary leg bar.** Single horizontal track split into two segments:
   - `Answered on primary` ({primary_answered}) in the primary queue color.
   - `Sent to overflow` ({overflow_received}) in the overflow queue color.
   Each segment's width is proportional to its share of `primary_calls`. Tooltips on each segment show absolute counts. A small caption line beneath: `{primary_answered} answered · {overflow_received} sent to overflow`.
4. **Overflow detail bar.** Shown when `overflow_received > 0`. Indented 16px, with a 1px left connector to suggest hierarchy. Split into:
   - `Answered on overflow` ({overflow_answered}) in the overflow queue color.
   - `Missed on overflow` ({overflow_received - overflow_answered}) in `var(--loss)`.
5. **Outcome strip.** Three small chips at the bottom:
   - `Reached someone: {primary_answered + overflow_answered} ({reached_rate}%)` — neutral.
   - `Never connected: {lost}` — `var(--loss)` tone.
   - `Untracked: {unaccounted}` — `var(--gold)` tone. Hidden when `unaccounted === 0` (today it shows even when zero).

The component still respects the `chart-body--scrollable` toggle. The PNG export filename (`{language}-funnel.png`) is unchanged.

### Tests

- Update `FunnelChart` tests (if present) to assert new structural elements: hero number, rates pills, primary leg segments, overflow detail bar visibility, outcome chip visibility.
- Add a snapshot or DOM test for the period summary strip on `OverviewView`.
- Add unit tests for `statusFor`, `humanizeAnomalyKind`, `formatPhone`.

## Files Touched

New:

- `src/components/PeriodSummary.tsx`
- `src/components/Tooltip.tsx`
- `src/data/glossary.ts`
- `src/data/thresholds.ts`
- `src/data/thresholds.test.ts`

Modified:

- `src/App.tsx` — no changes expected (renders subviews unchanged).
- `src/components/AppShell.tsx` — tab labels, status strip behavior.
- `src/components/MetricCard.tsx` — `status`/`metricId` props.
- `src/components/QueueCard.tsx` — language/role chip, label rewrites.
- `src/charts/FunnelChart.tsx` — full visual rebuild.
- `src/views/OverviewView.tsx` — insert `PeriodSummary`, restructure reference row, migrate metric cards.
- `src/views/PerQueueView.tsx` — migrate metric cards to `status`/`metricId`, label rewrites.
- `src/views/CrossQueueView.tsx` — restructure reference row.
- `src/data/selectors.ts` — add `getPeriodSummary`.
- `src/data/selectors.test.ts` — add `getPeriodSummary` tests.
- `src/utils/format.ts` — add `formatPhone`, `humanizeAnomalyKind`.
- `src/styles/app.css` — typography updates, status strip toggle, reference chip layout, funnel chart layout.
- `src/styles/tokens.css` — `--badge-*` trio.

## Validation

After implementation, pointed at `month_2026-04-01_2026-04-30`:

- Period summary renders `April 2026 — 1,620 calls handled` (1181 + 66 + 343 + 30). The reach-rate cell shows the funnel-weighted value (≈84% on the April fixture; recompute exactly during implementation).
- English "reached an agent" card shows `84.7%` with `Watch` pill (per new 0.80–0.90 band).
- French "reached an agent" card shows `87.9%` with `Watch` pill.
- Funnel chart hero shows `Calls in: 1,181` for the English language (matches `report.crossqueue.funnels.English.primary_calls`).
- Anomaly count on the period summary matches `report.anomalies.length` (the April fixture shows 15).
- Tab labels read `Overview · By Queue · Across Queues · Routing Funnel`.
- Healthy status strip collapses to one line. Forcing a fallback (e.g., loading a missing report path) expands the strip and tints the warning.
- Glossary `?` icons on the four labeled metrics show a definition popover on hover and focus.

## Rollout

Single branch, single PR. No feature flag — the change is purely cosmetic / surface-level and ships atomically. Reviewers can validate against the April fixture and the existing test suite.
