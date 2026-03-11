import { useState } from "react";

const COLORS = {
  research: "#ff8e6e",
  verify: "#63b3ed", 
  explain: "#68d391",
  guard: "#fc8181",
  infra: "#b794f4",
  db: "#f6e05e",
  ext: "#76e4f7",
  bg: "#0f172a",
  card: "#1e293b",
  border: "#334155",
  text: "#f1f5f9",
  muted: "#94a3b8",
};

const Box = ({ label, sub, color, width = 120, height = 44, style = {} }) => (
  <div style={{
    background: color + "22",
    border: `1.5px solid ${color}`,
    borderRadius: 8,
    width, height,
    display: "flex", flexDirection: "column",
    alignItems: "center", justifyContent: "center",
    padding: "4px 8px",
    ...style
  }}>
    <div style={{ color: color, fontWeight: 700, fontSize: 11, textAlign: "center", lineHeight: 1.2 }}>{label}</div>
    {sub && <div style={{ color: COLORS.muted, fontSize: 9, textAlign: "center", marginTop: 2 }}>{sub}</div>}
  </div>
);

const Arrow = ({ label, color = COLORS.muted, vertical = false, style = {} }) => (
  <div style={{
    display: "flex", alignItems: "center", justifyContent: "center",
    flexDirection: vertical ? "column" : "row",
    gap: 2, ...style
  }}>
    {label && <div style={{ color: COLORS.muted, fontSize: 9 }}>{label}</div>}
    <div style={{ color: color, fontSize: vertical ? 14 : 16 }}>{vertical ? "↓" : "→"}</div>
  </div>
);

const Section = ({ title, color, children, style = {} }) => (
  <div style={{
    border: `1px solid ${color}44`,
    borderRadius: 10,
    background: color + "08",
    padding: "10px 12px",
    ...style
  }}>
    <div style={{ color: color, fontSize: 10, fontWeight: 700, marginBottom: 8, letterSpacing: 1 }}>{title}</div>
    {children}
  </div>
);

const Pipeline = ({ color, label, steps }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "center" }}>
    <div style={{
      background: color + "33", border: `1.5px solid ${color}`,
      borderRadius: 6, padding: "3px 12px",
      color, fontWeight: 700, fontSize: 11, marginBottom: 2
    }}>{label}</div>
    {steps.map((step, i) => (
      <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
        <Box label={step.label} sub={step.sub} color={color} width={140} height={step.h || 40} />
        {i < steps.length - 1 && <Arrow vertical color={color} />}
      </div>
    ))}
  </div>
);

