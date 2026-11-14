import React, { useCallback, useEffect, useState } from "react";
import { Check } from "lucide-react";
import { Layout } from "../components/Layout";
import { PageHeader, StateLoading, StateError, SimpleTable, Pill, fmtDate, pickTitle } from "../components/ui/PageBits";
import { api } from "../lib/api";

export const isPendingStatus = (s?: string) =>
  !!s && /pending|await|review|draft|queued/i.test(s) && !/published|approved|done|complete/i.test(s);

export default function PublishingPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busyId, setBusyId] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRows((await api.listPublications()) || []);
    } catch (e: any) {
      setError(e.message || "Could not load publishing jobs.");
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
        title="Publishing"
        description="Articles on their way out to your sites. Jobs waiting for a decision can be approved right here."
        onRefresh={load}
        refreshing={loading}
      />
      {note && <p className="text-sm text-emerald-600 mb-4">{note}</p>}
      {loading ? (
        <StateLoading />
      ) : error ? (
        <StateError message={error} onRetry={load} />
      ) : (
        <SimpleTable
          rows={rows}
          emptyTitle="Nothing publishing right now"
          emptyHint="When an article is queued to go live on a site, its job shows up here."
          columns={[
            { label: "Article", render: (r) => <span className="font-medium text-[#123B2A]">{pickTitle(r)}</span> },
            {
              label: "Status",
              render: (r) => (
                <Pill
                  text={r.status || "—"}
                  tone={/publish|approv|done|complete/i.test(r.status || "") ? "green" : isPendingStatus(r.status) ? "gold" : "stone"}
                />
              ),
            },
            { label: "Site", render: (r) => r.site_name || r.site_id || "—" },
            { label: "Created", render: (r) => fmtDate(r.created_at) },
            {
              label: "",
              render: (r) =>
                isPendingStatus(r.status) ? (
                  <button
                    onClick={() => approve(r)}
                    disabled={busyId === (r.id || r.job_id)}
                    className="flex items-center gap-1 px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-semibold disabled:opacity-50"
                  >
                    <Check className="w-3 h-3" /> Approve
                  </button>
                ) : null,
            },
          ]}
        />
      )}
    </Layout>
  );
}
