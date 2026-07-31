import React, { useState, useRef, useEffect } from "react";

// ---------------------------------------------------------------------------
// Design tokens — graphite instrument panel, muted clinical-monitor teal,
// ochre for review flags, brick for the re-plan / critical path.
// ---------------------------------------------------------------------------
const T = {
  bg: "#12151A",
  panel: "#171B21",
  panelAlt: "#1B2028",
  border: "#262B33",
  borderStrong: "#3A414D",
  text: "#E7E9ED",
  textDim: "#8C93A0",
  textFaint: "#565D69",
  accent: "#5AAAA6",
  accentDim: "#2B4C4B",
  warn: "#CE9349",
  warnBg: "#241C10",
  warnBorder: "#7A5423",
  danger: "#BD6752",
  dangerBg: "#251511",
  dangerBorder: "#6E3B2C",
  success: "#6FA184",
};

const FONT_MONO =
  "'IBM Plex Mono', ui-monospace, 'SF Mono', 'Cascadia Code', monospace";
const FONT_SANS =
  "'IBM Plex Sans', -apple-system, 'Segoe UI', sans-serif";

const SAMPLES = [
  {
    id: "sample-1",
    label: "Routine follow-up — lean path",
    text: `Patient: J. Alvarez, 42M\nReason for visit: Follow-up for seasonal allergic rhinitis.\nAssessment: Symptoms well controlled on current regimen. No new complaints.\nPlan: Continue loratadine 10mg once daily. Return in 6 months.`,
  },
  {
    id: "sample-2",
    label: "Multi-system discharge — full path",
    text: `Patient: R. Okafor, 68F\nDischarge summary — admitted for community-acquired pneumonia with acute on chronic kidney disease exacerbation.\nHistory: Hypertension, type 2 diabetes, stage 3 CKD.\nHospital course: Treated with IV ceftriaxone, transitioned to oral amoxicillin on day 4. Renal function trended toward baseline by discharge.\nMedications on discharge: Amoxicillin 500mg TID x3 days, Lisinopril 10mg daily, Metformin 500mg BID, Furosemide 20mg daily.\nLabs on discharge: Creatinine 1.3 mg/dL, Sodium 138 mmol/L, Potassium 4.1 mmol/L.\nDiagnoses: Community-acquired pneumonia (resolved), CKD stage 3 (stable), Type 2 diabetes mellitus, Hypertension.`,
  },
  {
    id: "sample-3",
    label: "Dosage conflict — triggers re-plan",
    text: `Patient: T. Nguyen, 74M\nDischarge summary — admitted for hyperglycemia and volume overload.\nHistory: Type 2 diabetes, congestive heart failure, atrial fibrillation.\nHospital course: Metformin was held on admission for elevated creatinine. Diuresed with IV furosemide. Metformin resumed at discharge.\nMedications on discharge: Metformin 500mg BID, Metformin 2000mg once daily, Furosemide 40mg daily, Apixaban 5mg BID.\nLabs on discharge: Creatinine 1.1 mg/dL, Sodium 129 mmol/L, Potassium 4.3 mmol/L.\nDiagnoses: Type 2 diabetes mellitus, Congestive heart failure, Atrial fibrillation, Acute kidney injury (resolved).`,
  },
];

const STEP_DEFS = [
  { id: "orchestrator", num: "01", label: "Orchestrator", detail: "Routes by report complexity" },
  { id: "ner", num: "02", label: "NER agent", detail: "Entity + span extraction", specialist: true },
  { id: "relation", num: "03", label: "Relation agent", detail: "Causal + temporal links", specialist: true },
  { id: "grounding", num: "04", label: "Grounding agent", detail: "SNOMED / RxNorm mapping", specialist: true },
  { id: "summary", num: "05", label: "Summary agent", detail: "Narrative generation", specialist: true },
  { id: "verifier", num: "06", label: "Verifier / critic", detail: "Consistency checks" },
  { id: "done", num: "07", label: "Audit trail", detail: "Immutable log persisted" },
];

const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

function makeCaseId() {
  const chars = "0123456789ABCDEF";
  let s = "";
  for (let i = 0; i < 8; i++) s += chars[Math.floor(Math.random() * chars.length)];
  return `CASE-${s.slice(0, 4)}-${s.slice(4)}`;
}

