import React from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  icon?: React.ReactNode;
  variant?: "default" | "warning" | "critical" | "success";
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  sublabel,
  icon,
  variant = "default",
}) => {
  const borderVariants = {
    default: "border-slate-800 bg-slate-900/60",
    warning: "border-amber-500/30 bg-amber-950/20",
    critical: "border-rose-500/30 bg-rose-950/20",
    success: "border-emerald-500/30 bg-emerald-950/20",
  };

  return (
    <div className={`p-4 rounded-xl border backdrop-blur-sm ${borderVariants[variant]}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>
      <div className="mt-2 text-2xl font-bold tracking-tight text-slate-100">{value}</div>
      {sublabel && <div className="mt-1 text-xs text-slate-400">{sublabel}</div>}
    </div>
  );
};
