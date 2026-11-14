import React, { useCallback, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { PageHeader, StateLoading, StateError, SimpleTable, Pill, fmtDate, pickTitle } from "../components/ui/PageBits";
import { api } from "../lib/api";

export default function ResearchPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.listResearch();
      setRows(Array.isArray(data) ? data : (data as any)?.items || []);
    } catch (e: any) {
      setError(e.message || "Could not load research projects.");
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
        title="Research"
        description="Research projects the engine has opened — each one gathers sources and evidence before an article is written."
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
          emptyTitle="No research projects yet"
          emptyHint="When the engine starts researching a topic, the project shows up here."
          columns={[
            { label: "Project", render: (r) => <span className="font-medium text-[#123B2A]">{pickTitle(r)}</span> },
            { label: "Status", render: (r) => <Pill text={r.status || "—"} tone="gold" /> },
            { label: "Sources", render: (r) => r.source_count ?? r.sources_count ?? "—" },
            { label: "Started", render: (r) => fmtDate(r.created_at) },
            { label: "Updated", render: (r) => fmtDate(r.updated_at) },
          ]}
        />
      )}
    </Layout>
  );
}
