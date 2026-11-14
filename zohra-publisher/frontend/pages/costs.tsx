import React, { useCallback, useEffect, useState } from "react";
import { Coins } from "lucide-react";
import { Layout } from "../components/Layout";
import { MetricCard } from "../components/ui/MetricCard";
import { PageHeader, StateLoading, StateError } from "../components/ui/PageBits";
import { api } from "../lib/api";

const money = (v: any) => `$${Number(v || 0).toFixed(2)}`;

const BudgetBar: React.FC<{ label: string; spent: number; budget: number }> = ({ label, spent, budget }) => {
  const pct = budget > 0 ? Math.min(100, (spent / budget) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-stone-600">{label}</span>
        <span className="font-medium text-stone-800">
          {money(spent)} <span className="text-stone-400">of</span> {money(budget)}
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-[#F7F2E2] border border-[#E7DCB8] overflow-hidden">
        <div
          className={`h-full rounded-full ${pct >= 90 ? "bg-rose-500" : pct >= 70 ? "bg-[#C9A227]" : "bg-emerald-600"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="text-xs text-stone-400 mt-1">{pct.toFixed(0)}% used</div>
    </div>
  );
};

export default function CostsPage() {
  const [costs, setCosts] = useState<any>(null);
  const [snapshot, setSnapshot] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [c, s] = await Promise.all([api.getCosts(), api.getSnapshot().catch(() => null)]);
      setCosts(c);
      setSnapshot(s);
    } catch (e: any) {
      setError(e.message || "Could not load cost data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Layout>
      <PageHeader
        title="Costs & Budgets"
        description="What the AI has spent today and this month, against the limits you set. The engine slows down before it can overspend."
        onRefresh={load}
        refreshing={loading}
      />
      {loading && !costs ? (
        <StateLoading />
      ) : error ? (
        <StateError message={error} onRetry={load} />
      ) : costs ? (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            <MetricCard label="Spent today" value={money(costs.daily_total)} icon={<Coins className="w-4 h-4" />} />
            <MetricCard label="Left today" value={money(costs.daily_remaining)} variant="success" />
            <MetricCard label="Spent this month" value={money(costs.monthly_total)} />
            <MetricCard label="Left this month" value={money(costs.monthly_remaining)} variant="success" />
          </div>
          <div className="border border-[#E7DCB8] bg-white rounded-xl p-5 space-y-6 max-w-2xl">
            <BudgetBar label="Daily budget" spent={Number(costs.daily_total || 0)} budget={Number(costs.daily_budget || 0)} />
            <BudgetBar label="Monthly budget" spent={Number(costs.monthly_total || 0)} budget={Number(costs.monthly_budget || 0)} />
            {snapshot && (
              <p className="text-sm text-stone-500">
                Cost mode right now: <span className="font-semibold text-stone-800">{snapshot.cost_mode}</span> — in
                economy modes the engine picks cheaper models and slows non-urgent work.
              </p>
            )}
          </div>
        </>
      ) : null}
    </Layout>
  );
}
