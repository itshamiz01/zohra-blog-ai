import React from "react";
import { CheckCircle2, AlertTriangle, AlertOctagon, PauseCircle, PlayCircle, Clock, XCircle, HelpCircle } from "lucide-react";

export type StatusType =
  | "HEALTHY"
  | "WARNING"
  | "CRITICAL"
  | "PAUSED"
  | "RUNNING"
  | "WAITING"
  | "FAILED"
  | "SUCCESS"
  | "UNKNOWN";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md" | "lg";
}

const statusConfig: Record<StatusType, { bg: string; text: string; icon: React.ReactNode }> = {
  HEALTHY: { bg: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400", text: "Healthy", icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
  SUCCESS: { bg: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400", text: "Success", icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
  WARNING: { bg: "bg-amber-500/10 border-amber-500/30 text-amber-400", text: "Warning", icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  CRITICAL: { bg: "bg-rose-500/10 border-rose-500/30 text-rose-400", text: "Critical", icon: <AlertOctagon className="w-3.5 h-3.5" /> },
  FAILED: { bg: "bg-rose-500/10 border-rose-500/30 text-rose-400", text: "Failed", icon: <XCircle className="w-3.5 h-3.5" /> },
  PAUSED: { bg: "bg-slate-500/10 border-slate-500/30 text-slate-400", text: "Paused", icon: <PauseCircle className="w-3.5 h-3.5" /> },
  RUNNING: { bg: "bg-blue-500/10 border-blue-500/30 text-blue-400", text: "Running", icon: <PlayCircle className="w-3.5 h-3.5 animate-spin" /> },
  WAITING: { bg: "bg-purple-500/10 border-purple-500/30 text-purple-400", text: "Waiting", icon: <Clock className="w-3.5 h-3.5" /> },
  UNKNOWN: { bg: "bg-zinc-500/10 border-zinc-500/30 text-zinc-400", text: "Unknown", icon: <HelpCircle className="w-3.5 h-3.5" /> },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = "md" }) => {
  const norm = (status || "").toUpperCase() as StatusType;
  const cfg = statusConfig[norm] || statusConfig.UNKNOWN;

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium border rounded-full ${cfg.bg} ${
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"
      }`}
    >
      {cfg.icon}
      <span>{cfg.text}</span>
    </span>
  );
};
