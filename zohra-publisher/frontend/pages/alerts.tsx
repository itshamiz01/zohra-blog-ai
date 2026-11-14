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
            <h1 className="text-xl font-bold tracking-tight text-[#123B2A]">Operational Alerts & Triage</h1>
            <p className="text-xs text-stone-500">Deduplicated operational events, quota warnings & system anomalies</p>
          </div>
          <button
            onClick={loadAlerts}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#F7F2E2] hover:bg-[#EFE6C8] text-stone-800 rounded-lg text-xs font-medium border border-[#D8C78F]"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {alerts.length === 0 ? (
          <div className="p-12 text-center bg-white/60 border border-[#E7DCB8] rounded-2xl">
            <CheckCircle className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
            <div className="text-sm font-semibold text-stone-800">Zero Unresolved Alerts</div>
            <div className="text-xs text-stone-400 mt-1">All subsystems and site integrations are healthy.</div>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="p-4 bg-white/60 border border-[#E7DCB8] rounded-xl flex items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={alert.severity} size="sm" />
                    <span className="text-xs font-mono text-stone-500">[{alert.category}]</span>
                    <span className="text-sm font-semibold text-[#123B2A]">{alert.title}</span>
                    {alert.occurrence_count > 1 && (
                      <span className="px-2 py-0.5 rounded-full bg-[#F7F2E2] text-[10px] text-[#A8842A] font-mono border border-[#D8C78F]">
                        {alert.occurrence_count}x occurrences
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-stone-600">{alert.message}</p>
                  <div className="text-[10px] text-stone-400 font-mono">
                    Source: {alert.source} • Status: {alert.status} • {new Date(alert.created_at).toLocaleString()}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {alert.status === "OPEN" && (
                    <button
                      onClick={() => handleAck(alert.id)}
                      className="px-3 py-1.5 bg-[#F7F2E2] hover:bg-[#EFE6C8] text-stone-800 text-xs rounded-lg border border-[#D8C78F] font-medium"
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
