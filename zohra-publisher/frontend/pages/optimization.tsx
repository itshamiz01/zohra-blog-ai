import React, { useCallback, useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";
import { Layout } from "../components/Layout";
import { MetricCard } from "../components/ui/MetricCard";
import {
  PageHeader,
  StateLoading,
  StateError,
  StateEmpty,
  SimpleTable,
  SitePicker,
  Pill,
  pickTitle,
} from "../components/ui/PageBits";
import { api } from "../lib/api";

export default function OptimizationPage() {
  const [health, setHealth] = useState<any>(null);
  const [sites, setSites] = useState<any[]>([]);
  const [siteId, setSiteId] = useState("");
  const [candidates, setCandidates] = useState<any[]>([]);
  const [policies, setPolicies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [h, list] = await Promise.all([
          api.getOptimizationHealth().catch(() => null),
          api.listSites().catch(() => []),
        ]);
        setHealth(h);
        setSites(list || []);
        if (list && list.length === 1) setSiteId(list[0].id);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const loadData = useCallback(async () => {
    if (!siteId) return;
    setLoadingData(true);
    setError("");
    try {
      const [c, p] = await Promise.all([
        api.listOptimizationCandidates(siteId).catch(() => []),
        api.listOptimizationPolicies(siteId).catch(() => []),
      ]);
      setCandidates(c || []);
      setPolicies(p || []);
    } catch (e: any) {
      setError(e.message || "Could not load optimization data.");
    } finally {
      setLoadingData(false);
    }
  }, [siteId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <Layout>
      <PageHeader
        title="Optimization"
        description="Improvements the engine wants to make to existing articles — pages it can refresh to rank and earn better."
        onRefresh={loadData}
        refreshing={loadingData}
      />
      {loading ? (
        <StateLoading />
      ) : (
        <>
          {health && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
              <MetricCard label="Engine" value={health.status || "—"} icon={<TrendingUp className="w-4 h-4" />} variant="success" />
              <MetricCard label="Optimization" value={health.optimization_enabled ? "On" : "Off"} />
              <MetricCard label="Automatic changes" value={health.auto_optimization_enabled ? "On" : "Off"} sublabel="Off means changes wait for approval" />
              <MetricCard label="Pending approvals" value={health.pending_approvals ?? 0} variant={health.pending_approvals > 0 ? "warning" : "default"} />
            </div>
          )}
          {sites.length === 0 ? (
            <StateEmpty
              title="No sites connected yet"
              hint="Optimization works per site. Once a site is connected, its improvement candidates show up here."
            />
          ) : (
            <>
              <SitePicker sites={sites} value={siteId} onChange={setSiteId} />
              {!siteId ? (
                <StateEmpty title="Pick a site above" hint="Choose which site's improvements you want to see." />
              ) : loadingData ? (
                <StateLoading />
              ) : error ? (
                <StateError message={error} onRetry={loadData} />
              ) : (
                <div className="space-y-8">
                  <section>
                    <h2 className="text-sm font-bold text-[#123B2A] mb-2">Pages that could do better</h2>
                    <SimpleTable
                      rows={candidates}
                      emptyTitle="No candidates right now"
                      emptyHint="When the engine spots a page worth improving, it lists it here."
                      columns={[
                        { label: "Page", render: (r) => <span className="font-medium text-[#123B2A]">{r.url || pickTitle(r)}</span> },
                        { label: "Idea", render: (r) => r.recommendation || r.reason || r.type || "—" },
                        { label: "Status", render: (r) => <Pill text={r.status || "—"} tone="gold" /> },
                      ]}
                    />
                  </section>
                  <section>
                    <h2 className="text-sm font-bold text-[#123B2A] mb-2">Rules in effect</h2>
                    <SimpleTable
                      rows={policies}
                      emptyTitle="No policies set"
                      columns={[
                        { label: "Policy", render: (r) => pickTitle(r) },
                        { label: "Enabled", render: (r) => (r.enabled ? "Yes" : "No") },
                      ]}
                    />
                  </section>
                </div>
              )}
            </>
          )}
        </>
      )}
    </Layout>
  );
}
