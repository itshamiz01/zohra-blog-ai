import React, { useCallback, useEffect, useState } from "react";
import { Globe } from "lucide-react";
import { Layout } from "../components/Layout";
import { PageHeader, StateLoading, StateError, StateEmpty, Pill } from "../components/ui/PageBits";
import { api } from "../lib/api";

export default function SitesPage() {
  const [sites, setSites] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setSites((await api.listSites()) || []);
    } catch (e: any) {
      setError(e.message || "Could not load sites.");
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
        title="Sites"
        description="The websites Zohra writes and publishes for. Each site has its own topic, limits and on/off switches."
        onRefresh={load}
        refreshing={loading}
      />
      {loading ? (
        <StateLoading />
      ) : error ? (
        <StateError message={error} onRetry={load} />
      ) : sites.length === 0 ? (
        <StateEmpty
          title="No sites connected yet"
          hint="Once a WordPress site is connected in the backend, it appears here with its publishing switches and daily limits."
        />
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sites.map((s) => (
            <div key={s.id} className="border border-[#E7DCB8] bg-white rounded-xl p-5">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <Globe className="w-5 h-5 text-[#C9A227]" />
                  <div>
                    <div className="font-bold text-[#123B2A]">{s.name}</div>
                    <div className="text-xs text-stone-500">{s.domain}</div>
                  </div>
                </div>
                <Pill text={s.enabled ? "Enabled" : "Disabled"} tone={s.enabled ? "green" : "rose"} />
              </div>
              <dl className="mt-4 space-y-1.5 text-sm">
                <div className="flex justify-between">
                  <dt className="text-stone-500">Topic / niche</dt>
                  <dd className="font-medium text-stone-800">{s.niche || "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-stone-500">Publishing</dt>
                  <dd className="font-medium text-stone-800">{s.publishing_enabled ? "On" : "Off"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-stone-500">Automatic publishing</dt>
                  <dd className="font-medium text-stone-800">{s.autonomous_publishing_enabled ? "On" : "Off"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-stone-500">Max posts per day</dt>
                  <dd className="font-medium text-stone-800">{s.max_posts_per_day ?? "—"}</dd>
                </div>
              </dl>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
