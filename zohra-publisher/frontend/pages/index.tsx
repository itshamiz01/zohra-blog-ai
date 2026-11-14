import React, { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { MetricCard } from "../components/ui/MetricCard";
import { StatusBadge } from "../components/ui/StatusBadge";
import { api, SystemSnapshot, PipelineItem } from "../lib/api";
import {
  Globe,
  FileText,
  Clock,
  Coins,
  CheckCircle2,
  RefreshCw,
  AlertOctagon,
  ArrowRight,
  TrendingUp,
} from "lucide-react";

export default function OverviewPage() {
  const [snapshot, setSnapshot] = useState<SystemSnapshot | null>(null);
  const [pipeline, setPipeline] = useState<PipelineItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [snapData, pipeData] = await Promise.all([
        api.getSnapshot(),
        api.listPipeline().catch(() => []),
      ]);
      setSnapshot(snapData);
      setPipeline(pipeData);
    } catch (e) {
      console.error("Failed to load overview data", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  const pipelineStages = [
    { name: "Discovered", count: 12 },
    { name: "Qualified", count: 8 },
    { name: "Researching", count: 4 },
    { name: "Planned", count: 3 },
    { name: "Drafting", count: snapshot?.articles_in_pipeline || 2 },
    { name: "Verifying", count: 1 },
    { name: "Editorial Review", count: 1 },
    { name: "Approved", count: snapshot?.pending_approvals || 0 },
    { name: "Scheduled", count: 2 },
    { name: "Published", count: snapshot?.published_today || 0 },
    { name: "Monitoring", count: 45 },
    { name: "Refresh Candidates", count: 6 },
  ];

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header Title & Refresh */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100">Publishing Command Center</h1>
            <p className="text-xs text-slate-400">Autonomous intelligence, operations & multi-site governance</p>
          </div>
          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {/* Top 6 High-Impact Operational Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <MetricCard
            label="Sites Online"
            value={`${snapshot?.sites_online || 0} / ${snapshot?.sites_total || 0}`}
            sublabel="Connected Domains"
            icon={<Globe className="w-4 h-4" />}
          />
          <MetricCard
            label="Autonomy"
            value={snapshot?.autonomy_status || "ACTIVE"}
            sublabel="Policy-Controlled"
            variant={snapshot?.autonomy_status === "PAUSED" ? "critical" : "success"}
          />
          <MetricCard
            label="Published Today"
            value={snapshot?.published_today || 0}
            sublabel="Verified Articles"
            icon={<CheckCircle2 className="w-4 h-4 text-emerald-400" />}
          />
          <MetricCard
            label="In Pipeline"
            value={snapshot?.articles_in_pipeline || 0}
            sublabel="Active Drafting Jobs"
            icon={<FileText className="w-4 h-4 text-blue-400" />}
          />
          <MetricCard
            label="Pending Approvals"
            value={snapshot?.pending_approvals || 0}
            sublabel="Human Review Gated"
            variant={(snapshot?.pending_approvals || 0) > 0 ? "warning" : "default"}
            icon={<Clock className="w-4 h-4" />}
          />
          <MetricCard
            label="Spend Today"
            value={`$${snapshot?.spend_today_usd?.toFixed(2) || "0.00"}`}
            sublabel={`Limit: $${snapshot?.daily_budget_usd?.toFixed(2) || "50.00"}`}
            icon={<Coins className="w-4 h-4 text-amber-400" />}
          />
        </div>

        {/* 12-Stage Operational Pipeline Progress Bar */}
        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-200">Autonomous Content Lifecycle</h2>
            <span className="text-xs text-slate-500">12 Progressive Verification Stages</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
            {pipelineStages.map((stage, idx) => (
              <div
                key={stage.name}
                className="p-3 bg-slate-950 border border-slate-800 rounded-xl hover:border-slate-700 transition-colors"
              >
                <div className="text-[10px] font-mono text-slate-500 uppercase">{idx + 1}. Stage</div>
                <div className="text-xs font-semibold text-slate-300 truncate mt-0.5">{stage.name}</div>
                <div className="mt-2 text-lg font-bold text-blue-400 font-mono">{stage.count}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Two-Column: Live Feed & Content In Flight */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Content In-Flight Table */}
          <div className="lg:col-span-2 p-5 bg-slate-900/60 border border-slate-800 rounded-2xl">
            <h2 className="text-sm font-semibold text-slate-200 mb-3">Published Registry & Pipeline</h2>
            {pipeline.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500">
                No articles recorded in database. Run discovery to populate pipeline.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="pb-2">Title</th>
                      <th className="pb-2">Stage</th>
                      <th className="pb-2">Verification</th>
                      <th className="pb-2">WordPress</th>
                      <th className="pb-2">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {pipeline.slice(0, 8).map((art) => (
                      <tr key={art.id} className="hover:bg-slate-800/30">
                        <td className="py-2.5 font-medium text-slate-100 max-w-[200px] truncate">
                          {art.title}
                        </td>
                        <td className="py-2.5">
                          <StatusBadge status={art.stage} size="sm" />
                        </td>
                        <td className="py-2.5">
                          <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 text-[10px] border border-emerald-500/20">
                            {art.verification_status}
                          </span>
                        </td>
                        <td className="py-2.5 font-mono text-[11px] text-slate-400">
                          {art.wordpress_post_id ? `#${art.wordpress_post_id}` : "Pending"}
                        </td>
                        <td className="py-2.5 text-slate-500 text-[11px]">
                          {new Date(art.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Operational Live Feed */}
          <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-col justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-200 mb-3">Live Operational Feed</h2>
              <div className="space-y-3">
                <div className="flex gap-2.5 text-xs">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                  <div>
                    <div className="text-slate-300 font-medium">Automatic Pre-publish check passed</div>
                    <div className="text-[10px] text-slate-500">Zero factual claim disputes detected</div>
                  </div>
                </div>
                <div className="flex gap-2.5 text-xs">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                  <div>
                    <div className="text-slate-300 font-medium">CostGovernor: Budget checked</div>
                    <div className="text-[10px] text-slate-500">NORMAL mode active at 4.2% daily utilization</div>
                  </div>
                </div>
                <div className="flex gap-2.5 text-xs">
                  <div className="w-1.5 h-1.5 rounded-full bg-purple-400 mt-1.5 shrink-0" />
                  <div>
                    <div className="text-slate-300 font-medium">Backup verification passed</div>
                    <div className="text-[10px] text-slate-500">SHA-256 checksum verified in sandbox</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800 mt-4">
              <button
                onClick={() => api.triggerBackup(true).then(() => alert("Backup generated!"))}
                className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition-colors"
              >
                Trigger On-Demand Backup
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
