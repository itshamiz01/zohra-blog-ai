import React, { useCallback, useEffect, useState } from "react";
import { Play, Square } from "lucide-react";
import { Layout } from "../components/Layout";
import {
  PageHeader,
  StateLoading,
  StateError,
  StateEmpty,
  SimpleTable,
  SitePicker,
  Pill,
  fmtDate,
  pickTitle,
} from "../components/ui/PageBits";
import { api } from "../lib/api";

export default function ExperimentsPage() {
  const [sites, setSites] = useState<any[]>([]);
  const [siteId, setSiteId] = useState("");
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busyId, setBusyId] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const list = (await api.listSites().catch(() => [])) || [];
        setSites(list);
        if (list.length === 1) setSiteId(list[0].id);
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
      setRows((await api.listExperiments(siteId)) || []);
    } catch (e: any) {
      setError(e.message || "Could not load experiments.");
    } finally {
      setLoadingData(false);
    }
  }, [siteId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const act = async (exp: any, kind: "start" | "stop") => {
    setBusyId(exp.id);
    setNote("");
    try {
      if (kind === "start") await api.startExperiment(exp.id);
      else await api.stopExperiment(exp.id);
      setNote(`Experiment ${kind === "start" ? "started" : "stopped"}: ${pickTitle(exp)}`);
      loadData();
    } catch (e: any) {
      setNote(`That didn't work: ${e.message}`);
    } finally {
      setBusyId("");
    }
  };

  const isRunning = (s?: string) => /run|active|live/i.test(s || "");

  return (
    <Layout>
      <PageHeader
        title="Experiments"
        description="Tests the engine runs to learn what works — for example, trying a new headline style and measuring the result."
        onRefresh={loadData}
        refreshing={loadingData}
      />
      {note && <p className="text-sm text-emerald-600 mb-4">{note}</p>}
      {loading ? (
        <StateLoading />
      ) : sites.length === 0 ? (
        <StateEmpty
          title="No sites connected yet"
          hint="Experiments run per site. Once a site is connected, its experiments can be started and stopped here."
        />
      ) : (
        <>
          <SitePicker sites={sites} value={siteId} onChange={setSiteId} />
          {!siteId ? (
            <StateEmpty title="Pick a site above" hint="Choose which site's experiments you want to see." />
          ) : loadingData ? (
            <StateLoading />
          ) : error ? (
            <StateError message={error} onRetry={loadData} />
          ) : (
            <SimpleTable
              rows={rows}
              emptyTitle="No experiments yet"
              emptyHint="Experiments the engine creates for this site will appear here."
              columns={[
                { label: "Experiment", render: (r) => <span className="font-medium text-[#123B2A]">{pickTitle(r)}</span> },
                { label: "Status", render: (r) => <Pill text={r.status || "—"} tone={isRunning(r.status) ? "green" : "stone"} /> },
                { label: "Created", render: (r) => fmtDate(r.created_at) },
                {
                  label: "",
                  render: (r) =>
                    isRunning(r.status) ? (
                      <button
                        onClick={() => act(r, "stop")}
                        disabled={busyId === r.id}
                        className="flex items-center gap-1 px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded-md text-xs font-semibold disabled:opacity-50"
                      >
                        <Square className="w-3 h-3" /> Stop
                      </button>
                    ) : (
                      <button
                        onClick={() => act(r, "start")}
                        disabled={busyId === r.id}
                        className="flex items-center gap-1 px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-semibold disabled:opacity-50"
                      >
                        <Play className="w-3 h-3" /> Start
                      </button>
                    ),
                },
              ]}
            />
          )}
        </>
      )}
    </Layout>
  );
}
