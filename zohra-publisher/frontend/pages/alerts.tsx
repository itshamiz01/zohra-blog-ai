import React, { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { StatusBadge } from "../components/ui/StatusBadge";
import { api, AlertItem } from "../lib/api";
import { Bell, CheckCircle, Eye, AlertTriangle, RefreshCw } from "lucide-react";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadAlerts = async () => {
    try {
      const data = await api.listAlerts();
      setAlerts(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const handleAck = async (id: string) => {
    await api.acknowledgeAlert(id);
    loadAlerts();
  };

  const handleResolve = async (id: string) => {
    await api.resolveAlert(id);
    loadAlerts();
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100">Operational Alerts & Triage</h1>
            <p className="text-xs text-slate-400">Deduplicated operational events, quota warnings & system anomalies</p>
          </div>
          <button
            onClick={loadAlerts}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {alerts.length === 0 ? (
          <div className="p-12 text-center bg-slate-900/60 border border-slate-800 rounded-2xl">
            <CheckCircle className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            <div className="text-sm font-semibold text-slate-200">Zero Unresolved Alerts</div>
            <div className="text-xs text-slate-500 mt-1">All subsystems and site integrations are healthy.</div>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={alert.severity} size="sm" />
                    <span className="text-xs font-mono text-slate-400">[{alert.category}]</span>
                    <span className="text-sm font-semibold text-slate-100">{alert.title}</span>
                    {alert.occurrence_count > 1 && (
                      <span className="px-2 py-0.5 rounded-full bg-slate-800 text-[10px] text-amber-300 font-mono border border-slate-700">
                        {alert.occurrence_count}x occurrences
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-300">{alert.message}</p>
                  <div className="text-[10px] text-slate-500 font-mono">
                    Source: {alert.source} • Status: {alert.status} • {new Date(alert.created_at).toLocaleString()}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {alert.status === "OPEN" && (
                    <button
                      onClick={() => handleAck(alert.id)}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg border border-slate-700 font-medium"
                    >
                      Acknowledge
                    </button>
                  )}
                  <button
                    onClick={() => handleResolve(alert.id)}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs rounded-lg font-medium"
                  >
                    Resolve
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