export default function ClinicalAgentDemo() {
  const [sampleId, setSampleId] = useState(SAMPLES[0].id);
  const [reportText, setReportText] = useState(SAMPLES[0].text);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeStep, setActiveStep] = useState(null);
  const [completedSteps, setCompletedSteps] = useState([]);
  const [dispatched, setDispatched] = useState([]);
  const [replanCount, setReplanCount] = useState(0);
  const [replanActive, setReplanActive] = useState(false);
  const [auditEvents, setAuditEvents] = useState([]);
  const [expandedEvent, setExpandedEvent] = useState(null);
  const [flags, setFlags] = useState([]);
  const [counts, setCounts] = useState({ entities: 0, relations: 0, grounded: 0 });
  const [expandedStep, setExpandedStep] = useState(null);
  const [caseId, setCaseId] = useState(null);
  const [durationMs, setDurationMs] = useState(null);
  const [apiOutputs, setApiOutputs] = useState(null);
  const runId = useRef(0);
  const runStartedAt = useRef(0);

  useEffect(() => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href =
      "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap";
    document.head.appendChild(link);
    return () => document.head.removeChild(link);
  }, []);

  function pushEvent(evt) {
    setAuditEvents((prev) => [
      ...prev,
      { ...evt, id: prev.length, time: new Date().toLocaleTimeString([], { hour12: false }) },
    ]);
  }

  function selectSample(id) {
    const s = SAMPLES.find((x) => x.id === id);
    setSampleId(id);
    setReportText(s.text);
    resetRun();
  }

  function resetRun() {
    setIsProcessing(false);
    setActiveStep(null);
    setCompletedSteps([]);
    setDispatched([]);
    setReplanCount(0);
    setReplanActive(false);
    setAuditEvents([]);
    setFlags([]);
    setCounts({ entities: 0, relations: 0, grounded: 0 });
    setExpandedStep(null);
    setDurationMs(null);
    setApiOutputs(null);
  }

  async function runPipeline() {
    const myRun = ++runId.current;
    resetRun();
    await sleep(50);
    if (runId.current !== myRun) return;
    
    setIsProcessing(true);
    const newCaseId = makeCaseId();
    setCaseId(newCaseId);
    runStartedAt.current = Date.now();
    setActiveStep("orchestrator");

    // Call the actual FastAPI Backend!
    let backendResult = null;
    try {
      const response = await fetch("http://localhost:8000/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: newCaseId, text: reportText })
      });
      if (!response.ok) throw new Error("API request failed");
      backendResult = await response.json();
    } catch (e) {
      console.error(e);
      alert("Failed to connect to backend at http://localhost:8000/process.\\nMake sure your FastAPI server (api/main.py) is running!");
      setIsProcessing(false);
      setActiveStep(null);
      return;
    }

    if (runId.current !== myRun) return;
    
    // Map backend output to UI format
    const entitiesById = {};
    backendResult.extracted_entities.forEach(e => {
      entitiesById[e.id] = e;
    });

    const extractedNer = backendResult.extracted_entities.map(e => ({ text: e.text, type: e.label }));
    
    const extractedGrounding = backendResult.extracted_entities
      .filter(e => e.grounding)
      .map(e => ({ text: e.text, code: `${e.grounding.ontology} ${e.grounding.code}` }));
      
    const extractedRelations = backendResult.relations.map(r => {
      const fromText = entitiesById[r.source_entity_id]?.text || "Unknown Entity";
      const toText = entitiesById[r.target_entity_id]?.text || "Unknown Entity";
      return { from: fromText, rel: r.relation_type, to: toText };
    });

    
    const backendOutputs = {
      ner: extractedNer,
      relation: extractedRelations,
      grounding: extractedGrounding,
      summary: backendResult.summary
    };
    
    setApiOutputs(backendOutputs);

    const markDone = (id) => setCompletedSteps((prev) => [...prev, id]);
    await sleep(400); // Visual delay for Orchestrator processing
    
    // Extract plan from backend, map agent names to UI steps (e.g. ner_agent -> ner)
    const execPlan = backendResult.execution_plan || [];
    const dispatchSteps = execPlan.map(a => a.replace("_agent", ""));
    setDispatched(dispatchSteps);
    markDone("orchestrator");
    
    pushEvent({
      agent: "Orchestrator",
      type: "routing",
      summary: `Backend returned Execution Plan: ${execPlan.join(" → ")}`,
    });

    // Reveal the steps sequentially
    for (const agentId of dispatchSteps) {
      if (runId.current !== myRun) return;
      if (!STEP_DEFS.find(s => s.id === agentId)) continue; // ignore unknown agents in UI
      
      setActiveStep(agentId);
      await sleep(500);
      markDone(agentId);
      
      if (agentId === "ner") {
        setCounts((c) => ({ ...c, entities: extractedNer.length }));
        pushEvent({ agent: "NER agent", type: "extraction", summary: `Extracted ${extractedNer.length} entities` });
      }
      if (agentId === "relation") {
        setCounts((c) => ({ ...c, relations: extractedRelations.length }));
        pushEvent({ agent: "Relation agent", type: "extraction", summary: `Identified ${extractedRelations.length} relations` });
      }
      if (agentId === "grounding") {
        setCounts((c) => ({ ...c, grounded: extractedGrounding.length }));
        pushEvent({ agent: "Grounding agent", type: "extraction", summary: `Grounded ${extractedGrounding.length} entities` });
      }
      if (agentId === "summary") {
        pushEvent({ agent: "Summary agent", type: "generation", summary: "Generated narrative summary" });
      }
    }

    if (runId.current !== myRun) return;
    setActiveStep("verifier");
    await sleep(600);

    const vFlags = backendResult.verifier_flags || [];
    if (vFlags.length > 0) {
      const uiFlags = vFlags.map((f, i) => ({
        id: i,
        status: "open",
        type: f.check_type,
        summary: `${f.check_type} Flag`,
        justification: f.justification,
        confidence: 0.95,
        evidenceSpan: "Requires Manual Review"
      }));
      setFlags(uiFlags);
      
      uiFlags.forEach(f => {
        pushEvent({ agent: "Verifier / critic", type: "flag raised", summary: f.justification });
      });

      // Simulate a re-plan visually if backend triggered flags
      setReplanActive(true);
      setReplanCount(1);
      pushEvent({ agent: "Orchestrator", type: "re-plan", summary: "Routing flagged reports back to human review." });
      await sleep(800);
      setReplanActive(false);
    } else {
      pushEvent({ agent: "Verifier / critic", type: "check passed", summary: "All consistency checks passed — no flags raised from backend" });
    }

    if (runId.current !== myRun) return;
    markDone("verifier");
    setActiveStep("done");
    await sleep(400);
    markDone("done");
    const elapsed = Date.now() - runStartedAt.current;
    setDurationMs(elapsed);
    pushEvent({
      agent: "Audit trail",
      type: "persisted",
      summary: `Run complete in ${(elapsed / 1000).toFixed(1)}s — results persisted to SQLite DB by Backend`,
    });
    setIsProcessing(false);
    setActiveStep(null);
  }

  function resolveFlag(id, status) {
    setFlags((prev) => prev.map((f) => (f.id === id ? { ...f, status } : f)));
    pushEvent({
      agent: "Reviewer (HITL)",
      type: "flag resolved",
      summary: `Flag ${status} by reviewer`,
    });
  }

  function downloadAuditTrail() {
    const payload = {
      case_id: caseId,
      sample: sampleId,
      duration_ms: durationMs,
      flags,
      events: auditEvents,
      api_outputs: apiOutputs
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(caseId || "case").toLowerCase()}-audit-trail.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ background: T.bg, minHeight: "100vh", fontFamily: FONT_SANS }}>
      <style>{`
        * { box-sizing: border-box; }
        ::selection { background: ${T.accentDim}; }
        @keyframes ecgScroll { from { transform: translateX(0); } to { transform: translateX(-150px); } }
        @keyframes pulseDot { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
        select:focus, textarea:focus, button:focus-visible { outline: 1px solid ${T.accent}; outline-offset: 1px; }
        textarea::-webkit-scrollbar, .scroll::-webkit-scrollbar { width: 6px; }
        textarea::-webkit-scrollbar-thumb, .scroll::-webkit-scrollbar-thumb { background: ${T.borderStrong}; }
        @media (prefers-reduced-motion: reduce) {
          * { animation-duration: 0.001ms !important; animation-iteration-count: 1 !important; }
        }
      `}</style>

      <div style={{ maxWidth: "1360px", margin: "0 auto", padding: "28px 24px 60px" }}>
        <Header isProcessing={isProcessing} caseId={caseId} durationMs={durationMs} />

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "300px 1fr 400px",
            gap: "1px",
            background: T.border,
            border: `1px solid ${T.border}`,
            marginTop: "24px",
          }}
        >
          <InputPanel
            sampleId={sampleId}
            selectSample={selectSample}
            reportText={reportText}
            setReportText={setReportText}
            isProcessing={isProcessing}
            runPipeline={runPipeline}
          />
          <LedgerPanel
            dispatched={dispatched}
            activeStep={activeStep}
            completedSteps={completedSteps}
            replanActive={replanActive}
            replanCount={replanCount}
            counts={counts}
            flags={flags}
            agentOutputs={apiOutputs}
            expandedStep={expandedStep}
            setExpandedStep={setExpandedStep}
          />
          <AuditPanel
            auditEvents={auditEvents}
            expandedEvent={expandedEvent}
            setExpandedEvent={setExpandedEvent}
            flags={flags}
            resolveFlag={resolveFlag}
            onExport={downloadAuditTrail}
            canExport={auditEvents.length > 0}
          />
        </div>
      </div>
    </div>
  );
}

