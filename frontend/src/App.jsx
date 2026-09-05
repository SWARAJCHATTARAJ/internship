import { useMemo, useState } from "react";
import "./App.css";

const DEMOS = {
  routine: { label: "Routine follow-up", text: "Patient reports seasonal allergy symptoms. Paracetamol 500 mg once daily for 3 days." },
  complex: { label: "Multi-system discharge", text: "Discharge summary. Diagnosis: Type 2 diabetes and hypertension. Medications: Metformin 500 mg twice daily for 30 days. Lisinopril 10 mg once daily." },
  conflict: { label: "Dosage conflict", text: "Prescription: Metformin 500 mg twice daily. Metformin 1000 mg once daily." },
};
const AGENTS = [
  ["document", "Document agent"], ["ocr", "OCR agent"], ["orchestrator", "Orchestrator"], ["ner", "NER agent"],
  ["medication", "Medication agent"], ["clinical_context", "Clinical context"], ["relation", "Relation agent"],
  ["timeline", "Timeline agent"], ["grounding", "Grounding agent"], ["summary", "Summary agent"], ["verifier", "Verifier / critic"],
];

const apiBase = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

function prettify(value) { return String(value || "").replaceAll("_", " "); }
function confidence(value) { return value == null ? "Not available" : `${Math.round(value * 100)}%`; }

export default function App() {
  const [inputMode, setInputMode] = useState("upload");
  const [uploadedFile, setUploadedFile] = useState(null);
  const [documentText, setDocumentText] = useState("");
  const [demoScenario, setDemoScenario] = useState("routine");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [activeTab, setActiveTab] = useState("Overview");
  const isDemo = inputMode === "demo";

  const sourceName = isDemo ? `Demo: ${DEMOS[demoScenario].label}` : uploadedFile?.name || "No document selected";
  const traceByAgent = useMemo(() => Object.fromEntries((result?.execution_trace || []).map((item) => [item.agent, item])), [result]);

  function chooseFile(file) {
    setUploadedFile(file || null);
    setDocumentText("");
    setResult(null);
    setSelectedAgent(null);
    setInputMode("upload");
  }
  function chooseDemo(id) {
    setDemoScenario(id);
    setDocumentText(DEMOS[id].text);
    setResult(null);
    setSelectedAgent(null);
  }

  async function analyze() {
    if (!isDemo && !uploadedFile) return;
    setBusy(true); setResult(null); setSelectedAgent(null);
    try {
      let response;
      if (isDemo) {
        response = await fetch(`${apiBase}/process`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ document_id: `DEMO-${Date.now()}`, text: DEMOS[demoScenario].text }) });
      } else {
        const form = new FormData(); form.append("document_id", `DOC-${Date.now()}`); form.append("file", uploadedFile);
        response = await fetch(`${apiBase}/process/upload`, { method: "POST", body: form });
      }
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
      setResult(data);
      // This changes only when this exact document analysis completes.
      setDocumentText(data.source_text || data.original_text || "");
    } catch (error) { window.alert(`Analysis failed: ${error.message}`); }
    finally { setBusy(false); }
  }

  return <main className="app-shell">
    <header><p className="eyebrow">RESEARCH / DEMO ONLY</p><h1>Clinical document analysis</h1><p>Upload a document. The orchestrator selects and records the evidence-based execution path.</p></header>
    <section className="mode-switch" aria-label="Input mode"><button className={!isDemo ? "active" : ""} onClick={() => setInputMode("upload")}>Upload document</button><button className={isDemo ? "active" : ""} onClick={() => setInputMode("demo")}>Demo scenario</button></section>
    <div className="top-grid">
      <SourcePanel isDemo={isDemo} demoScenario={demoScenario} setDemoScenario={chooseDemo} uploadedFile={uploadedFile} chooseFile={chooseFile} sourceName={sourceName} text={isDemo && !documentText ? DEMOS[demoScenario].text : documentText} result={result} busy={busy} analyze={analyze} />
      <TracePanel traceByAgent={traceByAgent} selectedAgent={selectedAgent} setSelectedAgent={setSelectedAgent} />
      <AuditPanel audit={result?.audit_trail || []} replans={result?.replans || []} />
    </div>
    {result && <AnalysisResult result={result} tab={activeTab} setTab={setActiveTab} />}
    {selectedAgent && <Inspector item={traceByAgent[selectedAgent]} close={() => setSelectedAgent(null)} sourceName={sourceName} />}
  </main>;
}

function SourcePanel({ isDemo, demoScenario, setDemoScenario, uploadedFile, chooseFile, sourceName, text, result, busy, analyze }) {
  const analysis = result?.document_analysis;
  return <section className="panel source"><h2>Source document</h2><span className="badge">{isDemo ? "DEMO MODE" : "REAL DOCUMENT MODE"}</span>
    {isDemo ? <><label>Demo scenario<select value={demoScenario} onChange={(e) => setDemoScenario(e.target.value)}>{Object.entries(DEMOS).map(([id, scenario]) => <option key={id} value={id}>{scenario.label}</option>)}</select></label><p className="hint">Demo text is isolated from uploaded documents.</p></> : <><label className="upload">Upload PDF, PNG, or JPG<input type="file" accept="application/pdf,image/png,image/jpeg" onChange={(e) => chooseFile(e.target.files?.[0])} /></label><p className="file-name">{uploadedFile ? `Selected: ${uploadedFile.name}` : "Choose a document to begin."}</p></>}
    <div className="source-meta"><strong>{sourceName}</strong>{analysis && <><span>Type: {prettify(analysis.document_type)}</span><span>Method: {result.ocr_result ? "OCR" : "Native / provided text"}</span>{result.ocr_result && <span>OCR confidence: {confidence(result.ocr_result.overall_confidence)}</span>}</>}</div>
    <label>Extracted source text<textarea value={text} readOnly placeholder="The source text is displayed here after analysis; it is never changed by execution-path controls." rows="14" /></label>
    <button className="primary" disabled={busy || (!isDemo && !uploadedFile)} onClick={analyze}>{busy ? "Analyzing…" : "Analyze document →"}</button>
  </section>;
}

