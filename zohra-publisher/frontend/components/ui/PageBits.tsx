import React from "react";
import { AlertTriangle, Inbox, Loader2, RefreshCw } from "lucide-react";

/** Page title + one-line plain description + optional Refresh button. */
export const PageHeader: React.FC<{
  title: string;
  description: string;
  onRefresh?: () => void;
  refreshing?: boolean;
}> = ({ title, description, onRefresh, refreshing }) => (
  <div className="flex items-start justify-between gap-4 mb-6">
    <div>
      <h1 className="text-xl font-bold text-[#123B2A]">{title}</h1>
      <p className="text-sm text-stone-500 mt-0.5">{description}</p>
    </div>
    {onRefresh && (
      <button
        onClick={onRefresh}
        disabled={refreshing}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#D8C78F] hover:border-[#C9A227] text-[#123B2A] rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 shrink-0"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
        Refresh
      </button>
    )}
  </div>
);

export const StateLoading: React.FC = () => (
  <div className="flex items-center gap-2 text-sm text-stone-500 py-10 justify-center">
    <Loader2 className="w-4 h-4 animate-spin" /> Loading…
  </div>
);

export const StateError: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div className="border border-rose-500/30 bg-rose-50 rounded-xl p-5 flex items-start gap-3">
    <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
    <div>
      <div className="text-sm font-semibold text-rose-600">Something didn't load</div>
      <p className="text-sm text-stone-600 mt-0.5">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold"
        >
          Try again
        </button>
      )}
    </div>
  </div>
);

export const StateEmpty: React.FC<{ title: string; hint?: string }> = ({ title, hint }) => (
  <div className="border border-dashed border-[#D8C78F] bg-white/60 rounded-xl p-8 text-center">
    <Inbox className="w-8 h-8 text-[#C9A227] mx-auto mb-2" />
    <div className="text-sm font-semibold text-[#123B2A]">{title}</div>
    {hint && <p className="text-sm text-stone-500 mt-1">{hint}</p>}
  </div>
);

export interface Column {
  label: string;
  render: (row: any) => React.ReactNode;
  className?: string;
}

/** Simple, readable table used across the dashboard's list pages. */
export const SimpleTable: React.FC<{
  columns: Column[];
  rows: any[];
  emptyTitle: string;
  emptyHint?: string;
}> = ({ columns, rows, emptyTitle, emptyHint }) => {
  if (!rows || rows.length === 0) return <StateEmpty title={emptyTitle} hint={emptyHint} />;
  return (
    <div className="border border-[#E7DCB8] bg-white rounded-xl overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[#F7F2E2] text-left">
            {columns.map((c, i) => (
              <th key={i} className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-stone-500">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={row.id || row.job_id || ri} className="border-t border-[#E7DCB8]/70 hover:bg-[#FAF9F5]">
              {columns.map((c, ci) => (
                <td key={ci} className={`px-4 py-2.5 text-stone-700 ${c.className || ""}`}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

/** Site dropdown for the pages whose data is per-site. */
export const SitePicker: React.FC<{
  sites: any[];
  value: string;
  onChange: (id: string) => void;
}> = ({ sites, value, onChange }) => (
  <div className="flex items-center gap-2 mb-5">
    <label className="text-sm font-medium text-stone-600">Site:</label>
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="px-3 py-2 text-sm bg-white border border-[#D8C78F] rounded-lg text-[#123B2A] focus:outline-none focus:border-[#C9A227]"
    >
      <option value="">Select a site…</option>
      {sites.map((s) => (
        <option key={s.id} value={s.id}>
          {s.name || s.domain || s.id}
        </option>
      ))}
    </select>
  </div>
);

/** Small pill for status-like strings. */
export const Pill: React.FC<{ text: string; tone?: "green" | "gold" | "rose" | "stone" }> = ({
  text,
  tone = "stone",
}) => {
  const tones: Record<string, string> = {
    green: "bg-emerald-500/10 border-emerald-500/30 text-emerald-600",
    gold: "bg-[#C9A227]/10 border-[#C9A227]/40 text-[#A8842A]",
    rose: "bg-rose-500/10 border-rose-500/30 text-rose-600",
    stone: "bg-stone-500/10 border-stone-400/30 text-stone-500",
  };
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full border text-xs font-medium ${tones[tone]}`}>
      {text}
    </span>
  );
};

export const fmtDate = (v?: string) => {
  if (!v) return "—";
  const d = new Date(v);
  return isNaN(d.getTime()) ? v : d.toLocaleString();
};

export const pickTitle = (row: any): string =>
  row.title || row.name || row.keyword || row.question || row.headline || row.id || row.job_id || "Untitled";
