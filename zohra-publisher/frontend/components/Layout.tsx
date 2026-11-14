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
  ShieldAlert,
  MessageSquare,
  Image as ImageIcon,
  Menu,
  X,
  ChevronsLeft,
  ChevronsRight,
  Power,
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
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

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

  // Close the mobile menu whenever the page changes
  useEffect(() => {
    setMobileOpen(false);
  }, [router.pathname]);

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
  const currentLabel = navItems.find((i) => i.href === router.pathname)?.label || "Overview";

  const navList = (rail: boolean) => (
    <nav className="p-2 space-y-0.5 overflow-y-auto">
      {navItems.map((item) => {
        const active = router.pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            title={rail ? item.label : undefined}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors ${
              rail ? "justify-center" : ""
            } ${
              active
                ? "bg-emerald-600/15 text-emerald-700 border border-[#C9A227]/40 font-semibold"
                : "text-stone-500 hover:text-stone-800 hover:bg-white"
            }`}
          >
            {item.icon}
            {!rail && <span>{item.label}</span>}
          </Link>
        );
      })}
    </nav>
  );

  const brand = (rail: boolean, onToggle?: () => void) => (
    <div className="p-4 border-b border-[#E7DCB8]/80 flex items-center justify-between gap-2">
      <div className="flex items-center gap-2.5 min-w-0">
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center text-lg font-black shrink-0"
          style={{ background: "#123B2A", color: "#C9A227" }}
        >
          Z
        </div>
        {!rail && (
          <div className="min-w-0">
            <div className="text-sm font-bold tracking-widest text-[#123B2A] uppercase leading-tight">Zohra OS</div>
            <div className="text-[11px] text-stone-500 leading-tight">Autonomous Publishing</div>
          </div>
        )}
      </div>
      {onToggle && (
        <button
          onClick={onToggle}
          title={rail ? "Open the menu" : "Close the menu"}
          className="p-1.5 rounded-lg text-stone-500 hover:text-[#123B2A] hover:bg-white border border-transparent hover:border-[#E7DCB8] transition-colors shrink-0"
        >
          {rail ? <ChevronsRight className="w-4 h-4" /> : <ChevronsLeft className="w-4 h-4" />}
        </button>
      )}
    </div>
  );

  return (
    <div className="flex h-screen bg-[#FAF9F5] text-stone-700 antialiased overflow-hidden">
      {/* Desktop sidebar — collapsible to an icon rail */}
      <aside
        className={`hidden lg:flex flex-col justify-between border-r border-[#E7DCB8] bg-[#FAF9F5] shrink-0 transition-all duration-200 ${
          collapsed ? "w-[76px]" : "w-64"
        }`}
      >
        <div>
          {brand(collapsed, () => setCollapsed(!collapsed))}
          {navList(collapsed)}
        </div>
        <div className="p-3 border-t border-[#E7DCB8] text-[11px] text-stone-400 flex items-center justify-between">
          {!collapsed && <span>v1.0.0 Production</span>}
          <StatusBadge status={isPaused ? "PAUSED" : "HEALTHY"} size="sm" />
        </div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div className="fixed inset-0 bg-black/40" onClick={() => setMobileOpen(false)} />
          <aside className="relative w-64 max-w-[80vw] bg-[#FAF9F5] border-r border-[#E7DCB8] flex flex-col justify-between shadow-xl">
            <div>
              <div className="p-4 border-b border-[#E7DCB8]/80 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center text-lg font-black"
                    style={{ background: "#123B2A", color: "#C9A227" }}
                  >
                    Z
                  </div>
                  <div>
                    <div className="text-sm font-bold tracking-widest text-[#123B2A] uppercase leading-tight">Zohra OS</div>
                    <div className="text-[11px] text-stone-500 leading-tight">Autonomous Publishing</div>
                  </div>
                </div>
                <button
                  onClick={() => setMobileOpen(false)}
                  title="Close the menu"
                  className="p-1.5 rounded-lg text-stone-500 hover:text-[#123B2A] hover:bg-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              {navList(false)}
            </div>
            <div className="p-3 border-t border-[#E7DCB8] text-[11px] text-stone-400">v1.0.0 Production</div>
          </aside>
        </div>
      )}

      {/* Main column */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-14 border-b border-[#E7DCB8] bg-white/70 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setMobileOpen(true)}
              title="Open the menu"
              className="lg:hidden p-2 rounded-lg text-stone-600 hover:text-[#123B2A] hover:bg-[#F7F2E2]"
            >
              <Menu className="w-5 h-5" />
            </button>
            <span className="text-sm font-semibold text-[#123B2A] truncate">{currentLabel}</span>
            <span className="hidden md:inline text-xs px-2 py-0.5 bg-[#F7F2E2] border border-[#D8C78F] rounded-md text-stone-600">
              Mode: {autonomy?.cost_mode || "NORMAL"}
            </span>
            <span className="hidden md:inline text-xs text-stone-500">
              Spend today:{" "}
              <span className="font-mono text-stone-800">${autonomy?.spend_today_usd?.toFixed(2) || "0.00"}</span>
            </span>
          </div>

          {/* Autonomy ON / OFF switch — the master control */}
          <div className="flex items-center gap-2.5 shrink-0">
            <span className="hidden sm:flex items-center gap-1.5 text-xs font-semibold text-stone-600">
              <Power className={`w-3.5 h-3.5 ${isPaused ? "text-rose-500" : "text-emerald-600"}`} />
              Autonomy
            </span>
            <span
              className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${
                isPaused
                  ? "bg-rose-500/10 border-rose-500/30 text-rose-600"
                  : "bg-emerald-500/10 border-emerald-500/30 text-emerald-600"
              }`}
            >
              {isPaused ? "OFF" : "ON"}
            </span>
            <button
              role="switch"
              aria-checked={!isPaused}
              title={isPaused ? "Turn autonomy ON" : "Turn autonomy OFF"}
              onClick={() => {
                setModalAction(isPaused ? "RESUME" : "PAUSE");
                setModalOpen(true);
              }}
              className={`relative w-12 h-[26px] rounded-full transition-colors shrink-0 ${
                isPaused ? "bg-stone-300" : "bg-emerald-600"
              }`}
            >
              <span
                className={`absolute top-[3px] w-5 h-5 rounded-full bg-white shadow transition-all ${
                  isPaused ? "left-[3px]" : "left-[24px]"
                }`}
              />
            </button>
          </div>
        </header>

        {isPaused && (
          <div className="bg-rose-50 border-b border-rose-500/30 px-4 sm:px-6 py-2 flex items-center gap-2 text-xs text-rose-600">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>
              <span className="font-semibold">Autonomy is OFF.</span> Nothing will be discovered, written or published
              until you turn it back on.
            </span>
          </div>
        )}

        <main className="flex-1 overflow-y-auto p-4 sm:p-6">{children}</main>
      </div>

      <ConfirmModal
        isOpen={modalOpen}
        title={modalAction === "PAUSE" ? "Turn autonomy OFF?" : "Turn autonomy ON?"}
        description={
          modalAction === "PAUSE"
            ? "This stops all autonomous discovery, writing and publishing across every site, right away. Work already finished stays finished, and you can turn it back on at any time."
            : "This restarts autonomous discovery, writing and publishing, within each site's settings and your daily budget."
        }
        confirmLabel={modalAction === "PAUSE" ? "Turn OFF" : "Turn ON"}
        isDangerous={modalAction === "PAUSE"}
        defaultReason={modalAction === "PAUSE" ? "Turned off from the dashboard" : "Turned on from the dashboard"}
        onConfirm={handleAutonomyToggle}
        onCancel={() => setModalOpen(false)}
      />
    </div>
  );
};