function Header({ isProcessing, caseId, durationMs }) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
        <div>
          <div style={{ fontFamily: FONT_MONO, fontSize: "11px", letterSpacing: "0.12em", color: T.textFaint, textTransform: "uppercase" }}>
            Clinical report understanding — case trace
          </div>
          <h1 style={{ fontFamily: FONT_SANS, fontSize: "22px", fontWeight: 500, color: T.text, margin: "4px 0 0" }}>
            Multi-agent extraction &amp; verification
          </h1>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {caseId && (
            <div style={{ textAlign: "right" }}>
              <div style={{ fontFamily: FONT_MONO, fontSize: "12px", color: T.textDim }}>{caseId}</div>
              {durationMs != null && (
                <div style={{ fontFamily: FONT_MONO, fontSize: "10px", color: T.textFaint, marginTop: "2px" }}>
                  {(durationMs / 1000).toFixed(1)}s total
                </div>
              )}
            </div>
          )}
          <div style={{ fontFamily: FONT_MONO, fontSize: "11px", color: isProcessing ? T.accent : T.textFaint, display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: isProcessing ? T.accent : T.textFaint, display: "inline-block", animation: isProcessing ? "pulseDot 1s ease-in-out infinite" : "none" }} />
            {isProcessing ? "processing" : "idle"}
          </div>
        </div>
      </div>
      <EcgStrip isProcessing={isProcessing} />
    </div>
  );
}

