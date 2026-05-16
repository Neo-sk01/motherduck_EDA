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
  const overflowMissed = funnel.overflow_failed;
  const reachedTotal = funnel.primary_answered + funnel.overflow_answered;
  const reachedShare = funnel.primary_calls > 0 ? reachedTotal / funnel.primary_calls : 0;
  const primaryShare = funnel.primary_calls > 0 ? funnel.primary_answered / funnel.primary_calls : 0;
  const overflowShare = funnel.primary_calls > 0 ? funnel.overflow_received / funnel.primary_calls : 0;
  const ovfAnsShare = funnel.overflow_received > 0 ? funnel.overflow_answered / funnel.overflow_received : 0;
  const ovfMissShare = funnel.overflow_received > 0 ? overflowMissed / funnel.overflow_received : 0;
  const routingTooltip = getGlossaryEntry("right_language_routing");
  const reachedTooltip = getGlossaryEntry("reached_an_agent");

  return (
    <div className="funnel-chart" aria-label={`${language} routing funnel`}>
      <div className="funnel-hero">
        <p className="eyebrow">Calls in</p>
        <strong>{formatInteger(funnel.primary_calls)}</strong>
      </div>

      <div className="funnel-rates">
        <span>
          Right-language routing {formatPercent(funnel.routing_match)}
          {routingTooltip ? (
            <Tooltip
              id={`${language}-routing-tip`}
              label="Right-language routing"
              content={routingTooltip}
            />
          ) : null}
        </span>
        <span>
          Reached an agent {formatPercent(funnel.effective_answer_rate)}
          {reachedTooltip ? (
            <Tooltip
              id={`${language}-reached-tip`}
              label="Reached an agent"
              content={reachedTooltip}
            />
          ) : null}
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
