import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  LayoutDashboard,
  Activity,
  Compass,
  Sparkles,
  Search,
  FileText,
  Send,
  Globe,
  BarChart3,
  TrendingUp,
  FlaskConical,
  Brain,
  CheckSquare,
  Bell,
  Coins,
  Server,
  AlertTriangle,
  Play,
  Pause,
  ShieldAlert,
  MessageSquare,
  Image as ImageIcon,
} from "lucide-react";
import { api, AutonomyStatus } from "../lib/api";
import { StatusBadge } from "./ui/StatusBadge";
import { ConfirmModal } from "./ui/ConfirmModal";

const navItems = [
  { href: "/", label: "Overview", icon: <LayoutDashboard className="w-4 h-4" /> },
  { href: "/operations", label: "Live Operations", icon: <Activity className="w-4 h-4" /> },
  { href: "/reddit", label: "Reddit Intelligence", icon: <MessageSquare className="w-4 h-4" /> },
  { href: "/media", label: "Media Intelligence", icon: <ImageIcon className="w-4 h-4" /> },
  { href: "/discovery", label: "Discovery", icon: <Compass className="w-4 h-4" /> },
  { href: "/opportunities", label: "Opportunities", icon: <Sparkles className="w-4 h-4" /> },
  { href: "/research", label: "Research", icon: <Search className="w-4 h-4" /> },
  { href: "/content", label: "Content Pipeline", icon: <FileText className="w-4 h-4" /> },
  { href: "/publishing", label: "Publishing", icon: <Send className="w-4 h-4" /> },
  { href: "/sites", label: "Sites", icon: <Globe className="w-4 h-4" /> },
  { href: "/analytics", label: "Analytics", icon: <BarChart3 className="w-4 h-4" /> },
  { href: "/optimization", label: "Optimization", icon: <TrendingUp className="w-4 h-4" /> },
  { href: "/experiments", label: "Experiments", icon: <FlaskConical className="w-4 h-4" /> },
  { href: "/learning", label: "Learning Engine", icon: <Brain className="w-4 h-4" /> },
  { href: "/approvals", label: "Approvals", icon: <CheckSquare className="w-4 h-4" /> },
  { href: "/alerts", label: "Alerts", icon: <Bell className="w-4 h-4" /> },
  { href: "/costs", label: "Costs & Budgets", icon: <Coins className="w-4 h-4" /> },
  { href: "/system", label: "System Health", icon: <Server className="w-4 h-4" /> },
];


export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const router = useRouter();
  const [autonomy, setAutonomy] = useState<AutonomyStatus | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalAction, setModalAction] = useState<"PAUSE" | "RESUME">("PAUSE");

  const refreshStatus = async () => {
    try {
      const data = await api.getAutonomy();
      setAutonomy(data);
    } catch (e) {
      console.error("Failed to load autonomy status", e);
    }
  };

  useEffect(() => {
    refreshStatus();
    const interval = setInterval(refreshStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleAutonomyToggle = async (reason: string) => {
    try {
      if (modalAction === "PAUSE") {
        await api.pauseAutonomy(reason);
      } else {
        await api.resumeAutonomy(reason);
      }
      setModalOpen(false);
      refreshStatus();
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    }
  };

  const isPaused = autonomy?.autonomy_status === "PAUSED";

  return (
    <div className="flex h-screen bg-[#090d16] text-[#123B2A] antialiased overflow-hidden">
      {/* Sidebar Navigation */}
      <aside className="w-64 border-r border-[#E7DCB8] bg-[#FAF9F5]/60 backdrop-blur-md flex flex-col justify-between">
        <div>
          {/* Brand */}
          <div className="p-4 border-b border-[#E7DCB8]/80 flex items-center justify-between">
            <div>
              <div className="text-sm font-bold tracking-widest text-emerald-600 uppercase">ZOHRA OS</div>
              <div className="text-xs text-stone-500">Autonomous Publishing</div>
            </div>
            <StatusBadge status={isPaused ? "PAUSED" : "HEALTHY"} size="sm" />
          </div>

          {/* Navigation Links */}
          <nav className="p-2 space-y-0.5 overflow-y-auto max-h-[calc(100vh-140px)]">
            {navItems.map((item) => {
              const active = router.pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                    active
                      ? "bg-emerald-600/20 text-emerald-600 border border-[#C9A227]/30 font-semibold"
                      : "text-stone-500 hover:text-stone-800 hover:bg-white/60"
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User / Version footer */}
        <div className="p-3 border-t border-[#E7DCB8] text-xs text-stone-400 flex justify-between items-center">
          <span>v1.0.0 Production</span>
          <span className="font-mono">UTC</span>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Operational Header */}
        <header className="h-14 border-b border-[#E7DCB8] bg-[#FAF9F5]/40 backdrop-blur-md px-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-xs font-mono text-stone-500">Mode:</span>
            <span className="text-xs font-semibold px-2 py-0.5 bg-[#F7F2E2] border border-[#D8C78F] rounded-md text-stone-800">
              {autonomy?.cost_mode || "NORMAL"}
            </span>

            <span className="text-xs text-stone-400">|</span>

            <span className="text-xs text-stone-500">
              Spend Today: <span className="font-mono text-stone-800">${autonomy?.spend_today_usd?.toFixed(2) || "0.00"}</span>
            </span>
          </div>

          {/* Kill Switch Trigger */}
          <div className="flex items-center gap-3">
            {isPaused ? (
              <button
                onClick={() => {
                  setModalAction("RESUME");
                  setModalOpen(true);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-md transition-colors"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                Resume Autonomy
              </button>
            ) : (
              <button
                onClick={() => {
                  setModalAction("PAUSE");
                  setModalOpen(true);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow-md transition-colors"
              >
                <Pause className="w-3.5 h-3.5 fill-current" />
                Emergency Pause
              </button>
            )}
          </div>
        </header>

        {/* Global Pause Alert Banner */}
        {isPaused && (
          <div className="bg-rose-50/60 border-b border-rose-500/30 px-6 py-2 flex items-center justify-between text-xs text-rose-500">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
              <span className="font-semibold">GLOBAL AUTONOMY PAUSED:</span>
              <span>All autonomous publishing, drafting, and research actions are currently locked.</span>
            </div>
            <span className="text-stone-500 font-mono">Kill switch engaged</span>
          </div>
        )}

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>

      {/* Confirmation Modal for Kill Switch */}
      <ConfirmModal
        isOpen={modalOpen}
        title={modalAction === "PAUSE" ? "Activate Emergency Kill Switch" : "Resume Autonomous Publishing"}
        description={
          modalAction === "PAUSE"
            ? "This will immediately halt all autonomous discovery, drafting, and publishing workflows across all connected sites. Running database transactions and backups will complete safely."
            : "This will re-enable autonomous publishing workflows according to per-site risk policies and budget governor rules."
        }
        confirmLabel={modalAction === "PAUSE" ? "HALT ALL AUTONOMY" : "RESUME PUBLISHING"}
        isDangerous={modalAction === "PAUSE"}
        onConfirm={handleAutonomyToggle}
        onCancel={() => setModalOpen(false)}
      />
    </div>
  );
};
