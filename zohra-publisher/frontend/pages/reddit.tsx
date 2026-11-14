import React, { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { StatusBadge } from "../components/ui/StatusBadge";
import { api } from "../lib/api";
import {
  MessageSquare,
  Sparkles,
  Layers,
  ShieldCheck,
  CheckCircle,
  XCircle,
  Play,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  FileText,
  Search,
  CheckSquare,
  BarChart2,
  TrendingUp,
} from "lucide-react";

export default function RedditIntelligencePage() {
  const [activeTab, setActiveTab] = useState<"overview" | "questions" | "clusters" | "opportunities" | "drafts" | "policies" | "dryrun" | "referrals">("overview");
  const [status, setStatus] = useState<any>(null);
  const [overview, setOverview] = useState<any>(null);
  const [sites, setSites] = useState<any[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string>("");
  const [questions, setQuestions] = useState<any[]>([]);
  const [clusters, setClusters] = useState<any[]>([]);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [drafts, setDrafts] = useState<any[]>([]);
  const [policies, setPolicies] = useState<any[]>([]);
  const [referrals, setReferrals] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // Dry run form state
  const [dryRunTitle, setDryRunTitle] = useState("How can college students use ChatGPT for studying without relying on it completely?");
  const [dryRunBody, setDryRunBody] = useState("I want to learn effectively rather than just asking AI for answers to homework assignments.");
  const [dryRunSub, setDryRunSub] = useState("education");
  const [dryRunResult, setDryRunResult] = useState<any>(null);
  const [dryRunLoading, setDryRunLoading] = useState(false);

  // Initial load
  useEffect(() => {
    loadSitesAndStatus();
  }, []);

  const loadSitesAndStatus = async () => {
    try {
      setLoading(true);
      const [st, siteList] = await Promise.all([
        api.getRedditStatus().catch(() => null),
        api.listSites().catch(() => []),
      ]);
      setStatus(st);
      setSites(siteList);
      if (siteList.length > 0) {
        setSelectedSiteId(siteList[0].id);
        await loadSiteData(siteList[0].id);
      }
    } catch (e) {
      console.error("Failed loading Reddit intelligence status", e);
    } finally {
      setLoading(false);
    }
  };

  const loadSiteData = async (siteId: string) => {
    if (!siteId) return;
    try {
      const [ov, qs, cls, opps, drs, pols, refs] = await Promise.all([
        api.getRedditOverview(siteId).catch(() => null),
        api.listRedditQuestions(siteId).catch(() => []),
        api.listRedditClusters(siteId).catch(() => []),
        api.listRedditOpportunities(siteId).catch(() => []),
        api.listRedditDrafts(siteId).catch(() => []),
        api.listRedditPolicies(siteId).catch(() => []),
        api.getRedditReferrals(siteId).catch(() => null),
      ]);
      setOverview(ov);
      setQuestions(qs);
      setClusters(cls);
      setOpportunities(opps);
      setDrafts(drs);
      setPolicies(pols);
      setReferrals(refs);
    } catch (e) {
      console.error("Error loading site Reddit data", e);
    }
  };

  const handleSiteChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newSiteId = e.target.value;
    setSelectedSiteId(newSiteId);
    loadSiteData(newSiteId);
  };

  const handleScan = async () => {
    if (!selectedSiteId) return;
    try {
      setLoading(true);
      await api.triggerRedditScan(selectedSiteId);
      await loadSiteData(selectedSiteId);
    } catch (err: any) {
      alert(`Scan failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (draftId: string, stripLink: boolean = false) => {
    try {
      await api.approveRedditDraft(draftId, stripLink);
      await loadSiteData(selectedSiteId);
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    }
  };

  const handleReject = async (draftId: string) => {
    const reason = prompt("Enter reason for rejection:", "Does not fit community standards");
    if (!reason) return;
    try {
      await api.rejectRedditDraft(draftId, reason);
      await loadSiteData(selectedSiteId);
    } catch (err: any) {
      alert(`Rejection error: ${err.message}`);
    }
  };

  const executeDryRun = async () => {
    if (!selectedSiteId || !dryRunTitle) return;
    try {
      setDryRunLoading(true);
      const res = await api.runRedditDryRun(selectedSiteId, dryRunTitle, dryRunBody, dryRunSub);
      setDryRunResult(res);
    } catch (err: any) {
      alert(`Dry run simulation failed: ${err.message}`);
    } finally {
      setDryRunLoading(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-[#123B2A]">Reddit Opportunity & Referral Engine</h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100/60 border border-[#C9A227]/60 text-emerald-600 font-mono">
                {status?.autonomy_mode || "DISCOVERY_ONLY"}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-900/60 border border-amber-700/60 text-[#A8842A] font-mono">
                {status?.posting_enabled ? "LIVE_POSTING_ACTIVE" : "POSTING_DISABLED (DRY_RUN_SAFE)"}
              </span>
            </div>
            <p className="text-xs text-stone-500 mt-1">
              Real community questions → Thematic clusters → Research & Content opportunities → Useful answers → Permitted referrals
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={selectedSiteId}
              onChange={handleSiteChange}
              className="bg-white border border-[#D8C78F] text-xs text-stone-800 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#C9A227]"
            >
              {sites.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.name} ({site.domain})
                </option>
              ))}
            </select>

            <button
              onClick={handleScan}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              Run Scan Cycle
            </button>
          </div>
        </div>

        {/* High-level metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <div className="p-4 bg-white/60 border border-[#E7DCB8] rounded-xl">
            <div className="text-xs text-stone-500 font-medium">Discovered Questions</div>
            <div className="text-2xl font-bold text-[#123B2A] mt-1">{overview?.questions_total ?? 0}</div>
            <div className="text-[10px] text-stone-400 mt-0.5">Tracked subreddits</div>
          </div>
          <div className="p-4 bg-white/60 border border-[#E7DCB8] rounded-xl">
            <div className="text-xs text-stone-500 font-medium">Question Clusters</div>
            <div className="text-2xl font-bold text-emerald-600 mt-1">{overview?.clusters_total ?? 0}</div>
            <div className="text-[10px] text-stone-400 mt-0.5">Thematic umbrellas</div>
          </div>
          <div className="p-4 bg-white/60 border border-[#E7DCB8] rounded-xl">
            <div className="text-xs text-stone-500 font-medium">Opportunities Scored</div>
            <div className="text-2xl font-bold text-emerald-600 mt-1">{overview?.opportunities_total ?? 0}</div>
            <div className="text-[10px] text-emerald-500/80 mt-0.5">{overview?.qualified_opportunities ?? 0} qualified (score ≥65)</div>
          </div>
          <div className="p-4 bg-white/60 border border-[#E7DCB8] rounded-xl">
            <div className="text-xs text-stone-500 font-medium">Approval Queue</div>
            <div className="text-2xl font-bold text-[#A8842A] mt-1">{overview?.pending_drafts ?? 0}</div>
            <div className="text-[10px] text-stone-400 mt-0.5">Awaiting human signoff</div>
          </div>
          <div className="p-4 bg-white/60 border border-[#E7DCB8] rounded-xl">
            <div className="text-xs text-stone-500 font-medium">Published Answers</div>
            <div className="text-2xl font-bold text-emerald-600 mt-1">{overview?.published_responses ?? 0}</div>
            <div className="text-[10px] text-stone-400 mt-0.5">Live Reddit responses</div>
          </div>
          <div className="p-4 bg-white/60 border border-[#E7DCB8] rounded-xl">
            <div className="text-xs text-stone-500 font-medium">Referral Events</div>
            <div className="text-2xl font-bold text-cyan-400 mt-1">{overview?.referral_events_total ?? 0}</div>
            <div className="text-[10px] text-stone-400 mt-0.5">Tracked UTM sessions</div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-[#E7DCB8] text-xs font-medium space-x-2">
          {[
            { id: "overview", label: "Overview", icon: <TrendingUp className="w-3.5 h-3.5" /> },
            { id: "questions", label: `Discovered Questions (${questions.length})`, icon: <MessageSquare className="w-3.5 h-3.5" /> },
            { id: "clusters", label: `Clusters (${clusters.length})`, icon: <Layers className="w-3.5 h-3.5" /> },
            { id: "opportunities", label: `Opportunities (${opportunities.length})`, icon: <Sparkles className="w-3.5 h-3.5" /> },
            { id: "drafts", label: `Approval Queue (${drafts.length})`, icon: <CheckSquare className="w-3.5 h-3.5" /> },
            { id: "policies", label: `Community Policies (${policies.length})`, icon: <ShieldCheck className="w-3.5 h-3.5" /> },
            { id: "dryrun", label: "Dry-Run Simulator", icon: <Play className="w-3.5 h-3.5" /> },
            { id: "referrals", label: "Referral Analytics", icon: <BarChart2 className="w-3.5 h-3.5" /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-1.5 px-3 py-2 border-b-2 transition ${
                activeTab === tab.id
                  ? "border-[#C9A227] text-emerald-600"
                  : "border-transparent text-stone-500 hover:text-stone-800"
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab 1: Overview */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-5 bg-white/60 border border-[#E7DCB8] rounded-xl space-y-3">
                <h3 className="text-sm font-semibold text-stone-800 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  Engine Operational Gates & Safety Status
                </h3>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1.5 border-b border-[#E7DCB8]">
                    <span className="text-stone-500">Autonomy Mode</span>
                    <span className="font-mono text-emerald-600">{status?.autonomy_mode || "DISCOVERY_ONLY"}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-[#E7DCB8]">
                    <span className="text-stone-500">Autonomous Reddit Commenting</span>
                    <span className={`font-mono ${status?.posting_enabled ? "text-emerald-600" : "text-[#A8842A]"}`}>
                      {status?.posting_enabled ? "ENABLED" : "DISABLED (Operator Gate Required)"}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-[#E7DCB8]">
                    <span className="text-stone-500">Daily Comment Limit</span>
                    <span className="text-stone-800">{status?.daily_comment_limit || 5} per day</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-[#E7DCB8]">
                    <span className="text-stone-500">Minimum Opportunity Score</span>
                    <span className="text-stone-800">{status?.min_opportunity_score || 65.0} / 100</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-stone-500">Reddit OAuth Credentials</span>
                    <span className={`font-mono ${status?.oauth_configured ? "text-emerald-600" : "text-stone-500"}`}>
                      {status?.oauth_configured ? "CONFIGURED (Official API)" : "PUBLIC JSON DISCOVERY ONLY"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-5 bg-white/60 border border-[#E7DCB8] rounded-xl space-y-3">
                <h3 className="text-sm font-semibold text-stone-800 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-600" />
                  Monitored Communities & Niche Topics
                </h3>
                <p className="text-xs text-stone-500">
                  Targeted subreddits scanned for authentic learner and educator questions.
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {(status?.monitored_subreddits || ["artificial", "ChatGPT", "education", "edtech"]).map((sub: string) => (
                    <span key={sub} className="px-2.5 py-1 bg-[#F7F2E2] border border-[#D8C78F] text-xs rounded-lg text-stone-600">
                      r/{sub}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Discovered Questions */}
        {activeTab === "questions" && (
          <div className="bg-white/60 border border-[#E7DCB8] rounded-xl overflow-hidden">
            <div className="p-4 border-b border-[#E7DCB8] flex justify-between items-center">
              <div className="text-xs text-stone-500">
                Discovered questions normalized, classified and scored for site relevance.
              </div>
            </div>
            {questions.length === 0 ? (
              <div className="p-8 text-center text-xs text-stone-400">No questions discovered yet for this site. Run a scan cycle.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-stone-600">
                  <thead className="bg-[#FAF9F5]/80 text-stone-500 uppercase tracking-wider text-[10px] border-b border-[#E7DCB8]">
                    <tr>
                      <th className="px-4 py-3">Subreddit</th>
                      <th className="px-4 py-3">Question & Underlying Problem</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Intent</th>
                      <th className="px-4 py-3">Relevance</th>
                      <th className="px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E7DCB8]">
                    {questions.map((q) => (
                      <tr key={q.id} className="hover:bg-[#F7F2E2]/40">
                        <td className="px-4 py-3 font-mono text-emerald-600">r/{q.subreddit}</td>
                        <td className="px-4 py-3 max-w-md">
                          <div className="font-medium text-stone-800">{q.primary_question}</div>
                          {q.underlying_problem && (
                            <div className="text-[11px] text-stone-500 mt-0.5 line-clamp-1">{q.underlying_problem}</div>
                          )}
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-stone-600">{q.question_type}</td>
                        <td className="px-4 py-3 text-stone-500">{q.search_intent}</td>
                        <td className="px-4 py-3 font-semibold text-emerald-600">{q.relevance_score?.toFixed(1)}%</td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 bg-[#F7F2E2] text-[10px] rounded text-stone-600 uppercase">
                            {q.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Thematic Clusters */}
        {activeTab === "clusters" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {clusters.length === 0 ? (
              <div className="col-span-2 p-8 text-center text-xs text-stone-400 bg-white/60 border border-[#E7DCB8] rounded-xl">
                No clusters generated yet.
              </div>
            ) : (
              clusters.map((c) => (
                <div key={c.id} className="p-4 bg-white/60 border border-[#E7DCB8] rounded-xl space-y-2">
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-bold text-emerald-600">{c.cluster_name}</span>
                    <span className="px-2 py-0.5 bg-emerald-50/60 text-emerald-600 border border-[#D8C78F] text-[10px] rounded-full">
                      {c.question_count} questions
                    </span>
                  </div>
                  <div className="text-xs text-stone-600 font-medium">Canonical Problem: {c.canonical_problem}</div>
                  <div className="text-[11px] text-stone-500">Parent Topic: {c.parent_topic}</div>
                  {c.subtopics && c.subtopics.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {c.subtopics.map((sub: string, idx: number) => (
                        <span key={idx} className="px-2 py-0.5 bg-[#F7F2E2] text-[10px] text-stone-600 rounded">
                          {sub}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 4: Scored Opportunities */}
        {activeTab === "opportunities" && (
          <div className="space-y-3">
            {opportunities.length === 0 ? (
              <div className="p-8 text-center text-xs text-stone-400 bg-white/60 border border-[#E7DCB8] rounded-xl">
                No content opportunities scored yet.
              </div>
            ) : (
              opportunities.map((opp) => (
                <div key={opp.id} className="p-4 bg-white/60 border border-[#E7DCB8] rounded-xl flex flex-col md:flex-row justify-between gap-4">
                  <div className="space-y-1.5 max-w-2xl">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-stone-800">{opp.working_title}</span>
                      <span className="px-2 py-0.5 bg-[#F7F2E2] text-[10px] rounded font-mono text-emerald-600">
                        {opp.recommended_action}
                      </span>
                    </div>
                    <p className="text-xs text-stone-500">{opp.proposed_angle}</p>
                    <div className="text-[11px] text-stone-500 flex items-center gap-2">
                      <span>Target Keyword: <strong className="text-stone-600">{opp.target_keyword}</strong></span>
                      {opp.existing_article_match && (
                        <span className="text-[#A8842A]">Matched Existing Article: {opp.existing_article_match}</span>
                      )}
                    </div>
                  </div>
                  <div className="text-right flex flex-col justify-center items-end">
                    <div className="text-xs text-stone-500">Opportunity Score</div>
                    <div className="text-2xl font-bold text-emerald-600">{opp.opportunity_score?.toFixed(1)}</div>
                    <div className="text-[10px] text-stone-400">{opp.status}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 5: Approval Queue */}
        {activeTab === "drafts" && (
          <div className="space-y-4">
            <div className="p-3 bg-amber-950/40 border border-amber-800/60 rounded-xl text-xs text-amber-200 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#A8842A] flex-shrink-0" />
              <span>
                Safety Gate: Reddit responses will never be posted automatically without explicit operator review and approval.
              </span>
            </div>

            {drafts.length === 0 ? (
              <div className="p-8 text-center text-xs text-stone-400 bg-white/60 border border-[#E7DCB8] rounded-xl">
                Approval queue is currently empty.
              </div>
            ) : (
              drafts.map((d) => (
                <div key={d.id} className="p-5 bg-white/60 border border-[#E7DCB8] rounded-xl space-y-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs font-mono text-emerald-600">r/{d.subreddit}</span>
                      <span className="text-xs text-stone-400 ml-2">Post ID: {d.reddit_post_id}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 text-[10px] rounded font-medium ${d.rule_check_passed ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-500"}`}>
                        Rules: {d.rule_check_passed ? "PASS" : "BLOCK"}
                      </span>
                      <span className={`px-2 py-0.5 text-[10px] rounded font-medium ${d.anti_spam_passed ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-500"}`}>
                        Anti-Spam: {d.anti_spam_passed ? "PASS" : "FLAGGED"}
                      </span>
                    </div>
                  </div>

                  <div className="p-3 bg-[#FAF9F5] rounded-lg text-xs font-mono text-stone-800 whitespace-pre-wrap">
                    {d.response_body}
                  </div>

                  {d.proposed_link && (
                    <div className="text-xs text-stone-500 flex items-center gap-1.5">
                      <span>Proposed Link:</span>
                      <a href={d.proposed_link} target="_blank" rel="noreferrer" className="text-emerald-600 hover:underline flex items-center gap-1">
                        {d.proposed_link} <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}

                  <div className="flex justify-end gap-2 pt-2 border-t border-[#E7DCB8]">
                    <button
                      onClick={() => handleReject(d.id)}
                      className="px-3 py-1.5 bg-red-50/60 hover:bg-red-900 border border-red-800 text-red-200 text-xs rounded-lg transition"
                    >
                      Reject
                    </button>
                    {d.has_external_link && (
                      <button
                        onClick={() => handleApprove(d.id, true)}
                        className="px-3 py-1.5 bg-[#F7F2E2] hover:bg-[#EFE6C8] text-stone-800 text-xs rounded-lg transition"
                      >
                        Approve (Strip Link)
                      </button>
                    )}
                    <button
                      onClick={() => handleApprove(d.id, false)}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition"
                    >
                      Approve Response
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 6: Community Policies */}
        {activeTab === "policies" && (
          <div className="bg-white/60 border border-[#E7DCB8] rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-stone-600">
                <thead className="bg-[#FAF9F5]/80 text-stone-500 uppercase tracking-wider text-[10px] border-b border-[#E7DCB8]">
                  <tr>
                    <th className="px-4 py-3">Subreddit</th>
                    <th className="px-4 py-3">Posting Allowed</th>
                    <th className="px-4 py-3">Links Allowed</th>
                    <th className="px-4 py-3">Self-Promotion</th>
                    <th className="px-4 py-3">Confidence</th>
                    <th className="px-4 py-3">Last Verified</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E7DCB8]">
                  {policies.map((p) => (
                    <tr key={p.id} className="hover:bg-[#F7F2E2]/40">
                      <td className="px-4 py-3 font-mono text-emerald-600">r/{p.subreddit}</td>
                      <td className="px-4 py-3">{p.posting_allowed ? "YES" : "NO"}</td>
                      <td className="px-4 py-3 font-semibold">{p.external_links_allowed ? "YES (Permitted)" : "NO (Blocked)"}</td>
                      <td className="px-4 py-3">{p.self_promotion_allowed ? "ALLOWED" : "RESTRICTED"}</td>
                      <td className="px-4 py-3">{(p.confidence_level * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3 text-stone-400">{p.last_checked_at || "Never"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 7: Dry-Run Simulator */}
        {activeTab === "dryrun" && (
          <div className="space-y-4">
            <div className="p-4 bg-white/60 border border-[#E7DCB8] rounded-xl space-y-3">
              <h3 className="text-sm font-semibold text-stone-800">Interactive Dry-Run Engine Simulation</h3>
              <p className="text-xs text-stone-500">
                Simulates question detection, relevance calculation, website duplicate check, action determination, community rule verification, and response drafting without submitting anything to Reddit.
              </p>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-stone-500 mb-1">Reddit Question Title</label>
                  <input
                    type="text"
                    value={dryRunTitle}
                    onChange={(e) => setDryRunTitle(e.target.value)}
                    className="w-full bg-[#FAF9F5] border border-[#E7DCB8] text-xs text-stone-800 rounded-lg p-2.5 focus:outline-none focus:ring-1 focus:ring-[#C9A227]"
                  />
                </div>
                <div>
                  <label className="block text-xs text-stone-500 mb-1">Reddit Question Body (Optional)</label>
                  <textarea
                    rows={2}
                    value={dryRunBody}
                    onChange={(e) => setDryRunBody(e.target.value)}
                    className="w-full bg-[#FAF9F5] border border-[#E7DCB8] text-xs text-stone-800 rounded-lg p-2.5 focus:outline-none focus:ring-1 focus:ring-[#C9A227]"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <div>
                    <label className="block text-xs text-stone-500 mb-1">Subreddit</label>
                    <input
                      type="text"
                      value={dryRunSub}
                      onChange={(e) => setDryRunSub(e.target.value)}
                      className="bg-[#FAF9F5] border border-[#E7DCB8] text-xs text-stone-800 rounded-lg p-2 focus:outline-none focus:ring-1 focus:ring-[#C9A227]"
                    />
                  </div>
                  <button
                    onClick={executeDryRun}
                    disabled={dryRunLoading}
                    className="mt-5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
                  >
                    <Play className="w-3.5 h-3.5" />
                    {dryRunLoading ? "Evaluating..." : "Run Complete Dry Run"}
                  </button>
                </div>
              </div>
            </div>

            {dryRunResult && (
              <div className="p-5 bg-white/60 border border-[#E7DCB8] rounded-xl space-y-4">
                <div className="flex justify-between items-center border-b border-[#E7DCB8] pb-3">
                  <h4 className="text-sm font-bold text-stone-800">Simulation Results (Dry Run Safe)</h4>
                  <span className="text-xs px-2 py-0.5 rounded bg-emerald-50 border border-[#D8C78F] text-emerald-600 font-mono">
                    {dryRunResult.posting_gate_status}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-[#FAF9F5] rounded-lg">
                    <span className="text-stone-500">Classified Type:</span>
                    <div className="font-semibold text-stone-800 mt-0.5">{dryRunResult.question_type}</div>
                  </div>
                  <div className="p-3 bg-[#FAF9F5] rounded-lg">
                    <span className="text-stone-500">Opportunity Score:</span>
                    <div className="font-semibold text-emerald-600 mt-0.5">{dryRunResult.opportunity_score} / 100</div>
                  </div>
                  <div className="p-3 bg-[#FAF9F5] rounded-lg">
                    <span className="text-stone-500">Recommended Action:</span>
                    <div className="font-semibold text-emerald-600 mt-0.5">{dryRunResult.recommended_website_action}</div>
                  </div>
                </div>

                <div className="p-3 bg-[#FAF9F5] rounded-lg text-xs space-y-1">
                  <span className="text-stone-500">Proposed Website Article:</span>
                  <div className="font-semibold text-stone-800">{dryRunResult.proposed_article}</div>
                </div>

                <div className="p-3 bg-[#FAF9F5] rounded-lg text-xs space-y-1">
                  <span className="text-stone-500">Standalone Reddit Answer:</span>
                  <div className="text-stone-800 whitespace-pre-wrap">{dryRunResult.proposed_reddit_answer}</div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-[#FAF9F5] rounded-lg">
                    <span className="text-stone-500">Would Include Website Link:</span>
                    <div className={`font-semibold mt-0.5 ${dryRunResult.would_include_link ? "text-emerald-600" : "text-[#A8842A]"}`}>
                      {dryRunResult.would_include_link ? "YES" : "NO"}
                    </div>
                    <div className="text-[11px] text-stone-500 mt-1">{dryRunResult.link_inclusion_reason}</div>
                  </div>
                  <div className="p-3 bg-[#FAF9F5] rounded-lg">
                    <span className="text-stone-500">Would Publish Live Now:</span>
                    <div className="font-semibold text-red-400 mt-0.5">
                      {dryRunResult.would_publish ? "YES" : "NO (Live posting disabled for dry run safety)"}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 8: Referral Analytics */}
        {activeTab === "referrals" && (
          <div className="p-5 bg-white/60 border border-[#E7DCB8] rounded-xl space-y-3">
            <h3 className="text-sm font-semibold text-stone-800">Reddit Referral Performance</h3>
            <p className="text-xs text-stone-500">
              Legitimate attribution tracking via UTM campaign tags (utm_source=reddit, utm_medium=community).
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div className="p-3 bg-[#FAF9F5] rounded-lg">
                <span className="text-stone-500">Total Referrals (30d)</span>
                <div className="text-xl font-bold text-stone-800 mt-1">{referrals?.total_referrals ?? 0}</div>
              </div>
              <div className="p-3 bg-[#FAF9F5] rounded-lg">
                <span className="text-stone-500">Engaged Sessions</span>
                <div className="text-xl font-bold text-emerald-600 mt-1">{referrals?.engaged_sessions ?? 0}</div>
              </div>
              <div className="p-3 bg-[#FAF9F5] rounded-lg">
                <span className="text-stone-500">Conversions</span>
                <div className="text-xl font-bold text-emerald-600 mt-1">{referrals?.conversions ?? 0}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