function EcgStrip({ isProcessing }) {
  return (
    <div style={{ marginTop: "14px", height: "34px", overflow: "hidden", borderTop: `1px solid ${T.border}`, borderBottom: `1px solid ${T.border}` }}>
      <svg width="200%" height="34" viewBox="0 0 1600 34" preserveAspectRatio="none" style={{ animation: isProcessing ? "ecgScroll 2.2s linear infinite" : "none", opacity: isProcessing ? 0.9 : 0.28 }}>
        <defs>
          <pattern id="ecgUnit" x="0" y="0" width="150" height="34" patternUnits="userSpaceOnUse">
            <path d="M0,17 L52,17 L60,6 L67,29 L74,17 L150,17" fill="none" stroke={T.accent} strokeWidth="1.1" strokeLinejoin="round" strokeLinecap="round" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="1600" height="34" fill="url(#ecgUnit)" />
      </svg>
    </div>
  );
}

function PanelShell({ title, index, children, corner }) {
  return (
    <div style={{ background: T.panel, padding: "18px", minWidth: 0 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontFamily: FONT_MONO, fontSize: "11px", color: T.textFaint }}>{index}</span>
          <span style={{ fontFamily: FONT_MONO, fontSize: "11px", letterSpacing: "0.1em", textTransform: "uppercase", color: T.textDim }}>
            {title}
          </span>
        </div>
        {corner}
      </div>
      {children}
    </div>
  );
}

