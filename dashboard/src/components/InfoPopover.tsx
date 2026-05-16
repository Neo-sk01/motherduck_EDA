import { Info, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { getMetricInfo } from "../data/metricInfo";

interface InfoPopoverProps {
  infoId: string;
}

export function InfoPopover({ infoId }: InfoPopoverProps) {
  const [open, setOpen] = useState(false);
  const hostRef = useRef<HTMLSpanElement>(null);
  const info = getMetricInfo(infoId);

  useEffect(() => {
    if (!open) return undefined;
    const handleMouseDown = (event: MouseEvent) => {
      if (!hostRef.current) return;
      if (!hostRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  if (!info) return null;

  const popoverId = `${infoId}-info`;

  return (
    <span className="info-host" ref={hostRef}>
      <button
        type="button"
        className="info-trigger"
        aria-label={`About ${info.title}`}
        aria-expanded={open}
        aria-controls={popoverId}
        onClick={() => setOpen((current) => !current)}
      >
        <Info aria-hidden="true" size={14} />
      </button>
      <span
        id={popoverId}
        role="dialog"
        aria-label={info.title}
        className={`info-popover ${open ? "is-open" : ""}`}
        hidden={!open}
      >
        <span className="info-popover__head">
          <strong>{info.title}</strong>
          <button
            type="button"
            className="info-popover__close"
            aria-label="Close"
            onClick={() => setOpen(false)}
          >
            <X aria-hidden="true" size={14} />
          </button>
        </span>
        <span className="info-popover__section-label">How it's calculated</span>
        <span className="info-popover__body">{info.howCalculated}</span>
        <span className="info-popover__section-label">Why it matters</span>
        <span className="info-popover__body">{info.whyMatters}</span>
      </span>
    </span>
  );
}
