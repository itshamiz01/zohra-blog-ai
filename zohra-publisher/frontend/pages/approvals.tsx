import React, { useCallback, useEffect, useState } from "react";
import { Check, CheckSquare } from "lucide-react";
import { Layout } from "../components/Layout";
import { MetricCard } from "../components/ui/MetricCard";
import { PageHeader, StateLoading, StateError, SimpleTable, Pill, fmtDate, pickTitle } from "../components/ui/PageBits";
import { api } from "../lib/api";
import { isPendingStatus } from "./publishing";

export default function ApprovalsPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busyId, setBusyId] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const all = (await api.listPublications()) || [];
      setRows(all.filter((r: any) => isPendingStatus(r.status)));
    } catch (e: any) {
      setError(e.message || "Could not load approvals.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const approve = async (job: any) => {
    const id = job.id || job.job_id;
    setBusyId(id);
    setNote("");
    try {
      await api.approvePublication(id);
      setNote(`Approved: ${pickTitle(job)}`);
      load();
    } catch (e: any) {
      setNote(`Approve failed: ${e.message}`);
    } finally {
      setBusyId("");
    }
  };

  return (
    <Layout>
      <PageHeader
        title="Approvals"
        description="Everything waiting for your yes. Approving a publishing job lets it go live on its site."
        onRefresh={load}
        refreshing={loading}
      />
      {note && <p className="text-sm text-emerald-600 mb-4">{note}</p>}
      {loading ? (
        <StateLoading />
      ) : error ? (
        <StateError message={error} onRetry={load} />
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            <MetricCard
              label="Waiting for you"
              value={rows.length}
              icon={<CheckSquare className="w-4 h-4" />}
              variant={rows.length > 0 ? "warning" : "success"}
            />
          </div>
          <SimpleTable
            rows={rows}
            emptyTitle="Nothing waiting for approval"
            emptyHint="When an article is ready and needs your decision, it appears here."
            columns={[
              { label: "Article", render: (r) => <span className="font-medium text-[#123B2A]">{pickTitle(r)}</span> },
              { label: "Status", render: (r) => <Pill text={r.status || "—"} tone="gold" /> },
              { label: "Site", render: (r) => r.site_name || r.site_id || "—" },
              { label: "Created", render: (r) => fmtDate(r.created_at) },
              {
                label: "",
                render: (r) => (
                  <button
                    onClick={() => approve(r)}
                    disabled={busyId === (r.id || r.job_id)}
                    className="flex items-center gap-1 px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-semibold disabled:opacity-50"
                  >
                    <Check className="w-3 h-3" /> Approve
                  </button>
                ),
              },
            ]}
          />
        </>
      )}
    </Layout>
  );
}