function InputPanel({ sampleId, selectSample, reportText, setReportText, isProcessing, runPipeline }) {
  return (
    <PanelShell title="Input" index="—">
      <label style={fieldLabel}>Sample report</label>
      <select value={sampleId} onChange={(e) => selectSample(e.target.value)} disabled={isProcessing} style={selectStyle}>
        {SAMPLES.map((s) => (
          <option key={s.id} value={s.id}>
            {s.label}
          </option>
        ))}
      </select>

      <label style={{ ...fieldLabel, marginTop: "16px" }}>Report text</label>
      <textarea
        value={reportText}
        onChange={(e) => setReportText(e.target.value)}
        disabled={isProcessing}
        rows={15}
        style={textareaStyle}
      />

      <button
        onClick={runPipeline}
        disabled={isProcessing}
        style={{
          width: "100%",
          marginTop: "16px",
          background: isProcessing ? "transparent" : T.accent,
          color: isProcessing ? T.textFaint : "#0C1B1A",
          border: `1px solid ${isProcessing ? T.border : T.accent}`,
          padding: "10px",
          fontFamily: FONT_MONO,
          fontSize: "12px",
          letterSpacing: "0.04em",
          cursor: isProcessing ? "default" : "pointer",
        }}
      >
        {isProcessing ? "Processing via FastAPI..." : "Run Backend Pipeline →"}
      </button>
    </PanelShell>
  );
}

const fieldLabel = { display: "block", fontFamily: FONT_MONO, fontSize: "10px", letterSpacing: "0.08em", textTransform: "uppercase", color: T.textFaint, marginBottom: "6px" };
const selectStyle = { width: "100%", background: T.panelAlt, border: `1px solid ${T.border}`, color: T.text, fontFamily: FONT_SANS, fontSize: "13px", padding: "8px", borderRadius: "2px" };
const textareaStyle = { width: "100%", background: T.bg, border: `1px solid ${T.border}`, color: T.textDim, fontFamily: FONT_MONO, fontSize: "11.5px", lineHeight: 1.6, padding: "10px", resize: "vertical", borderRadius: "2px" };

function LedgerPanel({ dispatched, activeStep, completedSteps, replanActive, replanCount, counts, flags, agentOutputs, expandedStep, setExpandedStep }) {
  const openFlags = flags.filter((f) => f.status === "open").length;

  function statusOf(id, specialist) {
    if (specialist && !dispatched.includes(id) && dispatched.length > 0) return "skipped";
    if (activeStep === id) return "active";
    if (completedSteps.includes(id)) return "done";
    return "pending";
  }

  return (
    <PanelShell title="Pipeline trace" index="—">
      <div style={{ display: "flex", gap: "10px", marginBottom: "18px", flexWrap: "wrap" }}>
        <Metric label="entities" value={counts.entities} />
        <Metric label="relations" value={counts.relations} />
        <Metric label="grounded" value={counts.grounded} />
        <Metric label="open flags" value={openFlags} tone={openFlags > 0 ? "warn" : null} />
      </div>

      <div style={{ position: "relative", paddingLeft: "6px" }}>
        <div style={{ position: "absolute", left: "22px", top: "10px", bottom: "10px", width: "1px", background: T.border }} />
        {STEP_DEFS.map((step) => {
          const status = statusOf(step.id, step.specialist);
          const output = agentOutputs ? agentOutputs[step.id] : null;
          const inspectable = status === "done" && !!output;
          return (
            <LedgerRow
              key={step.id}
              step={step}
              status={status}
              inspectable={inspectable}
              expanded={expandedStep === step.id}
              onToggle={() => inspectable && setExpandedStep(expandedStep === step.id ? null : step.id)}
              output={output}
            />
          );
        })}

        {(replanActive || replanCount > 0) && (
          <div style={{ marginLeft: "44px", marginTop: "-6px", marginBottom: "10px", paddingLeft: "12px", borderLeft: `2px solid ${T.dangerBorder}`, fontFamily: FONT_MONO, fontSize: "11px", color: T.danger }}>
            ↳ re-plan {replanCount}/2 — flagging back to review
            {replanActive && <span style={{ marginLeft: "6px", opacity: 0.7 }}>· in progress</span>}
          </div>
        )}
      </div>
    </PanelShell>
  );
}

