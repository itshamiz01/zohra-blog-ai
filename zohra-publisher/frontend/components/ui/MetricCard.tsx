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
    default: "border-[#E7DCB8] bg-white/60",
    warning: "border-[#C9A227]/30 bg-amber-950/20",
    critical: "border-rose-500/30 bg-rose-50/20",
    success: "border-emerald-500/30 bg-emerald-50/20",
  };

  return (
    <div className={`p-4 rounded-xl border backdrop-blur-sm ${borderVariants[variant]}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-stone-500 uppercase tracking-wider">{label}</span>
        {icon && <div className="text-stone-500">{icon}</div>}
      </div>
      <div className="mt-2 text-2xl font-bold tracking-tight text-[#123B2A]">{value}</div>
      {sublabel && <div className="mt-1 text-xs text-stone-500">{sublabel}</div>}
    </div>
  );
};
