import React, { useCallback, useEffect, useState } from "react";
import { Activity, FileText, Globe, Wallet, CheckSquare, RotateCcw } from "lucide-react";
import { Layout } from "../components/Layout";
import { MetricCard } from "../components/ui/MetricCard";
import { PageHeader, StateLoading, StateError, SimpleTable, Pill, fmtDate } from "../components/ui/PageBits";
import { api } from "../lib/api";

export default function OperationsPage() {
  const [snapshot, setSnapshot] = useState<any>(null);
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [deadLetter, setDeadLetter] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [snap, pipe, dead] = await Promise.all([
        api.getSnapshot(),
        api.listPipeline().catch(() => []),
        api.listDeadLetter().catch(() => []),
      ]);
      setSnapshot(snap);
      setPipeline(pipe || []);
      setDeadLetter(dead || []);
    } catch (e: any) {
      setError(e.message || "Could not load operations data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const retry = async (jobId: string) => {
    try {
      await api.retryDeadLetter(jobId);
      setNote("Retry queued for that job.");
      load();
    } catch (e: any) {
      setNote(`Retry failed: ${e.message}`);
    }
  };

  return (
    <Layout>
      <PageHeader
        title="Live Operations"
        description="What the system is doing right now — articles in the pipeline and any jobs that failed."
        onRefresh={load}
        refreshing={loading}
      />
      {loading && !snapshot ? (
        <StateLoading />
      ) : error ? (
        <StateError message={error} onRetry={load} />
      ) : (
        <>
          {snapshot && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
              <MetricCard label="Sites online" value={`${snapshot.sites_online} / ${snapshot.sites_total}`} icon={<Globe className="w-4 h-4" />} />
              <MetricCard label="Published today" value={snapshot.published_today} icon={<FileText className="w-4 h-4" />} variant="success" />
              <MetricCard label="In the pipeline" value={snapshot.articles_in_pipeline} icon={<Activity className="w-4 h-4" />} />
              <MetricCard label="Waiting for approval" value={snapshot.pending_approvals} icon={<CheckSquare className="w-4 h-4" />} variant={snapshot.pending_approvals > 0 ? "warning" : "default"} />
            </div>
          )}

          <h2 className="text-sm font-bold text-[#123B2A] mb-2">Article pipeline</h2>
          <div className="mb-8">
            <SimpleTable
              rows={pipeline}
              emptyTitle="The pipeline is empty"
              emptyHint="When articles are being written or published, each step shows up here."
              columns={[
                { label: "Article", render: (r) => r.title || r.article_id || "Untitled" },
                { label: "Stage", render: (r) => <Pill text={r.stage || "—"} tone="gold" /> },
                { label: "Check", render: (r) => r.verification_status || "—" },
                { label: "Started", render: (r) => fmtDate(r.created_at) },
              ]}
            />
          </div>

          <h2 className="text-sm font-bold text-[#123B2A] mb-2">Failed jobs (dead letter)</h2>
          {note && <p className="text-xs text-emerald-600 mb-2">{note}</p>}
          <SimpleTable
            rows={deadLetter}
            emptyTitle="No failed jobs"
            emptyHint="If a background job fails for good, it lands here so you can retry it."
            columns={[
              { label: "Job", render: (r) => r.task_name || r.job_id },
              { label: "Failed at", render: (r) => fmtDate(r.failed_at) },
              { label: "Retries", render: (r) => r.retry_count ?? 0 },
              { label: "Error", render: (r) => <span className="text-rose-600">{r.error_message || "—"}</span> },
              {
                label: "",
                render: (r) => (
                  <button
                    onClick={() => retry(r.job_id)}
                    className="flex items-center gap-1 px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-semibold"
                  >
                    <RotateCcw className="w-3 h-3" /> Retry
                  </button>
                ),
              },
            ]}
          />
          {snapshot && (
            <p className="text-xs text-stone-400 mt-6 flex items-center gap-1.5">
              <Wallet className="w-3.5 h-3.5" /> Spend today: ${Number(snapshot.spend_today_usd || 0).toFixed(2)} of $
              {Number(snapshot.daily_budget_usd || 0).toFixed(2)} daily budget · Mode: {snapshot.cost_mode}
            </p>
          )}
        </>
      )}
    </Layout>
  );
}
