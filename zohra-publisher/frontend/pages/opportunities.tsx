import React, { useCallback, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { PageHeader, StateLoading, StateError, SimpleTable, Pill, fmtDate, pickTitle } from "../components/ui/PageBits";
import { api } from "../lib/api";

export default function OpportunitiesPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [mode, setMode] = useState<"all" | "top">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [list, watch] = await Promise.all([
        mode === "all" ? api.listOpportunities() : api.listTopOpportunities(),
        api.listWatchlist().catch(() => []),
      ]);
      setRows(list || []);
      setWatchlist(watch || []);
    } catch (e: any) {
      setError(e.message || "Could not load opportunities.");
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => {
    load();
  }, [load]);

  const scoreOf = (r: any) =>
    r.score ?? r.opportunity_score ?? r.total_score ?? null;

  return (
    <Layout>
      <PageHeader
        title="Opportunities"
        description="Topics the engine thinks are worth writing about, ranked by how promising they look."
        onRefresh={load}
        refreshing={loading}
      />
      <div className="flex gap-2 mb-5">
        {(["all", "top"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold border ${
              mode === m
                ? "bg-[#123B2A] text-white border-[#123B2A]"
                : "bg-white text-stone-600 border-[#D8C78F] hover:border-[#C9A227]"
            }`}
          >
            {m === "all" ? "All opportunities" : "Top opportunities"}
          </button>
        ))}
      </div>
      {loading ? (
        <StateLoading />
      ) : error ? (
        <StateError message={error} onRetry={load} />
      ) : (
        <>
          <SimpleTable
            rows={rows}
            emptyTitle="No opportunities yet"
            emptyHint="Opportunities appear here after discovery runs and finds promising topics."
            columns={[
              { label: "Topic", render: (r) => <span className="font-medium text-[#123B2A]">{pickTitle(r)}</span> },
              {
                label: "Score",
                render: (r) => {
                  const s = scoreOf(r);
                  return s === null ? "—" : <Pill text={String(Math.round(Number(s)))} tone={Number(s) >= 70 ? "green" : Number(s) >= 40 ? "gold" : "stone"} />;
                },
              },
              { label: "Status", render: (r) => r.status || "—" },
              { label: "Found", render: (r) => fmtDate(r.created_at || r.discovered_at) },
            ]}
          />
          {watchlist.length > 0 && (
            <>
              <h2 className="text-sm font-bold text-[#123B2A] mt-8 mb-2">Watchlist</h2>
              <SimpleTable
                rows={watchlist}
                emptyTitle="Watchlist is empty"
                columns={[
                  { label: "Topic", render: (r) => pickTitle(r) },
                  { label: "Status", render: (r) => r.status || "—" },
                  { label: "Added", render: (r) => fmtDate(r.created_at) },
                ]}
              />
            </>
          )}
        </>
      )}
    </Layout>
  );
}
