import React, { useCallback, useEffect, useState } from "react";
import { Brain } from "lucide-react";
import { Layout } from "../components/Layout";
import { MetricCard } from "../components/ui/MetricCard";
import { PageHeader, StateLoading, StateError, SimpleTable, fmtDate, pickTitle } from "../components/ui/PageBits";
import { api } from "../lib/api";

export default function LearningPage() {
  const [health, setHealth] = useState<any>(null);
  const [memories, setMemories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [h, m] = await Promise.all([api.getLearningHealth(), api.listLearningMemories().catch(() => [])]);
      setHealth(h);
      setMemories(m || []);
    } catch (e: any) {
      setError(e.message || "Could not load learning data.");
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
        title="Learning Engine"
        description="What the system has learned from past articles — lessons it reuses so each new article starts smarter."
        onRefresh={load}
        refreshing={loading}
      />
      {loading && !health ? (
        <StateLoading />
      ) : error ? (
        <StateError message={error} onRetry={load} />
      ) : (
        <>
          {health && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
              <MetricCard label="Engine" value={health.status || "—"} icon={<Brain className="w-4 h-4" />} variant="success" />
              <MetricCard label="Lessons stored" value={health.total_memories ?? 0} />
              <MetricCard label="Strong lessons" value={health.strong_memories ?? 0} sublabel="high-confidence, reused often" />
              <MetricCard label="Calibration" value={health.calibration_status || "—"} sublabel="how well its predictions match reality" />
            </div>
          )}
          <h2 className="text-sm font-bold text-[#123B2A] mb-2">Stored lessons</h2>
          <SimpleTable
            rows={memories}
            emptyTitle="No lessons stored yet"
            emptyHint="As articles are published and measured, the engine stores what it learns here."
            columns={[
              { label: "Lesson", render: (r) => r.content || r.summary || pickTitle(r) },
              { label: "Kind", render: (r) => r.memory_type || r.kind || r.category || "—" },
              { label: "Confidence", render: (r) => (r.confidence != null ? `${Math.round(Number(r.confidence) * 100)}%` : r.strength ?? "—") },
              { label: "Learned", render: (r) => fmtDate(r.created_at) },
            ]}
          />
        </>
      )}
    </Layout>
  );
}
