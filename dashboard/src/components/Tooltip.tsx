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
      <span
        role="tooltip"
        id={id}
        className={`tooltip-popover ${open ? "is-open" : ""}`}
        hidden={!open}
      >
        {content}
      </span>
    </span>
  );
}
