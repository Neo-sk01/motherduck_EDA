# Dashboard Readability Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the static analytics dashboard read like a product for internal analysts — plain-English labels, top-of-page summary, threshold badges with tooltips, restructured funnel chart — without changing the data layer or shell architecture.

**Architecture:** Surgical pass on `dashboard/` (React 19 + Vite + TypeScript). Add small pure modules (`thresholds.ts`, `glossary.ts`, format helpers, `getPeriodSummary` selector). Build a tiny `Tooltip` primitive and a new `PeriodSummary` component. Migrate `MetricCard` to a `status`/`metricId` API. Rewrite display strings across views. Restructure `FunnelChart` in place. Tighten typography and the status strip in `app.css`. No new dependencies, no extra report fetches.

**Tech Stack:** React 19, TypeScript, Vite, Vitest + React Testing Library + jsdom, lucide-react icons (already in deps), CSS variables in `styles/tokens.css` and `styles/app.css`.

**Spec:** `docs/superpowers/specs/2026-05-15-dashboard-readability-polish-design.md`.

**Working directory for all commands:** `dashboard/` (i.e. `/Users/neosekaleli/Desktop/Developer/MOTHERDUCK-EDA-CSH/dashboard/`).

---

## Task 1: Threshold module

**Files:**
- Create: `dashboard/src/data/thresholds.ts`
- Test: `dashboard/src/data/thresholds.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `dashboard/src/data/thresholds.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { statusFor } from "./thresholds";