function TracePanel({ traceByAgent, selectedAgent, setSelectedAgent }) {
  return <section className="panel"><h2>Observed execution trace</h2><p className="hint">Statuses and inspectors are returned by the backend.</p>{AGENTS.map(([id, label]) => {
    const item = traceByAgent[id]; const complete = item?.status === "completed";
    return (<button key={id} className={`trace-row ${complete ? "done" : "skipped"} ${selectedAgent === id ? "selected" : ""}`} onClick={() => item && setSelectedAgent(id)} disabled={!item}>
      <span>{complete ? "✓" : "○"}</span><span><strong>{label}</strong><small>{item ? (complete ? item.reason : `Not dispatched — ${item.reason}`) : "Run an analysis to view runtime status."}</small></span>{item && <span className="inspect">Inspect</span>}
    </button>);
  })}</section>;
}

function AuditPanel({ audit, replans }) { return <section className="panel audit"><h2>Audit trail</h2>{replans.length > 0 && <div className="replan"><strong>Re-planning recorded</strong>{replans.map((r, i) => <p key={i}>{r.strategy}</p>)}</div>}{audit.length ? audit.map((event) => <article key={event.id}><time>{new Date(event.timestamp).toLocaleTimeString()}</time><strong>{prettify(event.agent_name)}</strong><span>{prettify(event.action_type)}</span><p>{event.details?.message || event.details?.reason || JSON.stringify(event.details)}</p></article>) : <p className="hint">The complete audit appears after analysis.</p>}</section> }

function AnalysisResult({ result, tab, setTab }) {
  const final = result.final_result || {}; const tabs = ["Overview", "Entities", "Medications", "Relations", "Grounding", "Verification", "Provenance"];
  const content = {
    Overview: <div className="metrics"><Metric label="Document" value={prettify(result.document_analysis?.document_type || "unknown")} /><Metric label="Entities" value={result.extracted_entities?.length || 0} /><Metric label="Medications" value={result.medications?.length || 0} /><Metric label="Relations" value={result.relations?.length || 0} /><Metric label="Verification" value={final.verification?.status || "Pending"} /></div>,
    Entities: <EntityList entities={result.extracted_entities || []} />,
    Medications: <MedicationTable medications={result.medications || []} />,
    Relations: <JsonView value={result.relations || []} empty="No evidence-backed relations found." />,
    Grounding: <JsonView value={final.grounded_concepts || []} empty="No grounded concepts returned." />,
    Verification: <JsonView value={final.verification || {}} empty="No verification output." />,
    Provenance: <JsonView value={final.provenance || {}} empty="No provenance output." />,
  };
  return <section className="result"><h2>Analysis result</h2><p className="disclaimer">{final.disclaimer}</p><nav>{tabs.map((name) => <button key={name} className={tab === name ? "active" : ""} onClick={() => setTab(name)}>{name}</button>)}</nav><div className="result-body">{content[tab]}</div></section>;
}
function Metric({ label, value }) { return <div><small>{label}</small><strong>{value}</strong></div> }
function EntityList({ entities }) { return entities.length ? <div className="cards">{entities.map((e) => <article key={e.id}><strong>{e.text}</strong><span>{e.label} · {confidence(e.confidence)}</span><small>Page {e.provenance?.page_number || "not specified"}; span {e.start_char}–{e.end_char}</small></article>)}</div> : <p>No entities found.</p> }
function MedicationTable({ medications }) { return medications.length ? <div className="table-wrap"><table><thead><tr><th>Drug</th><th>Dose</th><th>Route</th><th>Frequency</th><th>Duration</th><th>Confidence</th></tr></thead><tbody>{medications.map((m, i) => <tr key={i}><td>{m.drug}</td><td>{m.dose || "Not stated"}</td><td>{m.route || "Not stated"}</td><td>{m.frequency || "Not stated"}</td><td>{m.duration || "Not stated"}</td><td>{confidence(m.confidence)}</td></tr>)}</tbody></table></div> : <p>No medication records found.</p> }
function JsonView({ value, empty }) { return Array.isArray(value) && !value.length ? <p>{empty}</p> : <pre>{JSON.stringify(value, null, 2)}</pre> }
function Inspector({ item, close, sourceName }) { const output = item?.output; return <div className="overlay" role="dialog" aria-modal="true"><section className="inspector"><button className="close" onClick={close}>×</button><p className="eyebrow">AGENT INSPECTOR</p><h2>{prettify(item.agent)}</h2><dl><dt>Status</dt><dd>{item.status}</dd><dt>Dispatch reason</dt><dd>{item.reason}</dd><dt>Source</dt><dd>{sourceName}</dd></dl><h3>Actual backend output</h3><pre>{JSON.stringify(output, null, 2)}</pre></section></div> }
