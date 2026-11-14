import React, { useState } from "react";
import { Layout } from "../components/Layout";
import { MetricCard } from "../components/ui/MetricCard";
import { StatusBadge } from "../components/ui/StatusBadge";
import {
  Image as ImageIcon,
  Sparkles,
  RefreshCw,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Eye,
  ShieldCheck,
  Zap,
  ArrowRight,
  Maximize2,
  FileCheck,
} from "lucide-react";

export default function MediaIntelligencePage() {
  const [activeTab, setActiveTab] = useState<"overview" | "studio" | "brand" | "backfill">("overview");

  // Studio simulator state
  const [simTitle, setSimTitle] = useState("How High School Students Can Use ChatGPT for Essay Outlining Without Plagiarizing");
  const [simTopic, setSimTopic] = useState("AI in Education & Critical Thinking");
  const [simCategory, setSimCategory] = useState("Education");
  const [simLoading, setSimLoading] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);

  // Brand profile state
  const [brandStyle, setBrandStyle] = useState("Modern clean editorial, authentic, balanced depth and natural light");
  const [brandComposition, setBrandComposition] = useState("Rule of thirds, clear focal subject, uncluttered background");
  const [brandMood, setBrandMood] = useState("Professional, intelligent, inviting, authentic");
  const [photoPref, setPhotoPref] = useState(0.7);
  const [textPolicy, setTextPolicy] = useState("NO_TEXT");
  const [savedNotice, setSavedNotice] = useState(false);

  const runSimulation = () => {
    setSimLoading(true);
    setTimeout(() => {
      setSimResult({
        visual_analysis: {
          primary_subject: "A student thoughtfully using digital assistive outlines alongside handwritten notes",
          visualizable_elements: [
            "Clean study desk with organized notebooks and tablet",
            "Focused student demonstrating critical thinking and engagement",
            "Natural morning window lighting across workspace",
          ],
          things_to_avoid: [
            "Floating generic robots looking at laptop",
            "Baked-in headlines or typography in image",
            "Distorted hands or unnatural facial anatomy",
          ],
        },
        concept: {
          image_type: "EDITORIAL_PHOTOGRAPHY",
          subject: "An authentic, focused student thoughtfully engaged with essay outlining tools",
          environment: "A contemporary sunlit study space with warm wood surfaces and books",
          composition: "Rule of thirds, shallow depth of field with soft background bokeh",
          lighting: "Soft natural window daylight coming from the left",
          style: "High-end editorial lifestyle photography, 35mm lens feel, natural color grading",
        },
        prompt: "A high-resolution editorial photograph: An authentic, focused student thoughtfully engaged with essay outlining tools. Setting: A contemporary sunlit study space with warm wood surfaces and books. Lighting: Soft natural window daylight. Composition: Rule of thirds. Constraints: DO NOT include any text, typography, letters, headlines, words, watermarks, or logos in the image; no fake interface popups; no distorted hands.",
        validation: {
          passed: true,
          score: 89.5,
          subject_relevance: 92.0,
          topic_relevance: 90.0,
          visual_clarity: 88.0,
          brand_suitability: 91.0,
          safety_score: 98.0,
          failure_reasons: [],
        },
        optimization: {
          filename: "how-high-school-students-can-use-chatgpt-for-essay.webp",
          dimensions: "1536 × 864 (16:9 Aspect Ratio)",
          mime_type: "image/webp",
          file_size_bytes: "142.8 KB (Compressed from 2.4 MB PNG)",
          alt_text: "Editorial visual representing student essay outlining with digital assistance",
          content_hash: "a4f89d37c8e2b01289cf00921471de89f41bce8923a10984decf8109312adbc8",
          responsive_variants: [
            { label: "1536w", dimensions: "1536 × 864", size: "142.8 KB" },
            { label: "1200w", dimensions: "1200 × 675", size: "94.2 KB" },
            { label: "768w", dimensions: "768 × 432", size: "48.1 KB" },
            { label: "480w", dimensions: "480 × 270", size: "22.5 KB" },
          ],
        },
      });
      setSimLoading(false);
    }, 900);
  };

  const handleSaveBrand = () => {
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2500);
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-100">Media & Visual Intelligence</h1>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                ACTIVE • DALL-E-3 / WEBP
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Autonomous article featured image generation, semantic validation, Pillow WebP compression & SEO packaging
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("studio")}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium shadow-sm transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Test Image Studio
            </button>
          </div>
        </div>

        {/* Top Operational Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            label="Media Pipeline"
            value="AUTOMATIC"
            sublabel="Attached on Article Publish"
            icon={<Zap className="w-4 h-4 text-amber-400" />}
          />
          <MetricCard
            label="Format & Ratio"
            value="WebP • 16:9"
            sublabel="1536 × 864 Web Ready"
            icon={<ImageIcon className="w-4 h-4 text-blue-400" />}
          />
          <MetricCard
            label="Validation Pass Rate"
            value="96.4%"
            sublabel="Bounded Retry Guard"
            icon={<ShieldCheck className="w-4 h-4 text-emerald-400" />}
          />
          <MetricCard
            label="Avg. Compression"
            value="-82.6%"
            sublabel="Responsive WebP Variants"
            icon={<Layers className="w-4 h-4 text-purple-400" />}
          />
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 space-x-6 text-xs font-medium">
          <button
            onClick={() => setActiveTab("overview")}
            className={`pb-2.5 transition-colors border-b-2 ${
              activeTab === "overview"
                ? "border-blue-500 text-blue-400 font-semibold"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Overview & Specifications
          </button>
          <button
            onClick={() => setActiveTab("studio")}
            className={`pb-2.5 transition-colors border-b-2 ${
              activeTab === "studio"
                ? "border-blue-500 text-blue-400 font-semibold"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Visual Concept Studio
          </button>
          <button
            onClick={() => setActiveTab("brand")}
            className={`pb-2.5 transition-colors border-b-2 ${
              activeTab === "brand"
                ? "border-blue-500 text-blue-400 font-semibold"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Site Brand & Style Policy
          </button>
          <button
            onClick={() => setActiveTab("backfill")}
            className={`pb-2.5 transition-colors border-b-2 ${
              activeTab === "backfill"
                ? "border-blue-500 text-blue-400 font-semibold"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Historical Backfill
          </button>
        </div>

        {/* Tab: Overview */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Pipeline Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-blue-400" />
                    Automated Media Lifecycle
                  </h3>
                  <StatusBadge status="SUCCESS" size="sm" />
                </div>
                <div className="space-y-3 text-xs text-slate-300">
                  <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                    <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-[10px] shrink-0">1</span>
                    <div>
                      <strong className="text-slate-100">Article Visual Analysis:</strong> Understands core meaning, primary subject, audience, and generates strict negative guardrails (e.g. no floating robots, no generic blue matrix).
                    </div>
                  </div>
                  <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                    <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-[10px] shrink-0">2</span>
                    <div>
                      <strong className="text-slate-100">Structured Concept & DALL-E-3 Prompt:</strong> Determines aesthetic style (editorial photography, tech visualization) and enforces <em>strict NO TEXT overlay</em> rule.
                    </div>
                  </div>
                  <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                    <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-[10px] shrink-0">3</span>
                    <div>
                      <strong className="text-slate-100">Relevance Validation & Bounded Retry:</strong> Scores image on subject relevance, visual clarity, and safety. If failed, executes targeted prompt repair (max 2 regenerations).
                    </div>
                  </div>
                  <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                    <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-[10px] shrink-0">4</span>
                    <div>
                      <strong className="text-slate-100">WebP Compression & Responsive Variants:</strong> Pillow encodes 1536w, 1200w, 768w, 480w variants, generates SHA-256 hash, and descriptive non-keyword-stuffed ALT text.
                    </div>
                  </div>
                  <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                    <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-[10px] shrink-0">5</span>
                    <div>
                      <strong className="text-slate-100">Publishing Integration:</strong> Attached directly to WordPress media endpoint (`featured_media`) and included in Heavenly Insights API payload and responsive HTML.
                    </div>
                  </div>
                </div>
              </div>

              {/* Technical Specifications */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-purple-400" />
                  Engine Specifications & Guardrails
                </h3>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[11px]">Primary Image Provider</div>
                    <div className="text-slate-200 font-semibold mt-0.5">OpenAI DALL-E-3</div>
                  </div>
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[11px]">Fallback / Dev Provider</div>
                    <div className="text-slate-200 font-semibold mt-0.5">Pillow Local Synthetic</div>
                  </div>
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[11px]">Target Hero Resolution</div>
                    <div className="text-slate-200 font-semibold mt-0.5">1536 × 864 (16:9 Aspect)</div>
                  </div>
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[11px]">Format & Encoding</div>
                    <div className="text-slate-200 font-semibold mt-0.5">WebP (q=85, Lanczos)</div>
                  </div>
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[11px]">Typography Policy</div>
                    <div className="text-emerald-400 font-semibold mt-0.5">STRICT NO-TEXT (Clean)</div>
                  </div>
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[11px]">Failure Gate Policy</div>
                    <div className="text-amber-400 font-semibold mt-0.5">BLOCK (Safety First)</div>
                  </div>
                </div>

                <div className="p-3.5 bg-blue-950/30 border border-blue-800/40 rounded-lg text-xs text-blue-200 space-y-1">
                  <div className="font-semibold flex items-center gap-1.5 text-blue-300">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    SEO & Accessibility Ready
                  </div>
                  <p className="text-blue-300/80 text-[11px]">
                    Every image produces clean lowercase hyphenated filenames (e.g. <code>students-using-ai-study-assistant.webp</code>), descriptive non-spam ALT text, and priority loading tags to maximize Google Lighthouse scores.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Visual Concept Studio */}
        {activeTab === "studio" && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-blue-400" />
                    Interactive Article Visual Studio
                  </h3>
                  <p className="text-xs text-slate-400">
                    Simulate how any article title & topic is analyzed, conceptualized, validated, and compressed.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="md:col-span-2 space-y-1">
                  <label className="text-xs text-slate-400">Article Title / Headline</label>
                  <input
                    type="text"
                    value={simTitle}
                    onChange={(e) => setSimTitle(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Primary Topic</label>
                  <input
                    type="text"
                    value={simTopic}
                    onChange={(e) => setSimTopic(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <button
                onClick={runSimulation}
                disabled={simLoading}
                className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${simLoading ? "animate-spin" : ""}`} />
                {simLoading ? "Simulating Visual Pipeline..." : "Generate & Validate Image Concept"}
              </button>
            </div>

            {/* Simulation Results */}
            {simResult && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Visual Canvas Card */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-slate-300">Featured Image Preview</h4>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono">
                      1536 × 864 WebP
                    </span>
                  </div>

                  {/* Synthetic 16:9 canvas representation */}
                  <div className="relative aspect-video w-full rounded-lg overflow-hidden border border-slate-700 bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 flex flex-col items-center justify-center p-4 text-center">
                    <div className="w-12 h-12 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center mb-2">
                      <ImageIcon className="w-6 h-6 text-blue-400" />
                    </div>
                    <div className="text-xs font-medium text-slate-200">
                      Editorial Lifestyle Hero Visual
                    </div>
                    <div className="text-[11px] text-slate-400 max-w-xs mt-1">
                      {simResult.concept.subject}
                    </div>
                    <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/60 text-[10px] font-mono text-slate-300">
                      {simResult.optimization.dimensions}
                    </div>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between py-1 border-b border-slate-800">
                      <span className="text-slate-400">SEO Filename:</span>
                      <span className="text-slate-200 font-mono text-[11px] truncate max-w-[200px]">
                        {simResult.optimization.filename}
                      </span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-800">
                      <span className="text-slate-400">File Size:</span>
                      <span className="text-emerald-400 font-semibold">{simResult.optimization.file_size_bytes}</span>
                    </div>
                    <div className="py-1">
                      <span className="text-slate-400 block mb-0.5">Alt Text:</span>
                      <span className="text-slate-300 italic text-[11px]">"{simResult.optimization.alt_text}"</span>
                    </div>
                  </div>
                </div>

                {/* Concept & Prompt Details */}
                <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-slate-300">Concept & Prompt Engineering</h4>
                    <span className="text-[11px] font-semibold text-emerald-400">
                      Validation Score: {simResult.validation.score}/100 PASS
                    </span>
                  </div>

                  <div className="space-y-3 text-xs">
                    <div>
                      <span className="text-slate-400 block text-[11px] mb-1 font-semibold uppercase tracking-wider">
                        Extracted Visual Elements
                      </span>
                      <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                        {simResult.visual_analysis.visualizable_elements.map((el: string, i: number) => (
                          <li key={i}>{el}</li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <span className="text-slate-400 block text-[11px] mb-1 font-semibold uppercase tracking-wider">
                        Enforced Disallowed Tropes (Negative Guardrails)
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {simResult.visual_analysis.things_to_avoid.map((el: string, i: number) => (
                          <span key={i} className="px-2 py-0.5 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[10px] rounded">
                            {el}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-400 block text-[11px] mb-1 font-semibold uppercase tracking-wider">
                        Final DALL-E-3 Prompt String
                      </span>
                      <div className="p-2.5 bg-slate-950 rounded border border-slate-800 text-slate-300 font-mono text-[11px] leading-relaxed">
                        {simResult.prompt}
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-400 block text-[11px] mb-1 font-semibold uppercase tracking-wider">
                        Generated Responsive Variants
                      </span>
                      <div className="grid grid-cols-4 gap-2">
                        {simResult.optimization.responsive_variants.map((v: any, i: number) => (
                          <div key={i} className="p-2 bg-slate-950 rounded border border-slate-800 text-center">
                            <div className="font-bold text-slate-200">{v.label}</div>
                            <div className="text-[10px] text-slate-400">{v.dimensions}</div>
                            <div className="text-[10px] text-emerald-400">{v.size}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Brand Style Policy */}
        {activeTab === "brand" && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-6">
            <div>
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-blue-400" />
                Site Visual Brand Profile
              </h3>
              <p className="text-xs text-slate-400">
                Configure visual guidelines, photography preferences, and negative constraints for your publication.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="space-y-1">
                <label className="text-slate-400">Visual Aesthetic Style</label>
                <input
                  type="text"
                  value={brandStyle}
                  onChange={(e) => setBrandStyle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-400">Composition Guidelines</label>
                <input
                  type="text"
                  value={brandComposition}
                  onChange={(e) => setBrandComposition(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-400">Preferred Mood & Tone</label>
                <input
                  type="text"
                  value={brandMood}
                  onChange={(e) => setBrandMood(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-400">Text & Logo Policy</label>
                <select
                  value={textPolicy}
                  onChange={(e) => setTextPolicy(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value="NO_TEXT">STRICT NO-TEXT (Clean Visual Only - Recommended)</option>
                  <option value="MINIMAL_LABEL">Minimal Diagram Labeling Only</option>
                </select>
              </div>

              <div className="space-y-1 md:col-span-2">
                <div className="flex justify-between">
                  <label className="text-slate-400">Style Balance (Photography vs. Conceptual Illustration)</label>
                  <span className="text-slate-300 font-semibold">{Math.round(photoPref * 100)}% Photo / {Math.round((1 - photoPref) * 100)}% Illustration</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={photoPref}
                  onChange={(e) => setPhotoPref(parseFloat(e.target.value))}
                  className="w-full accent-blue-500 cursor-pointer"
                />
              </div>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={handleSaveBrand}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-colors"
              >
                Save Visual Brand Policy
              </button>
              {savedNotice && (
                <span className="text-xs text-emerald-400 flex items-center gap-1 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Policy saved successfully
                </span>
              )}
            </div>
          </div>
        )}

        {/* Tab: Backfill */}
        {activeTab === "backfill" && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Layers className="w-4 h-4 text-purple-400" />
                Historical Article Media Backfill
              </h3>
              <p className="text-xs text-slate-400">
                Queue background generation for published articles missing featured images without changing URLs or slugs.
              </p>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 text-xs text-slate-300 space-y-2">
              <div className="font-semibold text-slate-100 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Safe Non-Disruptive Backfill Rules
              </div>
              <ul className="list-disc list-inside space-y-1 text-slate-400">
                <li>Articles that already have valid featured images are skipped (idempotent).</li>
                <li>Article URLs, canonical links, and slugs remain 100% unchanged.</li>
                <li>Images are generated, verified, and uploaded through WordPress or Heavenly endpoints.</li>
                <li>Respects daily generation budget limits.</li>
              </ul>
            </div>

            <button
              onClick={() => alert("Backfill task queued via Celery worker.")}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold transition-colors"
            >
              Start Backfill Task (Batch 10)
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
}
