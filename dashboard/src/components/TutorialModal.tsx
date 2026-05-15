import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { ViewKey } from "../data/reportTypes";

export interface TutorialStep {
  title: string;
  body: string;
  view: ViewKey;
  checkpoints: string[];
}

export const TUTORIAL_STEPS: TutorialStep[] = [
  {
    title: "Start with Period Health",
    body: "Start with the health snapshot to see total load, routing quality, answer rates, and the anomalies that need attention first.",
    view: "overview",
    checkpoints: ["Use queue cards to drill into a queue.", "Use anomaly cards as shortcuts into problem areas."],
  },
  {
    title: "Review One Queue",
    body: "Pick an individual queue to inspect daily volume, hourly no-answer pressure, release reasons, top agents, and repeat callers.",
    view: "per-queue",
    checkpoints: ["Switch queues with the queue selector.", "Export charts or tables when a detail needs to be shared."],
  },
  {
    title: "Compare Across Queues",
    body: "Compare agents and callers across queues to find shared demand, cross-queue patterns, and timing issues that one queue view can hide.",
    view: "cross-queue",
    checkpoints: ["Toggle multi-queue callers for overlap.", "Switch between raw and normalized volume overlays."],
  },
  {
    title: "Trace The Funnel",
    body: "Use funnel detail to follow primary calls into overflow, final loss, routing match, and any unaccounted transfer gaps.",
    view: "funnel-detail",
    checkpoints: ["Review English and French funnels separately.", "Use effective answer rate as the clean operational summary."],
  },
];

interface TutorialModalProps {
  isOpen: boolean;
  stepIndex: number;
  onClose: () => void;
  onStepChange: (stepIndex: number) => void;
  onViewChange: (view: ViewKey) => void;
}

export function TutorialModal({
  isOpen,
  stepIndex,
  onClose,
  onStepChange,
  onViewChange,
}: TutorialModalProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const step = TUTORIAL_STEPS[stepIndex] ?? TUTORIAL_STEPS[0];
  const isFirstStep = stepIndex === 0;
  const isLastStep = stepIndex === TUTORIAL_STEPS.length - 1;

  useEffect(() => {
    if (!isOpen) return undefined;

    closeButtonRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const goToStep = (nextStepIndex: number) => {
    const nextStep = TUTORIAL_STEPS[nextStepIndex];
    if (!nextStep) return;
    onStepChange(nextStepIndex);
    onViewChange(nextStep.view);
  };

  return (
    <div className="tutorial-backdrop">
      <section
        aria-describedby="tutorial-copy"
        aria-labelledby="tutorial-heading"
        aria-modal="true"
        className="tutorial-modal"
        role="dialog"
      >
        <div className="tutorial-modal__header">
          <div>
            <p className="eyebrow">
              Step {stepIndex + 1} of {TUTORIAL_STEPS.length}
            </p>
            <h2 id="tutorial-heading">CSH platform guide</h2>
          </div>
          <button
            ref={closeButtonRef}
            aria-label="Close tutorial"
            className="icon-button"
            type="button"
            onClick={onClose}
          >
            <X aria-hidden="true" size={16} />
          </button>
        </div>

        <div className="tutorial-modal__body">
          <h3>{step.title}</h3>
          <p id="tutorial-copy">{step.body}</p>
          <ul>
            {step.checkpoints.map((checkpoint) => (
              <li key={checkpoint}>{checkpoint}</li>
            ))}
          </ul>
        </div>

        <div className="tutorial-progress" aria-label="Tutorial progress">
          {TUTORIAL_STEPS.map((item, index) => (
            <button
              key={item.view}
              type="button"
              className={index === stepIndex ? "is-active" : ""}
              aria-label={`Go to step ${index + 1}: ${item.title}`}
              onClick={() => goToStep(index)}
            />
          ))}
        </div>

        <div className="tutorial-modal__footer">
          <button className="text-button" type="button" onClick={onClose}>
            Skip tour
          </button>
          <div>
            <button
              className="text-button"
              type="button"
              disabled={isFirstStep}
              onClick={() => goToStep(stepIndex - 1)}
            >
              <ChevronLeft aria-hidden="true" size={15} />
              Back
            </button>
            <button
              className="text-button tutorial-primary"
              type="button"
              onClick={() => (isLastStep ? onClose() : goToStep(stepIndex + 1))}
            >
              {isLastStep ? "Finish" : "Next"}
              {!isLastStep ? <ChevronRight aria-hidden="true" size={15} /> : null}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
