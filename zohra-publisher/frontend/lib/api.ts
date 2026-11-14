/**
 * Zohra Command Center — Strongly Typed API Client
 * Connects directly to FastAPI backend (/api/v1/...)
 */

export interface SystemSnapshot {
  autonomy_status: string;
  maintenance_mode: boolean;
  sites_total: number;
  sites_online: number;
  published_today: number;
  articles_in_pipeline: number;
  pending_approvals: number;
  spend_today_usd: number;
  daily_budget_usd: number;
  cost_mode: string;
  version: string;
  snapshot_timestamp: string;
}

export interface AutonomyStatus {
  autonomy_status: string;
  autonomy_mode: string;
  maintenance_mode: boolean;
  kill_switch_active: boolean;
  sites_online: number;
  spend_today_usd: number;
  cost_mode: string;
}

export interface AlertItem {
  id: string;
  site_id?: string;
  category: string;
  severity: "INFO" | "WARNING" | "HIGH" | "CRITICAL";
  title: string;
  message: string;
  source: string;
  status: "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
  occurrence_count: number;
  metadata_json: Record<string, any>;
  created_at: string;
}

export interface SiteItem {
  id: string;
  name: string;
  domain: string;
  niche: string;
  enabled: boolean;
  publishing_enabled: boolean;
  autonomous_publishing_enabled: boolean;
  max_posts_per_day: number;
}

export interface PipelineItem {
  id: string;
  article_id: string;
  title: string;
  site_id: string;
  stage: string;
  url?: string;
  verification_status: string;
  wordpress_post_id?: number;
  created_at: string;
  published_at?: string;
}

export interface BackupItem {
  backup_name: string;
  created_at: string;
  size_bytes: number;
  checksum_sha256: string;
  is_encrypted: boolean;
  verification_status: string;
}

