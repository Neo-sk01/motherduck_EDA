export interface MetricInfo {
  title: string;
  howCalculated: string;
  whyMatters: string;
}

export const METRIC_INFO: Record<string, MetricInfo> = {
  // ── Period summary ─────────────────────────────────────────────
  period_total_calls: {
    title: "Calls handled",
    howCalculated:
      "Sum of total_calls across all four queues (CSR English 8020, CSR French 8021, CSR Overflow English 8030, CSR Overflow French 8031) for the selected period.",
    whyMatters:
      "Top-line traffic volume for the month. Use the per-queue cards below to see where the load actually sat.",
  },
  reach_rate: {
    title: "Reach rate",
    howCalculated:
      "(Σ primary_answered + Σ overflow_answered) ÷ Σ primary_calls, weighted across both languages. Same formula as the per-language 'Reached an agent' card on each funnel.",
    whyMatters:
      "The headline 'how well did we serve callers this month' number. Below 80% → staffing or routing gap; above 90% → healthy. Track month-over-month.",
  },
  anomaly_count: {
    title: "Anomalies",
    howCalculated:
      "Count of anomalies emitted by the analytics pipeline (system-agent detections, hourly no-answer spikes, cross-queue callers, etc.). Severity is set by the rule that fires.",
    whyMatters:
      "Quick filter for 'is there anything I should look closer at this month?'. Click the count to jump to the anomaly list below.",
  },
  source_gap: {
    title: "Coverage gaps",
    howCalculated:
      "Days inside the selected period where the raw call export was empty or returned an error. A gap means we lost visibility for that day.",
    whyMatters:
      "Trust signal — if gaps exist, every total on the page undercounts real volume by an unknown amount. Investigate before quoting any number externally.",
  },

  // ── Funnel / cross-queue rates ─────────────────────────────────
  reached_an_agent: {
    title: "Reached an agent",
    howCalculated:
      "(primary_answered + overflow_answered) ÷ primary_calls, computed per language. A call counts as 'reached' if it connected to a live agent on the primary queue or after overflow.",
    whyMatters:
      "Best single summary of operational health. Below 80% suggests staffing or routing gaps; above 90% is healthy.",
  },
  right_language_routing: {
    title: "Right-language routing",
    howCalculated:
      "Share of calls placed on the queue that matches the caller's spoken language. Mismatch usually means the IVR or auto-attendant classified the language wrong.",
    whyMatters:
      "Mis-routed calls feel worse to customers and take longer to resolve. Below 85% suggests the language-detection layer needs a look.",
  },

  // ── Funnel step values ─────────────────────────────────────────
  calls_in: {
    title: "Calls in",
    howCalculated:
      "primary_calls — total calls entering the primary queue for this language. Equal to primary_answered + primary_failed; primary_failed includes overflow-bound calls and final losses.",
    whyMatters:
      "The denominator for every other number in this funnel. Everything else is a fraction of this.",
  },
  answered_on_primary: {
    title: "Answered on primary",
    howCalculated:
      "Calls that reached an agent on the primary queue without being routed to overflow.",
    whyMatters:
      "The happy path. High values mean the primary queue is absorbing demand on its own.",
  },
  missed_on_primary: {
    title: "Missed on primary",
    howCalculated:
      "primary_calls − primary_answered. Includes both calls routed onward to overflow and calls that hung up on the primary queue.",
    whyMatters:
      "Indicates pressure on the primary leg. If 'Sent to overflow' doesn't account for all of these, the rest were dropped before any agent picked up.",
  },
  sent_to_overflow: {
    title: "Sent to overflow",
    howCalculated:
      "overflow_received — calls that left the primary queue and arrived on the overflow queue (e.g., 8030 for English).",
    whyMatters:
      "Routing-volume signal. High values mean the primary queue can't keep up alone and the overflow team is doing real work.",
  },
  answered_on_overflow: {
    title: "Answered on overflow",
    howCalculated:
      "overflow_answered — calls that connected to an agent after arriving on the overflow queue.",
    whyMatters:
      "Calls salvaged by the overflow team. The bigger this is relative to 'Sent to overflow', the more effective the overflow leg.",
  },
  never_connected: {
    title: "Never connected",
    howCalculated:
      "lost — calls that didn't reach any agent on either the primary or overflow queue. The caller hung up or the system dropped them before connection.",
    whyMatters:
      "Pure missed business. Each one is a customer who couldn't get through. Usually the most actionable signal for staffing decisions.",
  },
  untracked: {
    title: "Untracked",
    howCalculated:
      "unaccounted — calls present in the raw queue log but not classifiable as answered, missed, or routed (e.g., the session ended before a disposition was recorded).",
    whyMatters:
      "Small numbers are expected. A growing untracked count usually means a Versature export gap or a release-reason value the pipeline doesn't recognise.",
  },

  // ── Per-queue cards ────────────────────────────────────────────
  total_calls: {
    title: "Total calls",
    howCalculated:
      "Count of cleaned calls assigned to this queue for the selected period, after deduplication on (caller, agent, timestamp).",
    whyMatters:
      "Baseline volume — sets the denominator for every rate on this card and tells you whether the queue is busy at all.",
  },
  avg_per_active_day: {
    title: "Average per active day",
    howCalculated:
      "total_calls ÷ days_with_calls. 'Active' days are weekdays where the queue saw at least one call.",
    whyMatters:
      "Normalises across holidays and weekends so you can compare a 22-business-day month to a 19-business-day month without skew.",
  },
  busiest_day: {
    title: "Busiest day",
    howCalculated:
      "The calendar day inside the selected period with the highest call count for this queue.",
    whyMatters:
      "Identifies the outlier load a staffing plan needs to absorb. Cross-reference with the daily volume chart for context.",
  },
  missed_call_rate: {
    title: "Missed-call rate",
    howCalculated:
      "no_agent_calls ÷ total_calls per queue per period. Counts calls that hung up or timed out before any agent picked up.",
    whyMatters:
      "Direct staffing signal — high missed-call rates point to peak hours that need more agents. Per-hour breakdown is on the hourly chart.",
  },
  peak_hour: {
    title: "Peak hour",
    howCalculated:
      "The hour-of-day (24-hour clock) with the highest call volume aggregated across every active day in the selected period.",
    whyMatters:
      "The most useful staffing signal — schedule the most agents around this hour first, then fan out.",
  },
  top_caller: {
    title: "Top caller",
    howCalculated:
      "Caller phone number with the most inbound calls into this queue for the period. Internal/test numbers can sometimes lead this list — verify before acting.",
    whyMatters:
      "Surfaces heavy users who may need a direct line, a tier-2 escalation path, or who should be flagged as suspicious / automated traffic.",
  },
};

export function getMetricInfo(infoId: string | undefined): MetricInfo | undefined {
  if (!infoId) return undefined;
  return METRIC_INFO[infoId];
}