function LedgerRow({ step, status, inspectable, expanded, onToggle, output }) {
  const isSkipped = status === "skipped";
  const dotColor = status === "active" ? T.accent : status === "done" ? T.success : status === "skipped" ? T.textFaint : T.borderStrong;

  return (
    <div>
      <div
        role={inspectable ? "button" : undefined}
        tabIndex={inspectable ? 0 : undefined}
        onClick={onToggle}
        onKeyDown={(e) => {
          if (inspectable && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            onToggle();
          }
        }}
        style={{ display: "flex", alignItems: "flex-start", gap: "12px", padding: "9px 0", opacity: isSkipped ? 0.4 : 1, cursor: inspectable ? "pointer" : "default" }}
      >
        <div style={{ width: "10px", height: "10px", borderRadius: "50%", marginLeft: "17px", marginTop: "3px", flexShrink: 0, background: status === "done" || status === "active" ? dotColor : "transparent", border: `1.5px solid ${dotColor}`, animation: status === "active" ? "pulseDot 1s ease-in-out infinite" : "none" }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: "8px", flexWrap: "wrap" }}>
            <span style={{ fontFamily: FONT_MONO, fontSize: "11px", color: T.textFaint }}>{step.num}</span>
            <span style={{ fontFamily: FONT_SANS, fontSize: "13px", fontWeight: 500, color: status === "pending" || isSkipped ? T.textDim : T.text }}>{step.label}</span>
            {isSkipped && <span style={{ fontFamily: FONT_MONO, fontSize: "10px", color: T.textFaint }}>not dispatched</span>}
            {inspectable && <span style={{ fontFamily: FONT_MONO, fontSize: "10px", color: T.textFaint }}>{expanded ? "[ hide output ]" : "[ inspect output ]"}</span>}
          </div>
          <div style={{ fontFamily: FONT_SANS, fontSize: "12px", color: T.textFaint, marginTop: "1px" }}>{step.detail}</div>
        </div>
      </div>
      {expanded && output && (
        <div style={{ marginLeft: "44px", marginBottom: "10px" }}>
          <StepOutput stepId={step.id} output={output} />
        </div>
      )}
    </div>
  );
}

function StepOutput({ stepId, output }) {
  const box = { border: `1px solid ${T.border}`, background: T.panelAlt, padding: "10px 12px", borderRadius: "2px" };
  const rowText = { fontFamily: FONT_MONO, fontSize: "11px", color: T.textDim, lineHeight: 1.7 };

  if (stepId === "ner") {
    return (
      <div style={box}>
        {output.length === 0 ? <div style={rowText}>No entities found.</div> : output.map((e, i) => (
          <div key={i} style={rowText}><span style={{ color: T.accent }}>{e.text}</span><span style={{ color: T.textFaint }}> · {e.type}</span></div>
        ))}
      </div>
    );
  }
  if (stepId === "relation") {
    return (
      <div style={box}>
        {output.length === 0 ? <div style={rowText}>No relations found.</div> : output.map((r, i) => (
          <div key={i} style={rowText}>{r.from} <span style={{ color: T.accent }}>→ {r.rel} →</span> {r.to}</div>
        ))}
      </div>
    );
  }
  if (stepId === "grounding") {
    return (
      <div style={box}>
        {output.length === 0 ? <div style={rowText}>No entities grounded.</div> : output.map((g, i) => (
          <div key={i} style={rowText}>{g.text} <span style={{ color: T.textFaint }}>—</span> <span style={{ color: g.code?.startsWith("—") ? T.textFaint : T.success }}>{g.code}</span></div>
        ))}
      </div>
    );
  }
  if (stepId === "summary") {
    return (
      <div style={box}>
        <div style={{ fontFamily: FONT_SANS, fontSize: "12.5px", color: T.textDim, lineHeight: 1.6 }}>{output || "No summary generated."}</div>
      </div>
    );
  }
  return null;
}

function Metric({ label, value, tone }) {
  const color = tone === "warn" && value > 0 ? T.warn : T.text;
  return (
    <div style={{ border: `1px solid ${tone === "warn" && value > 0 ? T.warnBorder : T.border}`, background: tone === "warn" && value > 0 ? T.warnBg : "transparent", padding: "6px 10px", borderRadius: "2px" }}>
      <div style={{ fontFamily: FONT_MONO, fontSize: "16px", color, lineHeight: 1 }}>{String(value).padStart(2, "0")}</div>
      <div style={{ fontFamily: FONT_MONO, fontSize: "9.5px", color: T.textFaint, letterSpacing: "0.06em", marginTop: "3px" }}>{label}</div>
    </div>
  );
}

