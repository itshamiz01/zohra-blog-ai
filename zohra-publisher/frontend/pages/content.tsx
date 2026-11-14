import React, { useCallback, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { PageHeader, StateLoading, StateError, SimpleTable, Pill, fmtDate, pickTitle } from "../components/ui/PageBits";
import { api } from "../lib/api";

export default function ContentPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.listDrafts();
      setRows(Array.isArray(data) ? data : (data as any)?.items || []);
    } catch (e: any) {
      setError(e.message || "Could not load drafts.");
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
        title="Content Pipeline"
        description="Articles being written right now — drafts move from research to writing to review before they are published."
        onRefresh={load}
        refreshing={loading}
      />
      {loading ? (
        <StateLoading />
      ) : error ? (
        <StateError message={error} onRetry={load} />
      ) : (
        <SimpleTable
          rows={rows}
          emptyTitle="No drafts in progress"
          emptyHint="Drafts appear here when the engine starts writing an article."
          columns={[
            { label: "Draft", render: (r) => <span className="font-medium text-[#123B2A]">{pickTitle(r)}</span> },
            { label: "Stage", render: (r) => <Pill text={r.stage || r.status || "—"} tone="gold" /> },
            { label: "Site", render: (r) => r.site_name || r.site_id || "—" },
            { label: "Updated", render: (r) => fmtDate(r.updated_at || r.created_at) },
          ]}
        />
      )}
    </Layout>
  );
}