describe("statusFor", () => {
  it("returns good for reached_an_agent at or above 0.90", () => {
    expect(statusFor("reached_an_agent", 0.95)).toBe("good");
    expect(statusFor("reached_an_agent", 0.9)).toBe("good");
  });

  it("returns watch for reached_an_agent in the 0.80–0.90 band", () => {
    expect(statusFor("reached_an_agent", 0.85)).toBe("watch");
    expect(statusFor("reached_an_agent", 0.8)).toBe("watch");
  });

  it("returns at-risk for reached_an_agent below 0.80", () => {
    expect(statusFor("reached_an_agent", 0.79)).toBe("at-risk");
  });

  it("returns good for missed_call_rate at or below 0.05", () => {
    expect(statusFor("missed_call_rate", 0.05)).toBe("good");
    expect(statusFor("missed_call_rate", 0.02)).toBe("good");
  });

  it("returns watch for missed_call_rate between 0.05 and 0.10", () => {
    expect(statusFor("missed_call_rate", 0.08)).toBe("watch");
  });

  it("returns at-risk for missed_call_rate above 0.10", () => {
    expect(statusFor("missed_call_rate", 0.12)).toBe("at-risk");
  });

  it("returns good for right_language_routing at or above 0.95", () => {
    expect(statusFor("right_language_routing", 0.97)).toBe("good");
  });

  it("returns watch for right_language_routing between 0.85 and 0.95", () => {
    expect(statusFor("right_language_routing", 0.9)).toBe("watch");
  });

  it("returns at-risk for right_language_routing below 0.85", () => {
    expect(statusFor("right_language_routing", 0.8)).toBe("at-risk");
  });

  it("returns undefined for unknown metric ids", () => {
    expect(statusFor("unknown_metric", 0.5)).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- thresholds`
Expected: FAIL with "Cannot find module './thresholds'".

- [ ] **Step 3: Implement the module**

Create `dashboard/src/data/thresholds.ts`:

```ts
export type MetricStatus = "good" | "watch" | "at-risk";

export type ThresholdMetricId =
  | "reached_an_agent"
  | "missed_call_rate"
  | "right_language_routing";

interface HigherIsBetter {
  direction: "higher-is-better";
  good: number;
  watch: number;
}

interface LowerIsBetter {
  direction: "lower-is-better";
  good: number;
  watch: number;
}

type ThresholdRule = HigherIsBetter | LowerIsBetter;

const THRESHOLDS: Record<ThresholdMetricId, ThresholdRule> = {
  reached_an_agent: { direction: "higher-is-better", good: 0.9, watch: 0.8 },
  missed_call_rate: { direction: "lower-is-better", good: 0.05, watch: 0.1 },
  right_language_routing: { direction: "higher-is-better", good: 0.95, watch: 0.85 },
};

export function statusFor(metricId: string, value: number): MetricStatus | undefined {
  const rule = THRESHOLDS[metricId as ThresholdMetricId];
  if (!rule) return undefined;
  if (rule.direction === "higher-is-better") {
    if (value >= rule.good) return "good";
    if (value >= rule.watch) return "watch";
    return "at-risk";
  }
  if (value <= rule.good) return "good";
  if (value <= rule.watch) return "watch";
  return "at-risk";
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- thresholds`
Expected: PASS, 10 tests.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/data/thresholds.ts dashboard/src/data/thresholds.test.ts
git commit -m "feat(dashboard): add threshold module with three-band metric status"
```

---

## Task 2: Glossary module

**Files:**
- Create: `dashboard/src/data/glossary.ts`

No tests required — pure data map, exercised through component tests later.

- [ ] **Step 1: Create the glossary file**

Create `dashboard/src/data/glossary.ts`:

```ts
export const GLOSSARY: Record<string, string> = {
  reached_an_agent:
    "Share of calls that reached a live agent on the primary queue or after overflow.",
  right_language_routing:
    "Share of calls placed on the queue that matches the caller's spoken language.",
  missed_call_rate:
    "Share of calls that ended without ever reaching an agent.",
  untracked:
    "Calls present in raw logs but not assignable to a known outcome — usually log gaps.",
};

export function getGlossaryEntry(metricId: string | undefined): string | undefined {
  if (!metricId) return undefined;
  return GLOSSARY[metricId];
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/data/glossary.ts
git commit -m "feat(dashboard): add glossary map for tooltip definitions"
```

---

## Task 3: Format helpers (`formatPhone`, `humanizeAnomalyKind`)

**Files:**
- Modify: `dashboard/src/utils/format.ts`
- Test: `dashboard/src/utils/format.test.ts` (new file)

- [ ] **Step 1: Write the failing tests**

Create `dashboard/src/utils/format.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { formatPhone, humanizeAnomalyKind } from "./format";

describe("formatPhone", () => {
  it("formats a NANP number with leading +1", () => {
    expect(formatPhone("+19052833500")).toBe("+1 (905) 283-3500");
  });

  it("formats a 10-digit NANP number without country code", () => {
    expect(formatPhone("9052833500")).toBe("+1 (905) 283-3500");
  });

  it("returns the raw value for non-NANP input", () => {
    expect(formatPhone("442012345678")).toBe("442012345678");
    expect(formatPhone("")).toBe("");
    expect(formatPhone("anonymous")).toBe("anonymous");
  });
});

describe("humanizeAnomalyKind", () => {
  it("maps known anomaly kinds to plain sentences", () => {
    expect(humanizeAnomalyKind("volume_spike")).toBe("Volume spike");
    expect(humanizeAnomalyKind("volume_drop")).toBe("Volume drop");
    expect(humanizeAnomalyKind("cross_queue_caller")).toBe("Caller hit multiple queues");
    expect(humanizeAnomalyKind("no_agent_outlier")).toBe("Unusual missed-call rate");
    expect(humanizeAnomalyKind("routing_mismatch")).toBe("Wrong-language routing");
  });

  it("falls back to title-cased text for unknown kinds", () => {
    expect(humanizeAnomalyKind("some_new_kind")).toBe("Some New Kind");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- utils/format`
Expected: FAIL with import errors for `formatPhone` and `humanizeAnomalyKind`.

- [ ] **Step 3: Add the helpers to `format.ts`**

Append to `dashboard/src/utils/format.ts`:

```ts
export function formatPhone(value: string): string {
  if (!value) return value;
  const digits = value.replace(/[^\d]/g, "");
  if (digits.length === 11 && digits.startsWith("1")) {
    return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }
  if (digits.length === 10) {
    return `+1 (${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  return value;
}

const ANOMALY_KIND_LABELS: Record<string, string> = {
  volume_spike: "Volume spike",
  volume_drop: "Volume drop",
  cross_queue_caller: "Caller hit multiple queues",
  no_agent_outlier: "Unusual missed-call rate",
  routing_mismatch: "Wrong-language routing",
};

export function humanizeAnomalyKind(kind: string): string {
  return ANOMALY_KIND_LABELS[kind] ?? titleCase(kind);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- utils/format`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/utils/format.ts dashboard/src/utils/format.test.ts
git commit -m "feat(dashboard): add formatPhone and humanizeAnomalyKind helpers"
```

---

## Task 4: `getPeriodSummary` selector

**Files:**
- Modify: `dashboard/src/data/selectors.ts`
- Modify: `dashboard/src/data/selectors.test.ts`

- [ ] **Step 1: Write the failing test**

Append to `dashboard/src/data/selectors.test.ts`:

```ts
import { getPeriodSummary } from "./selectors";

describe("getPeriodSummary", () => {
  it("computes the headline summary from the April fixture", () => {
    const summary = getPeriodSummary(report);
    expect(summary).toEqual({
      periodLabel: "April 2026",
      totalCalls: 1620,
      reachedRate: expect.closeTo(0.84, 2),
      anomalyCount: report.anomalies.length,
      sourceGapCount: 0,
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- selectors`
Expected: FAIL with `getPeriodSummary is not a function` (or import error).

- [ ] **Step 3: Add the selector to `selectors.ts`**

Add to `dashboard/src/data/selectors.ts`:

```ts
export interface PeriodSummary {
  periodLabel: string;
  totalCalls: number;
  reachedRate: number;
  anomalyCount: number;
  sourceGapCount: number;
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

/**
 * Headline summary for the Overview view.
 *
 * Note: `totalCalls` sums every queue's `total_calls` (including overflow queues),
 * while `reachedRate` is computed from funnel `primary_calls`. These intentionally
 * use different denominators — `totalCalls` answers "how much traffic moved through
 * the system", and `reachedRate` answers "of calls into the primary queues, how
 * many reached an agent."
 */
export function getPeriodSummary(report: DashboardReport): PeriodSummary {
  const [year, month] = report.date_range.start.split("-").map(Number);
  const periodLabel = `${MONTH_NAMES[month - 1]} ${year}`;

  const totalCalls = Object.values(report.queues).reduce(
    (sum, queue) => sum + (queue.total_calls ?? 0),
    0,
  );

  const funnels = Object.values(report.crossqueue.funnels);
  const primary = funnels.reduce((sum, f) => sum + (f.primary_calls ?? 0), 0);
  const answered = funnels.reduce(
    (sum, f) => sum + (f.primary_answered ?? 0) + (f.overflow_answered ?? 0),
    0,
  );
  const reachedRate = primary > 0 ? answered / primary : 0;

  return {
    periodLabel,
    totalCalls,
    reachedRate,
    anomalyCount: report.anomalies.length,
    sourceGapCount: report.source_gaps.length,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- selectors`
Expected: PASS, including new `getPeriodSummary` test.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/data/selectors.ts dashboard/src/data/selectors.test.ts
git commit -m "feat(dashboard): add getPeriodSummary selector for headline strip"
```

---

## Task 5: Badge color tokens

**Files:**
- Modify: `dashboard/src/styles/tokens.css`

- [ ] **Step 1: Add the badge tokens**

In `dashboard/src/styles/tokens.css`, inside the `:root` block (before the closing brace), add:

```css
  --badge-good-bg: #e2f1e1;
  --badge-good-fg: #1f5e2e;
  --badge-watch-bg: #f6efd5;
  --badge-watch-fg: #6b5a18;
  --badge-risk-bg: #f7dcdc;
  --badge-risk-fg: #8f2f2f;
```

- [ ] **Step 2: Verify the file still parses (no test exists for tokens)**

Run: `npm run build`
Expected: SUCCESS (build runs `tsc -b && vite build`). If vite build fails on CSS parse, fix and retry.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/styles/tokens.css
git commit -m "feat(dashboard): add badge color tokens for metric status pills"
```

---

## Task 6: `Tooltip` primitive

**Files:**
- Create: `dashboard/src/components/Tooltip.tsx`
- Test: `dashboard/src/components/Tooltip.test.tsx`
- Modify: `dashboard/src/styles/app.css`

- [ ] **Step 1: Write the failing test**

Create `dashboard/src/components/Tooltip.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Tooltip } from "./Tooltip";

describe("Tooltip", () => {
  it("renders a trigger button with aria-describedby pointing at the popover", () => {
    render(<Tooltip id="t1" label="What is this?" content="A definition." />);
    const trigger = screen.getByRole("button", { name: "What is this?" });
    expect(trigger).toHaveAttribute("aria-describedby", "t1");
  });

  it("reveals the popover on hover and hides on mouse leave", async () => {
    const user = userEvent.setup();
    render(<Tooltip id="t2" label="Why" content="Because." />);
    expect(screen.queryByText("Because.")).not.toBeInTheDocument();

    await user.hover(screen.getByRole("button", { name: "Why" }));
    expect(screen.getByText("Because.")).toBeInTheDocument();

    await user.unhover(screen.getByRole("button", { name: "Why" }));
    expect(screen.queryByText("Because.")).not.toBeInTheDocument();
  });

  it("reveals the popover on focus and hides on blur", async () => {
    const user = userEvent.setup();
    render(<Tooltip id="t3" label="Why" content="Because." />);
    await user.tab();
    expect(screen.getByText("Because.")).toBeInTheDocument();

    await user.tab();
    expect(screen.queryByText("Because.")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- Tooltip`
Expected: FAIL with module-not-found.

- [ ] **Step 3: Implement the component**

Create `dashboard/src/components/Tooltip.tsx`:

```tsx
import { HelpCircle } from "lucide-react";
import { useState } from "react";

interface TooltipProps {
  id: string;
  label: string;
  content: string;
}

export function Tooltip({ id, label, content }: TooltipProps) {
  const [open, setOpen] = useState(false);

  return (
    <span className="tooltip-host">
      <button
        type="button"
        className="tooltip-trigger"
        aria-label={label}
        aria-describedby={id}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false);
        }}
      >
        <HelpCircle aria-hidden="true" size={12} />
      </button>
      {open ? (
        <span role="tooltip" id={id} className="tooltip-popover">
          {content}
        </span>
      ) : null}
    </span>
  );
}
```

- [ ] **Step 4: Add CSS for the tooltip**

Append to `dashboard/src/styles/app.css`:

```css
.tooltip-host {
  position: relative;
  display: inline-flex;
  align-items: center;
  margin-left: 4px;
}

.tooltip-trigger {
  display: inline-grid;
  place-items: center;
  width: 14px;
  height: 14px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--muted);
  padding: 0;
}

.tooltip-trigger:hover,
.tooltip-trigger:focus-visible {
  color: var(--text);
  outline: none;
}

.tooltip-popover {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  width: max-content;
  max-width: 240px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #1c211e;
  color: #f3f6f1;
  font-family: var(--sans-font);
  font-size: 12px;
  line-height: 1.4;
  box-shadow: 0 8px 22px rgba(20, 25, 22, 0.25);
  pointer-events: none;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -- Tooltip`
Expected: PASS, 3 tests.

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/components/Tooltip.tsx dashboard/src/components/Tooltip.test.tsx dashboard/src/styles/app.css
git commit -m "feat(dashboard): add Tooltip primitive for glossary affordance"
```

---

## Task 7: Migrate `MetricCard` to `status` + `metricId` API

This task is atomic — it changes `MetricCard`'s props and updates every call site in one commit so the build never breaks mid-migration. There are five call sites: `OverviewView`, `PerQueueView`, `FunnelDetailView` (multiple).

**Files:**
- Modify: `dashboard/src/components/MetricCard.tsx`
- Modify: `dashboard/src/views/OverviewView.tsx`
- Modify: `dashboard/src/views/PerQueueView.tsx`
- Modify: `dashboard/src/views/FunnelDetailView.tsx`
- Modify: `dashboard/src/styles/app.css`
- Test: `dashboard/src/components/MetricCard.test.tsx` (new)

- [ ] **Step 1: Write the failing test**

Create `dashboard/src/components/MetricCard.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MetricCard } from "./MetricCard";

describe("MetricCard", () => {
  it("renders label, value, and support", () => {
    render(<MetricCard label="Reached an agent" value="92.1%" support="1,048 of 1,247" />);
    expect(screen.getByText("Reached an agent")).toBeInTheDocument();
    expect(screen.getByText("92.1%")).toBeInTheDocument();
    expect(screen.getByText("1,048 of 1,247")).toBeInTheDocument();
  });

  it("shows a Good pill when status is good", () => {
    render(<MetricCard label="Reached an agent" value="92%" status="good" />);
    expect(screen.getByText("Good")).toBeInTheDocument();
  });

  it("shows a Watch pill when status is watch", () => {
    render(<MetricCard label="Reached an agent" value="84%" status="watch" />);
    expect(screen.getByText("Watch")).toBeInTheDocument();
  });

  it("shows an At risk pill when status is at-risk", () => {
    render(<MetricCard label="Reached an agent" value="70%" status="at-risk" />);
    expect(screen.getByText("At risk")).toBeInTheDocument();
  });

  it("renders a tooltip trigger when metricId resolves in the glossary", () => {
    render(<MetricCard label="Reached an agent" value="92%" metricId="reached_an_agent" />);
    expect(screen.getByRole("button", { name: /reached an agent/i })).toBeInTheDocument();
  });

  it("does not render a tooltip trigger for unknown metric ids", () => {
    render(<MetricCard label="Foo" value="1" metricId="unknown_metric" />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- MetricCard`
Expected: FAIL — the current `MetricCard` doesn't render pills or tooltips and uses `tone`.

- [ ] **Step 3: Rewrite `MetricCard.tsx`**

Replace `dashboard/src/components/MetricCard.tsx` with:

```tsx
import { Tooltip } from "./Tooltip";
import { getGlossaryEntry } from "../data/glossary";
import type { MetricStatus } from "../data/thresholds";

interface MetricCardProps {
  label: string;
  value: string;
  support?: string;
  status?: MetricStatus;
  metricId?: string;
}

const STATUS_LABELS: Record<MetricStatus, string> = {
  good: "Good",
  watch: "Watch",
  "at-risk": "At risk",
};

export function MetricCard({ label, value, support, status, metricId }: MetricCardProps) {
  const glossaryEntry = getGlossaryEntry(metricId);
  const toneClass = status ? `metric-card--${status}` : "metric-card--neutral";

  return (
    <article className={`metric-card ${toneClass}`}>
      <div className="metric-card__head">
        <p className="eyebrow">
          {label}
          {glossaryEntry && metricId ? (
            <Tooltip id={`${metricId}-tip`} label={label} content={glossaryEntry} />
          ) : null}
        </p>
        {status ? (
          <span className={`metric-status-pill metric-status-pill--${status}`}>
            {STATUS_LABELS[status]}
          </span>
        ) : null}
      </div>
      <strong>{value}</strong>
      {support ? <span>{support}</span> : null}
    </article>
  );
}
```

- [ ] **Step 4: Add the new layout + pill CSS**

Append to `dashboard/src/styles/app.css`:

```css
.metric-card__head {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 8px;
}

.metric-card .eyebrow {
  display: inline-flex;
  align-items: center;
}

.metric-status-pill {
  flex: 0 0 auto;
  padding: 2px 8px;
  border-radius: 999px;
  font-family: var(--sans-font);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.01em;
  white-space: nowrap;
}

.metric-status-pill--good {
  background: var(--badge-good-bg);
  color: var(--badge-good-fg);
}

.metric-status-pill--watch {
  background: var(--badge-watch-bg);
  color: var(--badge-watch-fg);
}

.metric-status-pill--at-risk {
  background: var(--badge-risk-bg);
  color: var(--badge-risk-fg);
}

.metric-card--at-risk {
  border-color: rgba(163, 45, 45, 0.35);
}

.metric-card--watch {
  border-color: rgba(180, 145, 30, 0.35);
}

.metric-card--good {
  border-color: rgba(47, 122, 63, 0.42);
}
```

Then **remove** the now-stale rules `.metric-card--good` and `.metric-card--risk` from earlier in the file (search for the old block at roughly lines 297–303). The new rules above replace them; `metric-card--risk` is dead.

- [ ] **Step 5: Migrate `OverviewView.tsx` call sites**

In `dashboard/src/views/OverviewView.tsx`, in the `metric-grid` section that maps over `funnels`, replace each `MetricCard` props block with:

```tsx
<MetricCard
  key={item.language}
  label={`${item.language}: reached an agent`}
  value={formatPercent(item.funnel.effective_answer_rate)}
  support={`${formatInteger(item.funnel.primary_calls - item.funnel.lost)} reached before final loss; ${formatInteger(item.funnel.lost)} lost`}
  metricId="reached_an_agent"
  status={statusFor("reached_an_agent", item.funnel.effective_answer_rate)}
/>
```

Add the import at the top:

```tsx
import { statusFor } from "../data/thresholds";
```

- [ ] **Step 6: Migrate `PerQueueView.tsx` call sites**

In `dashboard/src/views/PerQueueView.tsx`, update the six metric cards to:

```tsx
<MetricCard label="Total calls" value={formatInteger(metrics.total_calls)} />
<MetricCard label="Avg per active day" value={formatDecimal(metrics.avg_calls_per_active_day)} />
<MetricCard
  label="Busiest day"
  value={metrics.busiest_day ? formatInteger(metrics.busiest_day.calls) : "0"}
  support={metrics.busiest_day?.date}
/>
<MetricCard
  label="Missed-call rate"
  value={formatPercent(metrics.no_agent_rate)}
  metricId="missed_call_rate"
  status={statusFor("missed_call_rate", metrics.no_agent_rate)}
/>
<MetricCard
  label="Peak hour"
  value={formatHour(busiestHour)}
  support={topAgent ? `Top agent ${topAgent.agent_name}` : "No handled calls"}
/>
<MetricCard
  label="Top caller"
  value={topCaller?.caller_number_norm ?? "n/a"}
  support={topCaller ? `${formatInteger(topCaller.calls)} calls` : undefined}
/>
```

Add the import:

```tsx
import { statusFor } from "../data/thresholds";
```

- [ ] **Step 7: Migrate `FunnelDetailView.tsx` call sites**

In `dashboard/src/views/FunnelDetailView.tsx`, replace the nine metric cards with:

```tsx
<MetricCard label="Calls in" value={formatInteger(item.funnel.primary_calls)} />
<MetricCard label="Answered on primary" value={formatInteger(item.funnel.primary_answered)} status="good" />
<MetricCard label="Missed on primary" value={formatInteger(item.funnel.primary_failed)} status="at-risk" />
<MetricCard label="Sent to overflow" value={formatInteger(item.funnel.overflow_received)} />
<MetricCard label="Answered on overflow" value={formatInteger(item.funnel.overflow_answered)} status="good" />
<MetricCard label="Never connected" value={formatInteger(item.funnel.lost)} status="at-risk" />
<MetricCard label="Untracked" value={formatInteger(item.funnel.unaccounted)} metricId="untracked" />
<MetricCard
  label="Right-language routing"
  value={formatPercent(item.funnel.routing_match)}
  metricId="right_language_routing"
  status={statusFor("right_language_routing", item.funnel.routing_match)}
/>
<MetricCard
  label="Reached an agent"
  value={formatPercent(item.funnel.effective_answer_rate)}
  metricId="reached_an_agent"
  status={statusFor("reached_an_agent", item.funnel.effective_answer_rate)}
/>
```

Add the import:

```tsx
import { statusFor } from "../data/thresholds";
```

- [ ] **Step 8: Run tests to verify everything still passes**

Run: `npm test`
Expected: All MetricCard tests pass. `App.test.tsx` may still pass since label assertions in those tests check funnel chart step rows (which we haven't touched yet) and queue card data, not metric-card labels directly. If `App.test.tsx` fails because of `tone` references in the existing test, those should not exist — verify with `grep -n "tone" dashboard/src/App.test.tsx`. (Expected: no matches.)

If `App.test.tsx` tests assert on "English Effective Answer" labels — they don't (verified during planning). Move on.

- [ ] **Step 9: Run a typecheck**

Run: `npx tsc -b`
Expected: PASS. If FAIL on `tone` references, search the codebase: `grep -rn "tone=" dashboard/src --include="*.tsx"` and remove any remaining references.

- [ ] **Step 10: Commit**

```bash
git add dashboard/src/components/MetricCard.tsx dashboard/src/components/MetricCard.test.tsx dashboard/src/views/OverviewView.tsx dashboard/src/views/PerQueueView.tsx dashboard/src/views/FunnelDetailView.tsx dashboard/src/styles/app.css
git commit -m "feat(dashboard): migrate MetricCard to status/metricId API with badges and tooltips"
```

---

## Task 8: `PeriodSummary` component

**Files:**
- Create: `dashboard/src/components/PeriodSummary.tsx`
- Test: `dashboard/src/components/PeriodSummary.test.tsx`
- Modify: `dashboard/src/styles/app.css`

- [ ] **Step 1: Write the failing test**

Create `dashboard/src/components/PeriodSummary.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PeriodSummary } from "./PeriodSummary";

const baseSummary = {
  periodLabel: "April 2026",
  totalCalls: 1620,
  reachedRate: 0.84,
  anomalyCount: 15,
  sourceGapCount: 0,
};

describe("PeriodSummary", () => {
  it("renders the headline, reach rate, and anomaly count", () => {
    render(<PeriodSummary summary={baseSummary} onAnomaliesClick={() => undefined} />);
    expect(screen.getByText(/April 2026/)).toBeInTheDocument();
    expect(screen.getByText(/1,620 calls handled/)).toBeInTheDocument();
    expect(screen.getByText(/84.0% reached an agent/)).toBeInTheDocument();
    expect(screen.getByText(/15 anomalies flagged/)).toBeInTheDocument();
  });

  it("hides the source-gap cell when there are no gaps", () => {
    render(<PeriodSummary summary={baseSummary} onAnomaliesClick={() => undefined} />);
    expect(screen.queryByText(/source gap/i)).not.toBeInTheDocument();
  });

  it("shows the source-gap cell with loss tone when gaps exist", () => {
    render(
      <PeriodSummary
        summary={{ ...baseSummary, sourceGapCount: 2 }}
        onAnomaliesClick={() => undefined}
      />,
    );
    expect(screen.getByText(/2 source gaps/)).toBeInTheDocument();
  });

  it("renders 'No anomalies flagged.' as plain text when count is zero", () => {
    render(
      <PeriodSummary
        summary={{ ...baseSummary, anomalyCount: 0 }}
        onAnomaliesClick={() => undefined}
      />,
    );
    expect(screen.getByText("No anomalies flagged.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /anomal/i })).not.toBeInTheDocument();
  });

  it("calls onAnomaliesClick when the anomaly cell is clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<PeriodSummary summary={baseSummary} onAnomaliesClick={onClick} />);
    await user.click(screen.getByRole("button", { name: /anomalies flagged/i }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- PeriodSummary`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the component**

Create `dashboard/src/components/PeriodSummary.tsx`:

```tsx
import { statusFor } from "../data/thresholds";
import type { PeriodSummary as PeriodSummaryData } from "../data/selectors";
import { formatInteger, formatPercent } from "../utils/format";

interface PeriodSummaryProps {
  summary: PeriodSummaryData;
  onAnomaliesClick: () => void;
}

export function PeriodSummary({ summary, onAnomaliesClick }: PeriodSummaryProps) {
  const reachStatus = statusFor("reached_an_agent", summary.reachedRate);
  const reachStatusLabel =
    reachStatus === "good" ? "Good" : reachStatus === "watch" ? "Watch" : reachStatus === "at-risk" ? "At risk" : null;

  return (
    <article className="period-summary">
      <div className="period-summary__headline">
        <p className="eyebrow">{summary.periodLabel}</p>
        <strong>{formatInteger(summary.totalCalls)} calls handled</strong>
      </div>

      <div className="period-summary__cell">
        <p className="eyebrow">Reach rate</p>
        <strong>{formatPercent(summary.reachedRate)} reached an agent</strong>
        {reachStatusLabel ? (
          <span className={`metric-status-pill metric-status-pill--${reachStatus}`}>
            {reachStatusLabel}
          </span>
        ) : null}
      </div>

      <div className="period-summary__cell">
        <p className="eyebrow">Anomalies</p>
        {summary.anomalyCount > 0 ? (
          <button
            type="button"
            className="period-summary__anomalies"
            onClick={onAnomaliesClick}
          >
            {formatInteger(summary.anomalyCount)} anomalies flagged
          </button>
        ) : (
          <span>No anomalies flagged.</span>
        )}
      </div>

      {summary.sourceGapCount > 0 ? (
        <div className="period-summary__cell period-summary__cell--warning">
          <p className="eyebrow">Coverage</p>
          <strong>
            {formatInteger(summary.sourceGapCount)} source gap
            {summary.sourceGapCount === 1 ? "" : "s"}
          </strong>
        </div>
      ) : null}
    </article>
  );
}
```

- [ ] **Step 4: Add styles**

Append to `dashboard/src/styles/app.css`:

```css
.period-summary {
  display: grid;
  grid-template-columns: minmax(220px, 1.4fr) repeat(3, minmax(160px, 1fr));
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow);
}

.period-summary__headline strong {
  display: block;
  margin-top: 4px;
  font-family: var(--display-font);
  font-size: 22px;
  line-height: 1.1;
}

.period-summary__cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.period-summary__cell strong {
  font-family: var(--sans-font);
  font-size: 15px;
  font-weight: 600;
}

.period-summary__cell--warning strong {
  color: var(--loss);
}

.period-summary__anomalies {
  border: 0;
  background: transparent;
  padding: 0;
  font: inherit;
  text-align: left;
  color: var(--text);
  text-decoration: underline dotted;
  text-underline-offset: 2px;
}

@media (max-width: 720px) {
  .period-summary {
    grid-template-columns: 1fr 1fr;
  }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -- PeriodSummary`
Expected: PASS, 5 tests.

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/components/PeriodSummary.tsx dashboard/src/components/PeriodSummary.test.tsx dashboard/src/styles/app.css
git commit -m "feat(dashboard): add PeriodSummary component"
```

---

## Task 9: Wire `PeriodSummary` into `OverviewView`

**Files:**
- Modify: `dashboard/src/views/OverviewView.tsx`

- [ ] **Step 1: Add the strip**

In `dashboard/src/views/OverviewView.tsx`:

1. Add imports at the top:
   ```tsx
   import { useRef } from "react";
   import { PeriodSummary } from "../components/PeriodSummary";
   import { getPeriodSummary } from "../data/selectors";
   ```
   (Keep the existing `useState` import; combine: `import { useRef, useState } from "react";`.)

2. Inside `OverviewView`, after the existing `const summaries = …` line, add:
   ```tsx
   const periodSummary = getPeriodSummary(report);
   const anomalyStripRef = useRef<HTMLElement>(null);
   ```

3. Insert the `PeriodSummary` element between the `view-heading` section and the `funnel-grid` section:
   ```tsx
   <PeriodSummary
     summary={periodSummary}
     onAnomaliesClick={() =>
       anomalyStripRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
     }
   />
   ```

4. Attach the ref to the existing `anomaly-strip` section element:
   ```tsx
   <section className="anomaly-strip" aria-label="Anomalies" ref={anomalyStripRef}>
   ```

- [ ] **Step 2: Verify the build typechecks**

Run: `npx tsc -b`
Expected: PASS.

- [ ] **Step 3: Run the test suite**

Run: `npm test`
Expected: PASS. The Overview view now renders the strip but no existing assertion is invalidated.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/views/OverviewView.tsx
git commit -m "feat(dashboard): show PeriodSummary on overview view"
```

---

## Task 10: Tab label rename

This task is atomic — rename the four tab labels in one commit and update the existing `App.test.tsx` assertions in the same commit.

**Files:**
- Modify: `dashboard/src/components/AppShell.tsx`
- Modify: `dashboard/src/App.test.tsx`

- [ ] **Step 1: Update the VIEWS labels**

In `dashboard/src/components/AppShell.tsx`, replace:

```tsx
export const VIEWS: Array<{ key: ViewKey; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "per-queue", label: "Per Queue" },
  { key: "cross-queue", label: "Cross Queue" },
  { key: "funnel-detail", label: "Funnel Detail" },
];
```

with:

```tsx
export const VIEWS: Array<{ key: ViewKey; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "per-queue", label: "By Queue" },
  { key: "cross-queue", label: "Across Queues" },
  { key: "funnel-detail", label: "Routing Funnel" },
];
```

- [ ] **Step 2: Update `FunnelDetailView` heading**

In `dashboard/src/views/FunnelDetailView.tsx`, replace:

```tsx
<h2>Funnel Detail</h2>
```

with:

```tsx
<h2>Routing Funnel</h2>
```

- [ ] **Step 3: Update `App.test.tsx` assertions**

In `dashboard/src/App.test.tsx`, update the affected assertions (the exact line numbers may shift):

```tsx
// Line ~26-28 — first test:
expect(screen.getByRole("button", { name: "Overview" })).toBeInTheDocument();
expect(screen.getByRole("button", { name: "By Queue" })).toBeInTheDocument();
expect(screen.getByRole("button", { name: "Across Queues" })).toBeInTheDocument();
expect(screen.getByRole("button", { name: "Routing Funnel" })).toBeInTheDocument();

// Line ~74 — tutorial walk test:
expect(screen.getByRole("heading", { name: "Routing Funnel" })).toBeInTheDocument();

// Line ~100 — cross-queue reference rows test:
await user.click((await screen.findAllByRole("button", { name: "Across Queues" }))[0]);

// Line ~114 — funnel detail routing values test:
await user.click((await screen.findAllByRole("button", { name: "Routing Funnel" }))[0]);
```

- [ ] **Step 4: Run the tests**

Run: `npm test`
Expected: PASS. The `App.test.tsx` assertions on old labels are gone; the new labels match.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/AppShell.tsx dashboard/src/views/FunnelDetailView.tsx dashboard/src/App.test.tsx
git commit -m "feat(dashboard): rename tabs and routing funnel heading to plain English"
```

---

## Task 11: Funnel chart label rewrites + Overview metric labels (in-place updates)

The MetricCard call sites in `OverviewView`, `PerQueueView`, and `FunnelDetailView` were already relabeled during Task 7. The remaining label rewrites are in `FunnelChart`'s step labels and `QueueCard`'s `dt` labels.

**Files:**
- Modify: `dashboard/src/charts/FunnelChart.tsx`
- Modify: `dashboard/src/components/QueueCard.tsx`
- Modify: `dashboard/src/App.test.tsx`

- [ ] **Step 1: Rewrite funnel step labels and rates pills**

In `dashboard/src/charts/FunnelChart.tsx`, replace the `steps` array entries' `label` strings and the `funnel-rates` block:

```tsx
const steps = [
  { label: "Calls in", value: funnel.primary_calls, color: QUEUE_META[primaryQueue].color },
  { label: "Answered on primary", value: funnel.primary_answered, color: "#2B7A4B" },
  { label: "Missed on primary", value: funnel.primary_failed, color: "#A32D2D" },
  { label: "Sent to overflow", value: funnel.overflow_received, color: QUEUE_META[overflowQueue].color },
  { label: "Answered on overflow", value: funnel.overflow_answered, color: "#2B7A4B" },
  { label: "Never connected", value: funnel.lost, color: "#A32D2D" },
  { label: "Untracked", value: funnel.unaccounted, color: "#7B6B3A" },
];
```

And replace the `funnel-rates` block:

```tsx
<div className="funnel-rates">
  <span>Right-language routing {formatPercent(funnel.routing_match)}</span>
  <span>Reached an agent {formatPercent(funnel.effective_answer_rate)}</span>
</div>
```

(Task 13 replaces this whole component with the new layered structure. For now the simple label rewrite keeps the test suite green and the dashboard usable.)

- [ ] **Step 2: Rewrite `QueueCard` dt labels**

In `dashboard/src/components/QueueCard.tsx`, replace the dt labels:

```tsx
<dt>Missed-call rate</dt>
…
<dt>Peak hour</dt>
…
<dt>Top agent</dt>
```

(`Top agent` is unchanged but listed for completeness.)

- [ ] **Step 3: Update `App.test.tsx` assertions for funnel labels**

In `dashboard/src/App.test.tsx`, replace the funnel-detail assertions (line ~118):

```tsx
expect(screen.getAllByText("Missed on primary").length).toBeGreaterThan(0);
expect(screen.getAllByText("Untracked").length).toBeGreaterThan(0);
```

- [ ] **Step 4: Run the tests**

Run: `npm test`
Expected: PASS. Funnel step labels match new strings.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/charts/FunnelChart.tsx dashboard/src/components/QueueCard.tsx dashboard/src/App.test.tsx
git commit -m "feat(dashboard): rewrite funnel and queue card labels in plain English"
```

---

## Task 12: Humanize anomaly kinds

**Files:**
- Modify: `dashboard/src/views/OverviewView.tsx`

- [ ] **Step 1: Swap `titleCase` for `humanizeAnomalyKind`**

In `dashboard/src/views/OverviewView.tsx`:

1. Update the import:
   ```tsx
   import { formatInteger, formatPercent, humanizeAnomalyKind } from "../utils/format";
   ```
   (Remove `titleCase` from the import if it's no longer used. Run `grep "titleCase" dashboard/src/views/OverviewView.tsx` to confirm — if only used for anomaly kinds, drop it.)

2. In the anomaly card render block, replace:
   ```tsx
   <strong>{titleCase(anomaly.kind)}</strong>
   ```
   with:
   ```tsx
   <strong>{humanizeAnomalyKind(anomaly.kind)}</strong>
   ```

- [ ] **Step 2: Run tests + typecheck**

Run: `npm test && npx tsc -b`
Expected: PASS. No existing assertion targets anomaly kind strings, so no test updates needed.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/views/OverviewView.tsx
git commit -m "feat(dashboard): humanize anomaly kind labels"
```

---

## Task 13: Restructure `FunnelChart` (layered layout + outcome chips)

This is the largest visual change. Rebuild the component end-to-end. The data props don't change; the rendering does.

**Files:**
- Modify: `dashboard/src/charts/FunnelChart.tsx`
- Test: `dashboard/src/charts/FunnelChart.test.tsx` (new)
- Modify: `dashboard/src/styles/app.css`
- Modify: `dashboard/src/App.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `dashboard/src/charts/FunnelChart.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FunnelChart } from "./FunnelChart";

import type { FunnelMetrics } from "../data/reportTypes";

const englishFunnel: FunnelMetrics = {
  primary_calls: 1181,
  primary_answered: 800,
  primary_failed: 200,
  overflow_received: 181,
  overflow_answered: 150,
  overflow_failed: 31,
  lost: 25,
  lost_rate: 25 / 1181,
  unaccounted: 6,
  routing_match: 0.983,
  effective_answer_rate: 0.847,
};

describe("FunnelChart", () => {
  it("renders the hero number with 'Calls in' eyebrow", () => {
    render(
      <FunnelChart
        language="English"
        funnel={englishFunnel}
        primaryQueue="8020"
        overflowQueue="8030"
      />,
    );
    expect(screen.getByText("Calls in")).toBeInTheDocument();
    expect(screen.getByText("1,181")).toBeInTheDocument();
  });

  it("shows both rate pills with plain-English labels", () => {
    render(
      <FunnelChart
        language="English"
        funnel={englishFunnel}
        primaryQueue="8020"
        overflowQueue="8030"
      />,
    );
    expect(screen.getByText(/Right-language routing 98.3%/)).toBeInTheDocument();
    expect(screen.getByText(/Reached an agent 84.7%/)).toBeInTheDocument();
  });

  it("renders the outcome strip with reached, never-connected, and hides untracked when zero", () => {
    render(
      <FunnelChart
        language="English"
        funnel={{ ...englishFunnel, unaccounted: 0 }}
        primaryQueue="8020"
        overflowQueue="8030"
      />,
    );
    expect(screen.getByText(/Reached someone:/)).toBeInTheDocument();
    expect(screen.getByText(/Never connected:/)).toBeInTheDocument();
    expect(screen.queryByText(/Untracked:/)).not.toBeInTheDocument();
  });

  it("shows the untracked chip when unaccounted > 0", () => {
    render(
      <FunnelChart
        language="English"
        funnel={englishFunnel}
        primaryQueue="8020"
        overflowQueue="8030"
      />,
    );
    expect(screen.getByText(/Untracked: 6/)).toBeInTheDocument();
  });

  it("hides the overflow detail bar when overflow_received is zero", () => {
    render(
      <FunnelChart
        language="French"
        funnel={{ ...englishFunnel, overflow_received: 0, overflow_answered: 0 }}
        primaryQueue="8021"
        overflowQueue="8031"
      />,
    );
    expect(screen.queryByText(/Answered on overflow/)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- FunnelChart`
Expected: FAIL — current component doesn't render the new structure.

- [ ] **Step 3: Rewrite `FunnelChart.tsx`**

Replace `dashboard/src/charts/FunnelChart.tsx` with:

```tsx
import { Tooltip } from "../components/Tooltip";
import { getGlossaryEntry } from "../data/glossary";
import type { FunnelMetrics, QueueId } from "../data/reportTypes";
import { QUEUE_META } from "../data/reportTypes";
import { formatInteger, formatPercent } from "../utils/format";

interface FunnelChartProps {
  language: "English" | "French";
  funnel: FunnelMetrics;
  primaryQueue: QueueId;
  overflowQueue: QueueId;
}

export function FunnelChart({ language, funnel, primaryQueue, overflowQueue }: FunnelChartProps) {
  const primaryColor = QUEUE_META[primaryQueue].color;
  const overflowColor = QUEUE_META[overflowQueue].color;
  const overflowMissed = Math.max(0, funnel.overflow_received - funnel.overflow_answered);
  const reachedTotal = funnel.primary_answered + funnel.overflow_answered;
  const reachedShare = funnel.primary_calls > 0 ? reachedTotal / funnel.primary_calls : 0;
  const primaryShare = funnel.primary_calls > 0 ? funnel.primary_answered / funnel.primary_calls : 0;
  const overflowShare = funnel.primary_calls > 0 ? funnel.overflow_received / funnel.primary_calls : 0;
  const ovfAnsShare = funnel.overflow_received > 0 ? funnel.overflow_answered / funnel.overflow_received : 0;
  const ovfMissShare = funnel.overflow_received > 0 ? overflowMissed / funnel.overflow_received : 0;

  return (
    <div className="funnel-chart" aria-label={`${language} routing funnel`}>
      <div className="funnel-hero">
        <p className="eyebrow">Calls in</p>
        <strong>{formatInteger(funnel.primary_calls)}</strong>
      </div>

      <div className="funnel-rates">
        <span>
          Right-language routing {formatPercent(funnel.routing_match)}
          <Tooltip
            id={`${language}-routing-tip`}
            label="Right-language routing"
            content={getGlossaryEntry("right_language_routing") ?? ""}
          />
        </span>
        <span>
          Reached an agent {formatPercent(funnel.effective_answer_rate)}
          <Tooltip
            id={`${language}-reached-tip`}
            label="Reached an agent"
            content={getGlossaryEntry("reached_an_agent") ?? ""}
          />
        </span>
      </div>

      <div className="funnel-leg" aria-label="Primary leg">
        <div className="funnel-bar">
          <span
            className="funnel-segment"
            style={{ width: `${primaryShare * 100}%`, backgroundColor: primaryColor }}
            title={`Answered on primary: ${formatInteger(funnel.primary_answered)}`}
          />
          <span
            className="funnel-segment"
            style={{ width: `${overflowShare * 100}%`, backgroundColor: overflowColor }}
            title={`Sent to overflow: ${formatInteger(funnel.overflow_received)}`}
          />
        </div>
        <p className="funnel-leg__caption">
          {formatInteger(funnel.primary_answered)} answered on primary ·{" "}
          {formatInteger(funnel.overflow_received)} sent to overflow
        </p>
      </div>

      {funnel.overflow_received > 0 ? (
        <div className="funnel-leg funnel-leg--child" aria-label="Overflow detail">
          <div className="funnel-bar">
            <span
              className="funnel-segment"
              style={{ width: `${ovfAnsShare * 100}%`, backgroundColor: overflowColor }}
              title={`Answered on overflow: ${formatInteger(funnel.overflow_answered)}`}
            />
            <span
              className="funnel-segment funnel-segment--loss"
              style={{ width: `${ovfMissShare * 100}%` }}
              title={`Missed on overflow: ${formatInteger(overflowMissed)}`}
            />
          </div>
          <p className="funnel-leg__caption">
            {formatInteger(funnel.overflow_answered)} answered on overflow ·{" "}
            {formatInteger(overflowMissed)} missed on overflow
          </p>
        </div>
      ) : null}

      <div className="funnel-outcomes">
        <span className="funnel-outcome">
          Reached someone: {formatInteger(reachedTotal)} ({formatPercent(reachedShare)})
        </span>
        <span className="funnel-outcome funnel-outcome--loss">
          Never connected: {formatInteger(funnel.lost)}
        </span>
        {funnel.unaccounted > 0 ? (
          <span className="funnel-outcome funnel-outcome--warn">
            Untracked: {formatInteger(funnel.unaccounted)}
          </span>
        ) : null}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Add the new CSS**

In `dashboard/src/styles/app.css`, find the existing `.funnel-chart`, `.funnel-rates`, `.funnel-row`, `.funnel-track` block (around lines 452–499) and replace it with:

```css
.funnel-chart {
  min-width: 0;
  display: grid;
  gap: 14px;
}

.funnel-hero {
  display: grid;
  gap: 2px;
}

.funnel-hero strong {
  font-family: var(--display-font);
  font-size: 28px;
  line-height: 1;
}

.funnel-rates {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  font-family: var(--sans-font);
  font-size: 12px;
}

.funnel-rates span {
  display: inline-flex;
  align-items: center;
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 6px 9px;
}

.funnel-leg {
  display: grid;
  gap: 6px;
}

.funnel-leg--child {
  margin-left: 16px;
  padding-left: 12px;
  border-left: 1px solid var(--border);
}

.funnel-bar {
  display: flex;
  height: 22px;
  border-radius: 5px;
  overflow: hidden;
  background: #e4ece1;
}

.funnel-segment {
  height: 100%;
  display: block;
}

.funnel-segment--loss {
  background: var(--loss);
}

.funnel-leg__caption {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.funnel-outcomes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.funnel-outcome {
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  font-size: 12px;
}

.funnel-outcome--loss {
  background: #f7dcdc;
  border-color: rgba(143, 47, 47, 0.4);
  color: var(--loss);
}

.funnel-outcome--warn {
  background: #f6efd5;
  border-color: rgba(180, 145, 30, 0.4);
  color: var(--gold);
}
```

- [ ] **Step 5: Update `App.test.tsx` assertion for the old funnel structure**

The existing test on line ~118 was already updated in Task 11 to look for "Missed on primary" and "Untracked". The new funnel chart renders "Missed on primary" only when displayed as a MetricCard in `FunnelDetailView` (still in place from Task 7). Verify:

Run: `npm test -- App.test`

If any assertion fails because the funnel chart no longer renders a row labeled `Missed on primary` (it doesn't — the FunnelChart now shows "Reached someone / Never connected / Untracked" chips and a leg caption with "answered on primary / sent to overflow"), update the assertion to:

```tsx
// In the "shows funnel detail routing values" test, replace any FunnelChart-specific
// row label assertions with assertions on the new chart structure or rely on the
// FunnelDetailView's MetricCard labels (which still exist with the new strings).
expect(screen.getAllByText("Missed on primary").length).toBeGreaterThan(0); // MetricCard
expect(screen.getAllByText("Untracked").length).toBeGreaterThan(0);          // MetricCard
expect(screen.getAllByText(/Right-language routing 98.3%/).length).toBeGreaterThan(0); // FunnelChart rate pill
```

- [ ] **Step 6: Run all tests**

Run: `npm test`
Expected: PASS.

- [ ] **Step 7: Run typecheck and build**

Run: `npx tsc -b && npm run build`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add dashboard/src/charts/FunnelChart.tsx dashboard/src/charts/FunnelChart.test.tsx dashboard/src/styles/app.css dashboard/src/App.test.tsx
git commit -m "feat(dashboard): restructure FunnelChart with hero, layered bars, outcome chips"
```

---

## Task 14: Queue identity flip in `QueueCard`

**Files:**
- Modify: `dashboard/src/components/QueueCard.tsx`

- [ ] **Step 1: Replace the chip content**

In `dashboard/src/components/QueueCard.tsx`, the queue chip currently shows `{summary.meta.id}` (e.g., `8020`). Replace it with a compact language/role tag and move the extension into the subtitle.

Find:

```tsx
<span className="queue-chip" style={{ "--queue-color": summary.meta.color } as React.CSSProperties}>
  {summary.meta.id}
</span>
<div>
  <h3>{summary.meta.name}</h3>
  <p>{summary.meta.language} {summary.meta.role}</p>
</div>
```

Replace with:

```tsx
<span className="queue-chip" style={{ "--queue-color": summary.meta.color } as React.CSSProperties}>
  {summary.meta.language === "English" ? "EN" : "FR"}
  <em>{summary.meta.role === "primary" ? "Pri" : "Ovr"}</em>
</span>
<div>
  <h3>{summary.meta.name}</h3>
  <p>
    {summary.meta.id} · {summary.meta.language} · {summary.meta.role}
  </p>
</div>
```

- [ ] **Step 2: Adjust chip CSS to fit two-line content**

In `dashboard/src/styles/app.css`, find the `.queue-chip` block (around line 361) and replace with:

```css
.queue-chip {
  width: 44px;
  height: 44px;
  display: inline-grid;
  place-items: center;
  align-content: center;
  gap: 0;
  border-radius: 6px;
  background: var(--queue-color);
  color: #fff;
  font-family: var(--sans-font);
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
}

.queue-chip em {
  font-style: normal;
  font-size: 9px;
  font-weight: 500;
  opacity: 0.85;
  margin-top: 2px;
}
```

- [ ] **Step 3: Run tests**

Run: `npm test`
Expected: PASS. The App test for "opens per queue from a queue card" (line ~40) finds the queue card by name `CSR French` — still works because the heading is unchanged. The `8021 · French · primary` text assertion on line ~48 still works.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/QueueCard.tsx dashboard/src/styles/app.css
git commit -m "feat(dashboard): lead with queue name; chip shows language and role"
```

---

## Task 15: Two-line reference chips on Overview + CrossQueue

**Files:**
- Modify: `dashboard/src/views/OverviewView.tsx`
- Modify: `dashboard/src/views/CrossQueueView.tsx`
- Modify: `dashboard/src/styles/app.css`
- Modify: `dashboard/src/App.test.tsx`

- [ ] **Step 1: Update Overview reference row**

In `dashboard/src/views/OverviewView.tsx`, replace the `reference-row` block in the `view-heading` section with:

```tsx
<div className="reference-row" aria-label="Period references">
  <span className="reference-chip">
    <em className="eyebrow">English primary queue</em>
    <strong>{formatInteger(report.queues["8020"].total_calls)}</strong>
    <small>CSR English · 8020</small>
  </span>
  <span className="reference-chip">
    <em className="eyebrow">Top agent</em>
    <strong>{topAgent?.agent_name ?? "n/a"}</strong>
    {topAgent ? <small>{formatInteger(topAgent.total_calls)} calls</small> : null}
  </span>
  <span className="reference-chip">
    <em className="eyebrow">Top caller</em>
    <strong>{topCaller ? formatPhone(topCaller.caller_number_norm) : "n/a"}</strong>
    {topCaller ? <small>{formatInteger(topCaller.total_calls)} calls</small> : null}
  </span>
</div>
```

Update the import:

```tsx
import { formatInteger, formatPercent, formatPhone, humanizeAnomalyKind } from "../utils/format";
```

- [ ] **Step 2: Update CrossQueue reference row**

In `dashboard/src/views/CrossQueueView.tsx`, replace the `reference-row` block with:

```tsx
<div className="reference-row" aria-label="Period references">
  <span className="reference-chip">
    <em className="eyebrow">Top agent</em>
    <strong>{topAgent?.agent_name ?? "n/a"}</strong>
    {topAgent ? <small>{formatInteger(topAgent.total_calls)} calls</small> : null}
  </span>
  <span className="reference-chip">
    <em className="eyebrow">Top caller</em>
    <strong>{topCaller ? formatPhone(topCaller.caller_number_norm) : "n/a"}</strong>
    {topCaller ? <small>{formatInteger(topCaller.total_calls)} calls</small> : null}
  </span>
</div>
```

Update the import:

```tsx
import { formatInteger, formatPhone } from "../utils/format";
```

- [ ] **Step 3: Replace the reference chip CSS**

In `dashboard/src/styles/app.css`, find the existing `.reference-row span` block (around line 237) and replace it with:

```css
.reference-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.reference-chip {
  display: grid;
  gap: 2px;
  padding: 8px 12px;
  min-width: 140px;
  border: 1px solid rgba(47, 122, 63, 0.24);
  border-radius: 10px;
  background: #f8fbf6;
  color: var(--text);
}

.reference-chip .eyebrow {
  margin: 0;
  font-style: normal;
  font-family: var(--sans-font);
  font-size: 10px;
  text-transform: none;
  letter-spacing: 0;
  color: var(--muted);
}

.reference-chip strong {
  font-family: var(--mono-font);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.15;
  word-break: break-word;
}

.reference-chip small {
  font-family: var(--sans-font);
  font-size: 11px;
  color: var(--muted);
}
```

- [ ] **Step 4: Update `App.test.tsx` reference-row assertions**

In `dashboard/src/App.test.tsx`, the test "shows cross-queue reference rows" (line ~96) checks for joined strings like `Alicia Yameen 241` and `9052833500 63`. Update to:

```tsx
it("shows cross-queue reference rows", async () => {
  const user = userEvent.setup();
  render(<App />);

  await user.click((await screen.findAllByRole("button", { name: "Across Queues" }))[0]);

  // Reference chips now render the formatted phone number; the joined "name + count"
  // string is gone (chips split label/value/support into separate elements).
  expect(screen.getAllByText("Alicia Yameen").length).toBeGreaterThan(0);
  expect(screen.getAllByText("+1 (905) 283-3500").length).toBeGreaterThan(0);
  expect(screen.getAllByText("241").length).toBeGreaterThan(0);
  // Caller table still renders raw normalized number and the count:
  expect(screen.getAllByText("9052833500").length).toBeGreaterThan(0);
  expect(screen.getAllByText("63").length).toBeGreaterThan(0);
});
```

- [ ] **Step 5: Run tests + typecheck**

Run: `npm test && npx tsc -b`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/views/OverviewView.tsx dashboard/src/views/CrossQueueView.tsx dashboard/src/styles/app.css dashboard/src/App.test.tsx
git commit -m "feat(dashboard): two-line reference chips with humanized phone numbers"
```

---

## Task 16: Status strip — collapse when healthy

**Files:**
- Modify: `dashboard/src/components/AppShell.tsx`
- Modify: `dashboard/src/styles/app.css`

- [ ] **Step 1: Restructure the strip**

In `dashboard/src/components/AppShell.tsx`, add a `useState` import:

```tsx
import { useState } from "react";
import { ChevronDown, ChevronRight, CircleHelp, Download, RefreshCw } from "lucide-react";
```

Inside the `AppShell` component, after the `const validation = …; const source = …;` lines, add:

```tsx
const sourceGaps = report?.source_gaps.length ?? 0;
const warning = loadResult?.status === "loaded" ? loadResult.warning : undefined;
const isDegraded =
  sourceGaps > 0 ||
  Boolean(warning) ||
  validation === "failed";
const [expanded, setExpanded] = useState(isDegraded);
const showExpanded = expanded || isDegraded;
const compactLabel = report
  ? `Loaded · ${report.date_range.start.slice(0, 7)} · Source: ${source}`
  : "Loading…";
```

Replace the existing `<div className="status-strip">…</div>` block with:

```tsx
<div className={`status-strip ${showExpanded ? "is-expanded" : ""}`}>
  <button
    type="button"
    className="status-strip__toggle"
    aria-expanded={showExpanded}
    onClick={() => setExpanded((current) => !current)}
  >
    {showExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
    <span>{showExpanded ? "Hide status" : compactLabel}</span>
  </button>
  {showExpanded ? (
    <>
      <span>Source: {source}</span>
      <span className={validation === "failed" ? "warning" : ""}>Validation: {validation}</span>
      <span className={sourceGaps > 0 ? "warning" : ""}>Source gaps: {sourceGaps}</span>
      {warning ? <span className="warning">Fallback: {warning}</span> : null}
    </>
  ) : null}
</div>
```

- [ ] **Step 2: Update the status strip CSS**

In `dashboard/src/styles/app.css`, find the `.status-strip` block (around line 191) and replace with:

```css
.status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 6px 24px;
  border-bottom: 1px solid var(--border);
  background: #fbfcfa;
  font-family: var(--sans-font);
  font-size: 11px;
  color: var(--muted);
  align-items: center;
}

.status-strip.is-expanded {
  padding: 9px 24px;
}

.status-strip__toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  padding: 2px 4px;
  border-radius: 4px;
}

.status-strip__toggle:hover,
.status-strip__toggle:focus-visible {
  background: var(--surface-subtle);
  color: var(--text);
  outline: none;
}
```

- [ ] **Step 3: Run tests + typecheck**

Run: `npm test && npx tsc -b`
Expected: PASS. No existing test asserts on the status strip directly.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/AppShell.tsx dashboard/src/styles/app.css
git commit -m "feat(dashboard): collapse status strip when healthy; expand on demand or on issues"
```

---

## Task 17: Typography polish

**Files:**
- Modify: `dashboard/src/styles/app.css`

- [ ] **Step 1: Move targeted labels from mono to sans**

In `dashboard/src/styles/app.css`, make the following edits. Use exact-string replacements; some rules combine multiple selectors.

**(a)** Find and update the tabs / segmented-control button rule (around line 108):

```css
.tabs button,
.segmented-control button {
  min-width: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  padding: 8px 11px;
  font-family: var(--sans-font);
  font-size: 12px;
  font-weight: 500;
}
```

**(b)** Find and update the report-controls label rule (around line 138):

```css
.report-controls label {
  min-width: 0;
  display: grid;
  gap: 4px;
  font-family: var(--sans-font);
  font-size: 11px;
  color: var(--muted);
}
```

**(c)** Find and update the `.text-button` rule (around line 168):

```css
.text-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 11px;
  font-family: var(--sans-font);
  font-size: 12px;
  white-space: nowrap;
}
```

**(d)** Find and update the `.eyebrow` rule (around line 305):

```css
.eyebrow {
  margin: 0;
  color: var(--muted);
  font-family: var(--sans-font);
  font-size: 11px;
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0;
}
```

**(e)** Find and update the `.metric-card strong` rule (around line 291):

```css
.metric-card strong {
  font-family: var(--mono-font);
  font-size: 32px;
  line-height: 1.0;
}
```

**(f)** Find and update the `.queue-card dt` rule (around line 381):

```css
.queue-card dt {
  color: var(--muted);
  font-family: var(--sans-font);
  font-size: 10px;
  font-weight: 500;
}
```

- [ ] **Step 2: Run tests + typecheck + build**

Run: `npm test && npx tsc -b && npm run build`
Expected: PASS. No test asserts on font properties.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/styles/app.css
git commit -m "style(dashboard): move labels to sans; promote metric numerals; calm eyebrow"
```

---

## Task 18: Validation — end-to-end check against the April fixture

**Files:** None modified. This is a verification gate.

- [ ] **Step 1: Run the full test suite**

Run: `npm test`
Expected: ALL PASS.

- [ ] **Step 2: Run typecheck and build**

Run: `npx tsc -b && npm run build`
Expected: ALL PASS.

- [ ] **Step 3: Start the dev server**

Run: `npm run dev`
Expected: Server starts at `http://127.0.0.1:5173`.

- [ ] **Step 4: Visual checklist on the Overview tab**

Open `http://127.0.0.1:5173`. With the April 2026 report selected, confirm:

- Tabs read: `Overview · By Queue · Across Queues · Routing Funnel`.
- Period summary strip appears between heading and funnel grid, reading `April 2026 — 1,620 calls handled` and showing the reach rate cell with a `Watch` pill (reach rate ≈ 84%).
- Reference chips show two lines: top label, value, support. Top caller value reads `+1 (905) 283-3500` (not `9052833500`).
- English/French funnel charts show a hero number, two pill rates (both with `?` icons), a primary leg bar, an overflow detail bar, and outcome chips. Untracked chip visible only when `unaccounted > 0`.
- English "reached an agent" card shows `84.7%` with `Watch` pill.
- Anomaly card kinds read in plain English (`Volume spike`, `Caller hit multiple queues`, etc.).
- Status strip is collapsed to a single muted line.

- [ ] **Step 5: Visual checklist on the By Queue tab**

Click `By Queue`. Confirm:

- View heading still leads with `CSR English` and shows `8020 · English · primary` as subtitle.
- Six metric cards show new labels: `Total calls`, `Avg per active day`, `Busiest day`, `Missed-call rate`, `Peak hour`, `Top caller`.
- `Missed-call rate` card shows a `Good` / `Watch` / `At risk` pill depending on value, and the eyebrow has a `?` tooltip.

- [ ] **Step 6: Visual checklist on the Routing Funnel tab**

Click `Routing Funnel`. Confirm:

- Heading reads `Routing Funnel`.
- Each language renders the new layered chart structure plus the existing metric grid (cards now use plain-English labels: `Calls in`, `Answered on primary`, `Missed on primary`, etc.).

- [ ] **Step 7: Visual checklist on the Across Queues tab**

Click `Across Queues`. Confirm:

- Heading and reference row use the two-line chip format.
- Tables still load and sort.

- [ ] **Step 8: Final commit (only if any fix-ups were needed during validation)**

If the visual checks passed cleanly, no further commit. If any fix was needed, commit it with a descriptive message and re-run all checks.

---

## Self-Review Notes

**Spec coverage:** Every section of the spec is covered.

- Section 1 (labels & glossary): Tasks 2 (glossary), 3 (humanize helper), 7 (metric card relabels), 10 (tabs), 11 (funnel labels, queue card labels), 12 (anomaly humanization).
- Section 2 (period summary): Tasks 4 (selector), 8 (component), 9 (wire-in).
- Section 3 (threshold badges + tooltips): Tasks 1 (thresholds), 5 (badge tokens), 6 (tooltip), 7 (MetricCard migration).
- Section 4 (polish + funnel): Tasks 13 (funnel restructure), 14 (queue identity flip), 15 (reference chips), 16 (status strip), 17 (typography).

**Type consistency:** `MetricStatus` is defined in Task 1 and reused by Tasks 7 and 8. `PeriodSummary` interface is defined in Task 4's selector code, then imported by Task 8's component. `getGlossaryEntry` is defined in Task 2, consumed by Tasks 7 and 13.

**No placeholders:** All steps include the actual code or commands.