function AuditPanel({ auditEvents, expandedEvent, setExpandedEvent, flags, resolveFlag, onExport, canExport }) {
  return (
    <PanelShell
      title="Audit trail"
      index="—"
      corner={canExport ? <TextButton label="[ export .json ]" color={T.textDim} onClick={onExport} /> : null}
    >
      {flags.map((flag) => (
        <FlagCard key={flag.id} flag={flag} onResolve={resolveFlag} />
      ))}

      <div style={{ display: "flex", flexDirection: "column", maxHeight: "560px", overflowY: "auto" }} className="scroll">
        {auditEvents.length === 0 && (
          <p style={{ fontFamily: FONT_SANS, fontSize: "12.5px", color: T.textFaint }}>
            No events yet — run the pipeline to populate the trace.
          </p>
        )}
        {auditEvents.map((evt, i) => (
          <AuditRow
            key={evt.id}
            evt={evt}
            isLast={i === auditEvents.length - 1}
            expanded={expandedEvent === evt.id}
            onToggle={() => setExpandedEvent(expandedEvent === evt.id ? null : evt.id)}
          />
        ))}
      </div>
    </PanelShell>
  );
}

function FlagCard({ flag, onResolve }) {
  return (
    <div style={{ borderLeft: `3px solid ${T.warnBorder}`, background: T.warnBg, padding: "12px 14px", marginBottom: "16px" }}>
      <div style={{ fontFamily: FONT_MONO, fontSize: "10px", letterSpacing: "0.08em", textTransform: "uppercase", color: T.warn, marginBottom: "6px" }}>Flagged for review</div>
      <div style={{ fontFamily: FONT_SANS, fontSize: "12.5px", color: T.text, lineHeight: 1.5 }}>{flag.summary}</div>
      <div style={{ fontFamily: FONT_SANS, fontSize: "12px", color: T.textDim, lineHeight: 1.6, marginTop: "8px" }}>{flag.justification}</div>

      <div style={{ marginTop: "10px", paddingTop: "8px", borderTop: `1px solid ${T.warnBorder}` }}>
        <div style={{ fontFamily: FONT_MONO, fontSize: "9.5px", letterSpacing: "0.08em", color: T.textFaint, marginBottom: "4px" }}>EVIDENCE</div>
        <div style={{ fontFamily: FONT_MONO, fontSize: "11px", color: T.textDim }}>"{flag.evidenceSpan}"</div>
      </div>

      <RangeBar value={flag.confidence} />

      <div style={{ marginTop: "10px", display: "flex", gap: "16px" }}>
        {flag.status === "open" ? (
          <>
            <TextButton label="[ approve ]" color={T.success} onClick={() => onResolve(flag.id, "approved")} />
            <TextButton label="[ reject ]" color={T.danger} onClick={() => onResolve(flag.id, "rejected")} />
          </>
        ) : (
          <span style={{ fontFamily: FONT_MONO, fontSize: "11px", color: flag.status === "approved" ? T.success : T.danger }}>{flag.status} by reviewer</span>
        )}
      </div>
    </div>
  );
}

function RangeBar({ value }) {
  return (
    <div style={{ marginTop: "10px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontFamily: FONT_MONO, fontSize: "9px", color: T.textFaint }}>
        <span>confidence</span>
        <span>{value.toFixed(2)}</span>
      </div>
      <div style={{ position: "relative", height: "3px", background: T.borderStrong, marginTop: "4px" }}>
        <div style={{ position: "absolute", left: "50%", top: "-2px", width: "1px", height: "7px", background: T.textFaint }} />
        <div style={{ position: "absolute", left: `calc(${value * 100}% - 3px)`, top: "-2px", width: "7px", height: "7px", borderRadius: "50%", background: T.warn }} />
      </div>
    </div>
  );
}

function TextButton({ label, color, onClick }) {
  return (
    <button onClick={onClick} style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: FONT_MONO, fontSize: "11px", color }}>{label}</button>
  );
}

function AuditRow({ evt, expanded, onToggle, isLast }) {
  return (
    <div onClick={onToggle} style={{ borderBottom: isLast ? "none" : `1px solid ${T.border}`, padding: "9px 0", cursor: "pointer" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: "8px", flexWrap: "wrap" }}>
        <span style={{ fontFamily: FONT_MONO, fontSize: "10px", color: T.textFaint }}>{evt.time}</span>
        <span style={{ fontFamily: FONT_SANS, fontSize: "12px", fontWeight: 500, color: T.accent }}>{evt.agent}</span>
        <span style={{ fontFamily: FONT_MONO, fontSize: "10px", color: T.textFaint }}>{evt.type}</span>
      </div>
      <div style={{ fontFamily: FONT_SANS, fontSize: "12px", color: T.textDim, marginTop: "3px", lineHeight: 1.5, display: expanded ? "block" : "-webkit-box", WebkitLineClamp: expanded ? "unset" : 1, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{evt.summary}</div>
    </div>
  );
}
