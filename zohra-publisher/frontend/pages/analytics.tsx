import React, { useCallback, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import {
  PageHeader,
  StateLoading,
  StateError,
  StateEmpty,
  SimpleTable,
  SitePicker,
  pickTitle,
} from "../components/ui/PageBits";
import { api } from "../lib/api";

export default function AnalyticsPage() {
  const [sites, setSites] = useState<any[]>([]);
  const [siteId, setSiteId] = useState("");
  const [pages, setPages] = useState<any[]>([]);
  const [queries, setQueries] = useState<any[]>([]);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const list = (await api.listSites()) || [];
        setSites(list);
        if (list.length === 1) setSiteId(list[0].id);
      } catch {
        /* site list failing just leaves the picker empty */
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
      const [p, q, a] = await Promise.all([
        api.getAnalyticsPages(siteId).catch(() => []),
        api.getAnalyticsQueries(siteId).catch(() => []),
        api.getAnalyticsAnomalies(siteId).catch(() => []),
      ]);
      setPages(p || []);
      setQueries(q || []);
      setAnomalies(a || []);
    } catch (e: any) {
      setError(e.message || "Could not load analytics.");
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
        title="Analytics"
        description="How your published pages are doing in search — top pages, the searches that find them, and anything unusual."
        onRefresh={loadData}
        refreshing={loadingData}
      />
      {loading ? (
        <StateLoading />
      ) : sites.length === 0 ? (
        <StateEmpty
          title="No sites connected yet"
          hint="Analytics is per site. Once a site is connected and publishing, its search performance shows up here."
        />
      ) : (
        <>
          <SitePicker sites={sites} value={siteId} onChange={setSiteId} />
          {!siteId ? (
            <StateEmpty title="Pick a site above" hint="Choose which site's numbers you want to see." />
          ) : loadingData ? (
            <StateLoading />
          ) : error ? (
            <StateError message={error} onRetry={loadData} />
          ) : (
            <div className="space-y-8">
              <section>
                <h2 className="text-sm font-bold text-[#123B2A] mb-2">Top pages</h2>
                <SimpleTable
                  rows={pages}
                  emptyTitle="No page data yet"
                  emptyHint="Page performance appears after the site's analytics have synced."
                  columns={[
                    { label: "Page", render: (r) => r.url || r.page || pickTitle(r) },
                    { label: "Clicks", render: (r) => r.clicks ?? "—" },
                    { label: "Impressions", render: (r) => r.impressions ?? "—" },
                    { label: "Position", render: (r) => (r.position ? Number(r.position).toFixed(1) : "—") },
                  ]}
                />
              </section>
              <section>
                <h2 className="text-sm font-bold text-[#123B2A] mb-2">Searches that find you</h2>
                <SimpleTable
                  rows={queries}
                  emptyTitle="No search data yet"
                  columns={[
                    { label: "Search", render: (r) => r.query || r.keyword || pickTitle(r) },
                    { label: "Clicks", render: (r) => r.clicks ?? "—" },
                    { label: "Impressions", render: (r) => r.impressions ?? "—" },
                  ]}
                />
              </section>
              <section>
                <h2 className="text-sm font-bold text-[#123B2A] mb-2">Anything unusual</h2>
                <SimpleTable
                  rows={anomalies}
                  emptyTitle="Nothing unusual"
                  emptyHint="Sudden drops or spikes in a page's performance would be flagged here."
                  columns={[
                    { label: "What happened", render: (r) => r.title || r.description || r.type || pickTitle(r) },
                    { label: "Severity", render: (r) => r.severity || "—" },
                  ]}
                />
              </section>
            </div>
          )}
        </>
      )}
    </Layout>
  );
}
