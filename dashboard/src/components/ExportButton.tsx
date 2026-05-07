import { Download } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

interface ExportButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
}

export function ExportButton({ label, ...props }: ExportButtonProps) {
  return (
    <button className="icon-button" type="button" aria-label={label} title={label} {...props}>
      <Download aria-hidden="true" size={16} />
    </button>
  );
}