export default function VelaArchitecture() {
  const [activeTab, setActiveTab] = useState("full");

  return (
    <div style={{ background: COLORS.bg, minHeight: "100vh", padding: 24, fontFamily: "system-ui, sans-serif", color: COLORS.text }}>
      
      {/* Title */}
      <div style={{ textAlign: "center", marginBottom: 20 }}>
        <div style={{ fontSize: 22, fontWeight: 800, color: COLORS.text }}>Vela — System Architecture</div>
        <div style={{ color: COLORS.muted, fontSize: 12, marginTop: 4 }}>Next.js 14 + FastAPI + GPT-4.1 + LangChain + ChromaDB</div>
      </div>

      {/* Tab */}
      <div style={{ display: "flex", justifyContent: "center", gap: 8, marginBottom: 20 }}>
        {["full", "research", "guard"].map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{
            padding: "6px 16px", borderRadius: 20, border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600,
            background: activeTab === tab ? "#6366f1" : COLORS.card,
            color: activeTab === tab ? "#fff" : COLORS.muted,
          }}>
            {{ full: "Full Architecture", research: "Research Pipeline", guard: "Guard Layers" }[tab]}
          </button>
        ))}
      </div>

      {/* ══ FULL ARCHITECTURE ══ */}
      {activeTab === "full" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

          {/* Row 1: User + Frontend */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <Box label="User" sub="Any Language" color={COLORS.text} width={90} height={44} />
            <Arrow label="HTTPS" />
            <Box label="Next.js 14" sub="TypeScript + Tailwind" color="#6366f1" width={140} height={44} />
            <Arrow label="REST / SSE" />
            <Box label="Clerk JWT" sub="Auth Middleware" color={COLORS.infra} width={110} height={44} />
            <Arrow />
            <Box label="FastAPI" sub="Python 3.11" color="#6366f1" width={110} height={44} />
          </div>

          <Arrow vertical style={{ alignSelf: "center" }} label="Request" />

          {/* Row 2: Guards */}
          <Section title="INPUT GUARDS (cheapest → expensive)" color={COLORS.guard}>
            <div style={{ display: "flex", gap: 6, alignItems: "center", justifyContent: "center", flexWrap: "wrap" }}>
              {[
                { l: "0. Length", s: "O(1) free" },
                { l: "1. PHI", s: "Regex free" },
                { l: "2. Injection", s: "Regex free" },
                { l: "3. Intent", s: "GPT-4.1-mini" },
                { l: "4. Rate Limit", s: "30 req/60s" },
              ].map((g, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Box label={g.l} sub={g.s} color={COLORS.guard} width={100} height={44} />
                  {i < 4 && <div style={{ color: COLORS.guard, fontSize: 14 }}>→</div>}
                </div>
              ))}
            </div>
          </Section>

          <Arrow vertical style={{ alignSelf: "center" }} label="Passed" />

          {/* Row 3: Three Pipelines */}
          <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>

            {/* Research */}
            <Section title="RESEARCH PIPELINE" color={COLORS.research} style={{ flex: 1 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "center" }}>
                <Box label="Query Rewriting" sub="→ 3 medical-EN queries" color={COLORS.research} width="100%" height={40} />
                <Arrow vertical color={COLORS.research} />
                <div style={{ display: "flex", gap: 6 }}>
                  <Box label="Chroma" sub="Local Vector DB" color={COLORS.db} width={80} height={40} />
                  <Box label="PubMed" sub="36M+ articles" color={COLORS.ext} width={80} height={40} />
                  <Box label="FDA API" sub="Drug labels" color={COLORS.ext} width={80} height={40} />
                </div>
                <Arrow vertical color={COLORS.research} label="parallel →merge" />
                <Box label="Dedup + Year Boost" sub="+0.10~+0.02" color={COLORS.research} width="100%" height={40} />
                <Arrow vertical color={COLORS.research} />
                <Box label="LLM-as-Judge" sub="relevance ≥ 0.45" color={COLORS.research} width="100%" height={40} />
                <Arrow vertical color={COLORS.research} />
                <Box label="Reranker" sub="top_k=8" color={COLORS.research} width="100%" height={40} />
                <Arrow vertical color={COLORS.research} />
                <Box label="GPT-4.1" sub="Generate + cite → SSE" color={COLORS.research} width="100%" height={40} />
              </div>
            </Section>

            {/* Verify */}
            <Section title="VERIFY PIPELINE" color={COLORS.verify} style={{ flex: 1 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "center" }}>
                <Box label="Drug Name Parser" sub="10 drugs max" color={COLORS.verify} width="100%" height={40} />
                <Arrow vertical color={COLORS.verify} />
                <Box label="Levenshtein" sub="Spelling correction" color={COLORS.verify} width="100%" height={40} />
                <Arrow vertical color={COLORS.verify} />
                <Box label="FDA Cache" sub="Hit → 24h TTL" color={COLORS.db} width="100%" height={40} />
                <Arrow vertical color={COLORS.verify} label="miss" />
                <Box label="OpenFDA API" sub="Live drug labels" color={COLORS.ext} width="100%" height={40} />
                <Arrow vertical color={COLORS.verify} />
                <Box label="GPT-4.1" sub="Interaction analysis" color={COLORS.verify} width="100%" height={40} />
                <Arrow vertical color={COLORS.verify} />
                <Box label="Structured Response" sub="severity + recommendation" color={COLORS.verify} width="100%" height={40} />
              </div>
            </Section>

            {/* Explain */}
            <Section title="EXPLAIN PIPELINE" color={COLORS.explain} style={{ flex: 1 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "center" }}>
                <Box label="Language Detection" sub="Unicode range" color={COLORS.explain} width="100%" height={40} />
                <Arrow vertical color={COLORS.explain} />
                <Box label="Entity Extractor" sub="GPT-4.1-mini" color={COLORS.explain} width="100%" height={40} />
                <Arrow vertical color={COLORS.explain} label="lab / med / dx" />
                <div style={{ display: "flex", gap: 4 }}>
                  <Box label="LOINC" sub="Lab std" color={COLORS.ext} width={70} height={40} />
                  <Box label="RxNorm" sub="Drug ID" color={COLORS.ext} width={70} height={40} />
                  <Box label="MedlinePlus" sub="Consumer" color={COLORS.ext} width={72} height={40} />
                </div>
                <Arrow vertical color={COLORS.explain} />
                <Box label="Cache Layer" sub="LOINC 7d / MedlinePlus 24h" color={COLORS.db} width="100%" height={40} />
                <Arrow vertical color={COLORS.explain} />
                <Box label="GPT-4.1" sub="Explain in input language" color={COLORS.explain} width="100%" height={40} />
              </div>
            </Section>
          </div>

          <Arrow vertical style={{ alignSelf: "center" }} />

          {/* Row 4: Infra */}
          <Section title="INFRASTRUCTURE" color={COLORS.infra}>
            <div style={{ display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
              <Box label="PostgreSQL" sub="ChatHistory + Audit" color={COLORS.infra} width={130} height={44} />
              <Box label="ChromaDB" sub="Vector store (local)" color={COLORS.db} width={130} height={44} />
              <Box label="SimpleCache" sub="In-memory TTL" color={COLORS.infra} width={130} height={44} />
              <Box label="SSE Stream" sub="fetchEventSource" color={COLORS.infra} width={130} height={44} />
              <Box label="Golden Dataset" sub="G01–G17 evals" color={COLORS.infra} width={130} height={44} />
            </div>
          </Section>

        </div>
      )}

      {/* ══ RESEARCH PIPELINE DETAIL ══ */}
      {activeTab === "research" && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0 }}>
          {[
            { label: "User Query", sub: "Any language, any phrasing", color: COLORS.text },
            null,
            { label: "Query Rewriting", sub: "GPT-4.1-mini → 3 standardized medical-EN queries", color: COLORS.research, h: 50 },
            null,
            { label: "Parallel Retrieval", sub: "Chroma (semantic)  +  PubMed (live)  +  FDA (live)", color: COLORS.ext, h: 50, wide: true },
            null,
            { label: "Merge + Dedup", sub: "by source_id — remove duplicates", color: COLORS.research },
            null,
            { label: "Year Boost", sub: "0yr: +0.10 / 1yr: +0.08 / 2yr: +0.06 / 3yr: +0.04 / 4yr: +0.02", color: COLORS.research, h: 50, wide: true },
            null,
            { label: "LLM-as-Judge", sub: "GPT-4.1-mini filters irrelevant docs  threshold ≥ 0.45", color: "#f6ad55", h: 50, wide: true },
            null,
            { label: "Reranker", sub: "top_k=8 from candidates ×4 (32 retrieved)", color: COLORS.research },
            null,
            { label: "GPT-4.1 Generator", sub: "Cited answer → SSE stream → client", color: COLORS.research, h: 50 },
            null,
            { label: "PostgreSQL", sub: "Save to ChatHistory", color: COLORS.infra },
          ].map((step, i) => {
            if (!step) return <Arrow key={i} vertical color={COLORS.research} />;
            return (
              <div key={i} style={{
                background: step.color + "22", border: `1.5px solid ${step.color}`,
                borderRadius: 8, padding: "8px 20px",
                width: step.wide ? 400 : 300, height: step.h || 44,
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                textAlign: "center"
              }}>
                <div style={{ color: step.color, fontWeight: 700, fontSize: 13 }}>{step.label}</div>
                <div style={{ color: COLORS.muted, fontSize: 10, marginTop: 3 }}>{step.sub}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* ══ GUARD LAYERS ══ */}
      {activeTab === "guard" && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
          <div style={{ color: COLORS.muted, fontSize: 12, marginBottom: 8 }}>Ordered cheapest → most expensive. Blocked at any step = immediate reject.</div>
          {[
            { n: "0", label: "Input Length Check", sub: "len(text) > 5000 → reject", cost: "Free  O(1)", color: "#68d391" },
            { n: "1", label: "PHI Detection", sub: "TW ID / JP My Number / SSN / MRN regex", cost: "Free  Regex", color: "#68d391" },
            { n: "2", label: "Prompt Injection", sub: "12 patterns: ignore instructions / jailbreak / system tags", cost: "Free  Regex", color: "#68d391" },
            { n: "3", label: "Rate Limiter", sub: "Research/Verify: 30 req/60s  •  Explain: 20 req/60s", cost: "Free  In-memory", color: "#f6ad55" },
            { n: "4", label: "Medical Intent", sub: "GPT-4.1-mini classifies medical vs non-medical (first 500 chars)", cost: "~$0.0001", color: COLORS.guard },
            { n: "✓", label: "Request Passes → Pipeline", sub: "All guards cleared", cost: "", color: COLORS.research },
          ].map((g, i) => (
            <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0 }}>
              {i > 0 && <Arrow vertical color={g.color} style={{ marginBottom: 4 }} />}
              <div style={{
                display: "flex", alignItems: "center", gap: 12,
                background: g.color + "15", border: `1.5px solid ${g.color}`,
                borderRadius: 10, padding: "10px 20px", width: 500,
              }}>
                <div style={{
                  background: g.color + "33", border: `1.5px solid ${g.color}`,
                  borderRadius: 6, width: 28, height: 28,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  color: g.color, fontWeight: 800, fontSize: 13, flexShrink: 0
                }}>{g.n}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ color: g.color, fontWeight: 700, fontSize: 13 }}>{g.label}</div>
                  <div style={{ color: COLORS.muted, fontSize: 10, marginTop: 2 }}>{g.sub}</div>
                </div>
                {g.cost && (
                  <div style={{
                    background: COLORS.card, borderRadius: 6, padding: "3px 10px",
                    color: g.color, fontSize: 10, fontWeight: 700, flexShrink: 0
                  }}>{g.cost}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Legend */}
      <div style={{ display: "flex", gap: 16, justifyContent: "center", marginTop: 20, flexWrap: "wrap" }}>
        {[
          { color: COLORS.research, label: "Research" },
          { color: COLORS.verify, label: "Verify" },
          { color: COLORS.explain, label: "Explain" },
          { color: COLORS.guard, label: "Guards" },
          { color: COLORS.db, label: "Storage / Cache" },
          { color: COLORS.ext, label: "External APIs" },
          { color: COLORS.infra, label: "Infrastructure" },
        ].map(l => (
          <div key={l.label} style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: l.color }} />
            <span style={{ fontSize: 11, color: COLORS.muted }}>{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
