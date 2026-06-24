import { CheckCircle2, XCircle, AlertTriangle, Loader2, Circle } from "lucide-react";

const CONFIG = {
  agreed: {
    label: "Agreed",
    cls: "border-success/40 bg-success/15 text-success",
    Icon: CheckCircle2,
    spin: false,
  },
  walked_away: {
    label: "Walked Away",
    cls: "border-danger/40 bg-danger/15 text-red-400",
    Icon: XCircle,
    spin: false,
  },
  escalated: {
    label: "Escalated",
    cls: "border-warning/40 bg-warning/15 text-amber-300",
    Icon: AlertTriangle,
    spin: false,
  },
  in_progress: {
    label: "In Progress",
    cls: "border-accent/40 bg-accent/15 text-indigo-300",
    Icon: Loader2,
    spin: true,
  },
  idle: {
    label: "Waiting",
    cls: "border-white/15 bg-white/5 text-white/50",
    Icon: Circle,
    spin: false,
  },
};

export function OutcomeBadge({ status }) {
  const { label, cls, Icon, spin } = CONFIG[status] ?? CONFIG.idle;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${cls}`}
    >
      <Icon className={`h-3.5 w-3.5 ${spin ? "animate-spin" : ""}`} aria-hidden="true" />
      {label}
    </span>
  );
}