export interface DeadLetterJob {
  job_id: string;
  task_name: string;
  site_id?: string;
  failed_at: string;
  retry_count: number;
  error_message: string;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("zohra_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  const payload = await response.json();
  if (!response.ok || !payload.success) {
    throw new Error(payload.error?.message || payload.detail || "API request failed");
  }

  return payload.data;
}

export const api = {
  // Snapshot & Autonomy
  getSnapshot: () => request<SystemSnapshot>("/api/v1/operations/snapshot"),
  getAutonomy: () => request<AutonomyStatus>("/api/v1/operations/autonomy"),
  pauseAutonomy: (reason: string) =>
    request<{ autonomy_status: string }>("/api/v1/operations/autonomy/pause", {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  resumeAutonomy: (reason: string) =>
    request<{ autonomy_status: string }>("/api/v1/operations/autonomy/resume", {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  setMaintenance: (enabled: boolean, reason: string) =>
    request<{ maintenance_mode: boolean }>("/api/v1/operations/maintenance", {
      method: "POST",
      body: JSON.stringify({ enabled, reason }),
    }),

  // Alerts
  listAlerts: (siteId?: string, severity?: string) => {
    const params = new URLSearchParams();
    if (siteId) params.append("site_id", siteId);
    if (severity) params.append("severity", severity);
    return request<AlertItem[]>(`/api/v1/alerts?${params.toString()}`);
  },
  acknowledgeAlert: (id: string) =>
    request<AlertItem>(`/api/v1/alerts/${id}/acknowledge`, { method: "POST" }),
  resolveAlert: (id: string) =>
    request<AlertItem>(`/api/v1/alerts/${id}/resolve`, { method: "POST" }),

  // Sites
  listSites: () => request<SiteItem[]>("/api/v1/sites"),

  // Pipeline & Lineage
  listPipeline: (siteId?: string) => {
    const params = siteId ? `?site_id=${siteId}` : "";
    return request<PipelineItem[]>(`/api/v1/operations/pipeline${params}`);
  },
  getLineage: (articleId: string) => request<any>(`/api/v1/operations/lineage/${articleId}`),

  // Backups
  listBackups: () => request<BackupItem[]>("/api/v1/backups"),
  triggerBackup: (encrypt: boolean = true) =>
    request<BackupItem>(`/api/v1/backups?encrypt=${encrypt}`, { method: "POST" }),
  verifyBackup: (filename: string) =>
    request<any>(`/api/v1/backups/${encodeURIComponent(filename)}/verify`, { method: "POST" }),
  testRestore: (filename: string) =>
    request<any>(`/api/v1/backups/${encodeURIComponent(filename)}/test-restore`, { method: "POST" }),

  // Dead Letter
  listDeadLetter: () => request<DeadLetterJob[]>("/api/v1/operations/dead-letter"),
  retryDeadLetter: (jobId: string) =>
    request<any>(`/api/v1/operations/dead-letter/${jobId}/retry`, { method: "POST" }),

  // Reddit Engine API
  getRedditStatus: () => request<any>("/api/v1/reddit/status"),
  getRedditOverview: (siteId: string) => request<any>(`/api/v1/reddit/overview?site_id=${siteId}`),
  listRedditQuestions: (siteId: string, subreddit?: string) => {
    const params = new URLSearchParams({ site_id: siteId });
    if (subreddit) params.append("subreddit", subreddit);
    return request<any[]>(`/api/v1/reddit/questions?${params.toString()}`);
  },
  listRedditClusters: (siteId: string) => request<any[]>(`/api/v1/reddit/clusters?site_id=${siteId}`),
  listRedditOpportunities: (siteId: string, minScore: number = 0.0) =>
    request<any[]>(`/api/v1/reddit/opportunities?site_id=${siteId}&min_score=${minScore}`),
  listRedditDrafts: (siteId: string) => request<any[]>(`/api/v1/reddit/drafts?site_id=${siteId}`),
  approveRedditDraft: (draftId: string, stripLink: boolean = false) =>
    request<any>(`/api/v1/reddit/drafts/${draftId}/approve?strip_link=${stripLink}`, { method: "POST" }),
  rejectRedditDraft: (draftId: string, reason: string) =>
    request<any>(`/api/v1/reddit/drafts/${draftId}/reject?reason=${encodeURIComponent(reason)}`, { method: "POST" }),
  listRedditPolicies: (siteId: string) => request<any[]>(`/api/v1/reddit/policies?site_id=${siteId}`),
  getRedditReferrals: (siteId: string, days: number = 30) =>
    request<any>(`/api/v1/reddit/referrals?site_id=${siteId}&days=${days}`),
  runRedditDryRun: (siteId: string, sampleTitle: string, sampleBody?: string, subreddit: string = "education") =>
    request<any>(
      `/api/v1/reddit/dry-run?site_id=${siteId}&sample_title=${encodeURIComponent(sampleTitle)}&subreddit=${subreddit}${
        sampleBody ? `&sample_body=${encodeURIComponent(sampleBody)}` : ""
      }`,
      { method: "POST" }
    ),
  triggerRedditScan: (siteId: string, limitPerSub: number = 10) =>
    request<any>(`/api/v1/reddit/scan?site_id=${siteId}&limit_per_sub=${limitPerSub}`, { method: "POST" }),

  // Media & Featured Image Engine
  getArticleFeaturedImage: (articleId: string) =>
    request<any>(`/api/v1/media/articles/${articleId}`),
  generateArticleFeaturedImage: (articleId: string, data: any) =>
    request<any>(`/api/v1/media/articles/${articleId}/generate`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  overrideArticleFeaturedImage: (articleId: string, data: any) =>
    request<any>(`/api/v1/media/articles/${articleId}/override`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  backfillArticleImages: (siteId: string, maxArticles: number = 10) =>
    request<any>(`/api/v1/media/backfill?site_id=${siteId}&max_articles=${maxArticles}`, {
      method: "POST",
    }),
  getBrandProfile: (siteId: string) =>
    request<any>(`/api/v1/media/brand-profiles/${siteId}`),
  updateBrandProfile: (siteId: string, data: any) =>
    request<any>(`/api/v1/media/brand-profiles/${siteId}`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

