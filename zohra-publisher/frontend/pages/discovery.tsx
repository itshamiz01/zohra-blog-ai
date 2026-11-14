import React, { useCallback, useEffect, useState } from "react";
import { Compass, Play, Pause, Radar } from "lucide-react";
import { Layout } from "../components/Layout";
import { MetricCard } from "../components/ui/MetricCard";
import { PageHeader, StateLoading, StateError, Pill } from "../components/ui/PageBits";
import { api } from "../lib/api";

export default function DiscoveryPage() {
  const [status, setStatus] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [st, ss] = await Promise.all([api.getDiscoveryStatus(), api.getDiscoveryStats()]);
      setStatus(st);
      setStats(ss);
    } catch (e: any) {
      setError(e.message || "Could not load discovery data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (kind: "run" | "pause" | "resume") => {
    setBusy(true);
    setNote("");
    try {
      if (kind === "run") await api.runDiscovery();
      if (kind === "pause") await api.pauseDiscovery();
      if (kind === "resume") await api.resumeDiscovery();
      setNote(
        kind === "run" ? "Discovery run started." : kind === "pause" ? "Discovery paused." : "Discovery resumed."
      );
      load();
    } catch (e: any) {
      setNote(`That didn't work: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const enabled = status?.discovery_enabled;

  return (
    <Layout>
      <PageHeader
        title="Discovery"
        description="The engine that finds new topics and sources to write about. Run it, pause it, or check its health here."
        onRefresh={load}
        refreshing={loading}
      />
      {loading && !status ? (
        <StateLoading />
      ) : error ? (
        <StateError message={error} onRetry={load} />
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2 mb-6">
            <button
              onClick={() => act("run")}
              disabled={busy}
              className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold disabled:opacity-50"
            >
              <Radar className="w-4 h-4" /> Run discovery now
            </button>
            {enabled ? (
              <button
                onClick={() => act("pause")}
                disabled={busy}
                className="flex items-center gap-1.5 px-4 py-2 bg-white border border-[#D8C78F] hover:border-[#C9A227] text-[#123B2A] rounded-lg text-sm font-semibold disabled:opacity-50"
              >
                <Pause className="w-4 h-4" /> Pause discovery
              </button>
            ) : (
              <button
                onClick={() => act("resume")}
                disabled={busy}
                className="flex items-center gap-1.5 px-4 py-2 bg-white border border-[#D8C78F] hover:border-[#C9A227] text-[#123B2A] rounded-lg text-sm font-semibold disabled:opacity-50"
              >
                <Play className="w-4 h-4" /> Resume discovery
              </button>
            )}
            <span className="text-sm text-stone-500 flex items-center gap-2 ml-1">
              Status: <Pill text={enabled ? "Running" : "Stopped"} tone={enabled ? "green" : "rose"} />
            </span>
          </div>
          {note && <p className="text-sm text-emerald-600 -mt-3 mb-5">{note}</p>}

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            <MetricCard label="Sources" value={stats?.sources_total ?? 0} icon={<Compass className="w-4 h-4" />} />
            <MetricCard label="Healthy sources" value={stats?.sources_healthy ?? 0} variant="success" />
            <MetricCard label="Failing sources" value={stats?.sources_failing ?? 0} variant={stats?.sources_failing > 0 ? "critical" : "default"} />
            <MetricCard label="Found today" value={stats?.documents_discovered_today ?? 0} sublabel="new documents discovered" />
          </div>

          <div className="border border-[#E7DCB8] bg-white rounded-xl p-5">
            <h2 className="text-sm font-bold text-[#123B2A] mb-3">How discovery is set right now</h2>
            <dl className="grid sm:grid-cols-2 gap-x-8 gap-y-2 text-sm">
              <div className="flex justify-between border-b border-[#E7DCB8]/60 py-1.5">
                <dt className="text-stone-500">Discovery</dt>
                <dd className="font-medium text-stone-800">{status?.discovery_enabled ? "On" : "Off"}</dd>
              </div>
              <div className="flex justify-between border-b border-[#E7DCB8]/60 py-1.5">
                <dt className="text-stone-500">Autonomy link</dt>
                <dd className="font-medium text-stone-800">{status?.autonomy_enabled ? "On" : "Off"}</dd>
              </div>
              <div className="flex justify-between border-b border-[#E7DCB8]/60 py-1.5">
                <dt className="text-stone-500">Active sources</dt>
                <dd className="font-medium text-stone-800">{status?.active_sources ?? 0}</dd>
              </div>
              <div className="flex justify-between border-b border-[#E7DCB8]/60 py-1.5">
                <dt className="text-stone-500">Paused sources</dt>
                <dd className="font-medium text-stone-800">{status?.paused_sources ?? 0}</dd>
              </div>
              <div className="flex justify-between border-b border-[#E7DCB8]/60 py-1.5">
                <dt className="text-stone-500">Duplicates blocked today</dt>
                <dd className="font-medium text-stone-800">{stats?.exact_duplicates_blocked_today ?? 0}</dd>
              </div>
              <div className="flex justify-between border-b border-[#E7DCB8]/60 py-1.5">
                <dt className="text-stone-500">Maintenance mode</dt>
                <dd className="font-medium text-stone-800">{status?.maintenance_mode ? "On" : "Off"}</dd>
              </div>
            </dl>
            {(stats?.sources_total ?? 0) === 0 && (
              <p className="text-sm text-stone-500 mt-4">
                No discovery sources are connected yet, so runs will complete but find nothing. Sources are added in
                the backend configuration.
              </p>
            )}
          </div>
        </>
      )}
    </Layout>
  );
}
