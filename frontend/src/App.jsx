import { useMemo, useState } from "react";
import "./App.css";

const AGENTS = [
  ["document", "Document agent"], ["ocr", "OCR agent"], ["orchestrator", "Orchestrator"], ["ner", "NER agent"],
  ["medication", "Medication agent"], ["clinical_context", "Clinical context"], ["relation", "Relation agent"],
  ["timeline", "Timeline agent"], ["grounding", "Grounding agent"], ["summary", "Summary agent"], ["verifier", "Verifier / critic"],
];

const SAMPLE_CASES = [
  {
    id: "routine-follow-up",
    label: "Routine follow-up",
    text: "Patient returns for seasonal allergic rhinitis follow-up. Symptoms are controlled. Continue loratadine 10 mg once daily.",
  },
  {
    id: "discharge-summary",
    label: "Multi-system discharge",
    text: `Discharge summary: admitted with community-acquired pneumonia and chronic kidney disease.
History: hypertension and type 2 diabetes.
Hospital course: treated with ceftriaxone, then transitioned to amoxicillin.
Medications: amoxicillin 500 mg three times daily, lisinopril 10 mg daily, metformin 500 mg twice daily.
Labs: creatinine 1.3 mg/dL, sodium 138 mmol/L.
Diagnoses: pneumonia, chronic kidney disease, diabetes, hypertension.`,
  },
  {
    id: "dosage-conflict",
    label: "Conflicting medication doses",
    text: `Discharge summary: patient with type 2 diabetes and heart failure.
Metformin was held during admission and resumed at discharge.
Medication list: metformin 500 mg twice daily and metformin 2000 mg once daily.
Also taking furosemide 40 mg daily.
Creatinine 1.1 mg/dL.`,
  },
];

const apiBase = import.meta.env.VITE_BACKEND_URL || "/api";

function prettify(value) { return String(value || "").replaceAll("_", " "); }
function confidence(value) { return value == null ? "Not available" : `${Math.round(value * 100)}%`; }

export default function App() {
  const [inputMode, setInputMode] = useState("text");
  const [uploadedFile, setUploadedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [documentText, setDocumentText] = useState("");
  const [selectedSample, setSelectedSample] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [activeTab, setActiveTab] = useState("Summary");
  const [durationMs, setDurationMs] = useState(null);
  const [reviewedFlags, setReviewedFlags] = useState({});

  const sourceName = inputMode === "upload" ? (uploadedFile?.name || "No document selected") : "Clinical Note Entry";
  const traceByAgent = useMemo(() => Object.fromEntries((result?.execution_trace || []).map((item) => [item.agent, item])), [result]);

  function chooseFile(file) {
    setUploadedFile(file || null);
    if (file && file.type.startsWith("image/")) {
      setPreviewUrl(URL.createObjectURL(file));
    } else {
      setPreviewUrl(null);
    }
    setDocumentText("");
    setSelectedSample("");
    setResult(null);
    setSelectedAgent(null);
    setInputMode("upload");
  }

  function loadSample(sampleId) {
    const sample = SAMPLE_CASES.find((item) => item.id === sampleId);
    if (!sample) {
      setSelectedSample("");
      return;
    }
    setSelectedSample(sample.id);
    setDocumentText(sample.text);
    setResult(null);
    setSelectedAgent(null);
  }

  async function analyze() {
    if (inputMode === "text" && !documentText.trim()) return;
    if (inputMode === "upload" && !uploadedFile) return;
    const startedAt = performance.now();
    setBusy(true); setResult(null); setSelectedAgent(null);
    setDurationMs(null);
    setReviewedFlags({});
    try {
      let response;
      if (inputMode === "upload") {
        const form = new FormData();
        form.append("document_id", `DOC-${Date.now()}`);
        form.append("file", uploadedFile);
        response = await fetch(`${apiBase}/process/upload`, { method: "POST", body: form });
      } else {
        response = await fetch(`${apiBase}/process`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ document_id: `FREE-${Date.now()}`, text: documentText })
        });
      }
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
      setResult(data);
      setDocumentText(data.source_text || data.original_text || "");
      setActiveTab("Summary");
    } catch (error) {
      window.alert(`Analysis failed: ${error.message}`);
    } finally {
      setDurationMs(Math.round(performance.now() - startedAt));
      setBusy(false);
    }
  }

  function resolveFlag(flagId, status) {
    setReviewedFlags((previous) => ({ ...previous, [flagId]: status }));
  }

  function downloadAuditTrail() {
    if (!result) return;
    const payload = {
      document_id: result.document_id,
      sample: selectedSample || null,
      duration_ms: durationMs,
      flags: result.verifier_flags || [],
      review_decisions: reviewedFlags,
      events: result.audit_trail || [],
      report: result,
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${String(result.document_id || "report").toLowerCase()}-audit-trail.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="app-shell">
      <header>
        <p className="eyebrow">CLINICAL INTELLIGENCE PLATFORM · MULTI-AGENT ARCHITECTURE</p>
        <h1>Clinical Document Understanding & Decision Support</h1>
        <p>Intelligent extraction, multimodal OCR transcription, ontology grounding, and safety verification for clinical documentation.</p>
      </header>

      <section className="mode-switch" aria-label="Input mode">
        <button className={inputMode === "text" ? "active" : ""} onClick={() => setInputMode("text")}>✍️ Clinical Text Entry</button>
        <button className={inputMode === "upload" ? "active" : ""} onClick={() => setInputMode("upload")}>📄 Document Scan / PDF (OCR)</button>
      </section>

      <div className="top-grid">
        <SourcePanel
          inputMode={inputMode}
          selectedSample={selectedSample}
          loadSample={loadSample}
          clearSelectedSample={() => setSelectedSample("")}
          uploadedFile={uploadedFile}
          previewUrl={previewUrl}
          chooseFile={chooseFile}
          sourceName={sourceName}
          text={documentText}
          setText={setDocumentText}
          result={result}
          busy={busy}
          analyze={analyze}
        />
        <TracePanel traceByAgent={traceByAgent} selectedAgent={selectedAgent} setSelectedAgent={setSelectedAgent} />
        <AuditPanel
          audit={result?.audit_trail || []}
          replans={result?.replans || []}
          onExport={downloadAuditTrail}
          canExport={Boolean(result)}
        />
      </div>

      {result && (
        <AnalysisResult
          result={result}
          tab={activeTab}
          setTab={setActiveTab}
          durationMs={durationMs}
          reviewedFlags={reviewedFlags}
          resolveFlag={resolveFlag}
        />
      )}
      {selectedAgent && <Inspector item={traceByAgent[selectedAgent]} close={() => setSelectedAgent(null)} sourceName={sourceName} />}
    </main>
  );
}

function SourcePanel({
  inputMode, selectedSample, loadSample, clearSelectedSample, uploadedFile, previewUrl,
  chooseFile, sourceName, text, setText, result, busy, analyze,
}) {
  const analysis = result?.document_analysis;
  return (
    <section className="panel source">
      <h2>Clinical Intake</h2>
      <span className="badge">
        {inputMode === "text" ? "DIRECT TEXT ENTRY" : "DOCUMENT SCAN / OCR"}
      </span>

      {inputMode === "text" && (
        <label>Sample case
          <select value={selectedSample} onChange={(event) => loadSample(event.target.value)}>
            <option value="">Choose a sample case...</option>
            {SAMPLE_CASES.map((sample) => (
              <option key={sample.id} value={sample.id}>{sample.label}</option>
            ))}
          </select>
        </label>
      )}

      {inputMode === "upload" && (
        <>
          <label className="upload">Upload Prescription / Lab (PNG, JPG, PDF)
            <input type="file" accept="application/pdf,image/png,image/jpeg" onChange={(e) => chooseFile(e.target.files?.[0])} />
          </label>
          {previewUrl && (
            <div className="preview-container">
              <small>Document Scan Preview:</small>
              <img src={previewUrl} alt="Uploaded preview" className="doc-preview" />
            </div>
          )}
          <p className="file-name">{uploadedFile ? `Selected: ${uploadedFile.name}` : "Choose a scanned image or PDF to begin."}</p>
        </>
      )}

      <div className="source-meta">
        <strong>{sourceName}</strong>
        {analysis && (
          <>
            <span>Type: <strong>{prettify(analysis.document_type)}</strong></span>
            <span>Intake Method: <strong>{result.ocr_result ? "High-Resolution OCR" : "Native Text Gating"}</strong></span>
            {result.ocr_result && <span>OCR Confidence: <strong>{confidence(result.ocr_result.overall_confidence)}</strong></span>}
          </>
        )}
      </div>

      <label>Clinical Document Text:
        <textarea
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            clearSelectedSample();
          }}
          placeholder="Type or paste any prescription, clinical note, diagnosis, or patient scenario here freely..."
          rows="12"
        />
      </label>
      <button className="primary" disabled={busy || (inputMode === "upload" ? !uploadedFile : !text.trim())} onClick={analyze}>
        {busy ? "Executing Multi-Agent Graph…" : "Run Clinical Analysis →"}
      </button>
    </section>
  );
}

function TracePanel({ traceByAgent, selectedAgent, setSelectedAgent }) {
  return (
    <section className="panel">
      <h2>Multi-Agent Trace</h2>
      <p className="hint">Live execution plan and agent dispatch statuses:</p>
      {AGENTS.map(([id, label]) => {
        const item = traceByAgent[id];
        const complete = item?.status === "completed";
        return (
          <button
            key={id}
            className={`trace-row ${complete ? "done" : "skipped"} ${selectedAgent === id ? "selected" : ""}`}
            onClick={() => item && setSelectedAgent(id)}
            disabled={!item}
          >
            <span>{complete ? "✓" : "○"}</span>
            <span>
              <strong>{label}</strong>
              <small>{item ? (complete ? item.reason : `Not dispatched — ${item.reason}`) : "Awaiting execution."}</small>
            </span>
            {item && <span className="inspect">Inspect</span>}
          </button>
        );
      })}
    </section>
  );
}

function AuditPanel({ audit, replans, onExport, canExport }) {
  return (
    <section className="panel audit">
      <div className="audit-heading">
        <h2>Audit & Safety Trail</h2>
        {canExport && <button onClick={onExport}>Export JSON</button>}
      </div>
      {replans.length > 0 && (
        <div className="replan">
          <strong>Re-planning Recorded</strong>
          {replans.map((r, i) => <p key={i}>{r.strategy}</p>)}
        </div>
      )}
      {audit.length ? (
        audit.map((event) => (
          <article key={event.id}>
            <time>{new Date(event.timestamp).toLocaleTimeString()}</time>
            <strong>{prettify(event.agent_name)}</strong>
            <span>{prettify(event.action_type)}</span>
            <p>{event.details?.message || event.details?.reason || JSON.stringify(event.details)}</p>
          </article>
        ))
      ) : (
        <p className="hint">The immutable audit log is generated during pipeline execution.</p>
      )}
    </section>
  );
}

function AnalysisResult({ result, tab, setTab, durationMs, reviewedFlags, resolveFlag }) {
  const final = result.final_result || {};
  const tabs = ["Summary", "Overview", "Entities", "Medications", "Relations", "Grounding", "Verification", "Provenance"];

  const content = {
    Summary: <ClinicalSummaryView summary={result.summary} />,
    Overview: (
      <div className="metrics">
        <Metric label="Document Type" value={prettify(result.document_analysis?.document_type || "unknown")} />
        <Metric label="Entities Found" value={result.extracted_entities?.length || 0} />
        <Metric label="Medications" value={result.medications?.length || 0} />
        <Metric label="Relations" value={result.relations?.length || 0} />
        <Metric label="Verification Status" value={final.verification?.status || "PASS"} />
      </div>
    ),
    Entities: <EntityList entities={result.extracted_entities || []} />,
    Medications: <MedicationTable medications={result.medications || []} />,
    Relations: <RelationsList relations={result.relations || []} entities={result.extracted_entities || []} />,
    Grounding: <GroundingList concepts={final.grounded_concepts || []} entities={result.extracted_entities || []} />,
    Verification: (
      <VerificationView
        flags={result.verifier_flags || []}
        status={final.verification?.status}
        reviewedFlags={reviewedFlags}
        resolveFlag={resolveFlag}
      />
    ),
    Provenance: <ProvenanceList entities={result.extracted_entities || []} ocrResult={result.ocr_result} />,
  };

  return (
    <section className="result">
      <h2>Clinical Decision Support Output</h2>
      <p className="disclaimer">{final.disclaimer || "Document understanding research demo only; not clinical advice."}</p>
      <p className="hint">
        Document {result.document_id}
        {durationMs != null ? ` · processed in ${(durationMs / 1000).toFixed(1)}s` : ""}
      </p>
      <nav>
        {tabs.map((name) => (
          <button key={name} className={tab === name ? "active" : ""} onClick={() => setTab(name)}>
            {name}
          </button>
        ))}
      </nav>
      <div className="result-body">{content[tab]}</div>
    </section>
  );
}

function Metric({ label, value }) {
  return <div><small>{label}</small><strong>{value}</strong></div>;
}

function ClinicalSummaryView({ summary }) {
  if (!summary) return <p>No clinical summary generated.</p>;
  return (
    <div className="summary-box">
      <pre className="summary-content">{summary}</pre>
    </div>
  );
}

function EntityList({ entities }) {
  return entities.length ? (
    <div className="cards">
      {entities.map((e) => (
        <article key={e.id}>
          <strong>{e.text}</strong>
          <span className={`label-badge label-${e.label.toLowerCase()}`}>{e.label} · {confidence(e.confidence)}</span>
          <small>
            {e.provenance?.page_number ? `Page ${e.provenance.page_number}` : "User Text"}
            {e.provenance?.bbox ? ` | Bounding Box: [${e.provenance.bbox.join(", ")}]` : ""}
          </small>
        </article>
      ))}
    </div>
  ) : <p>No entities found.</p>;
}

function MedicationTable({ medications }) {
  return medications.length ? (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Drug</th>
            <th>Dose</th>
            <th>Route</th>
            <th>Frequency</th>
            <th>Duration</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {medications.map((m, i) => (
            <tr key={i}>
              <td><strong>{m.drug}</strong></td>
              <td>{m.dose || "—"}</td>
              <td>{m.route || "—"}</td>
              <td>{m.frequency || "—"}</td>
              <td>{m.duration || "—"}</td>
              <td>{confidence(m.confidence)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : <p>No medication records found.</p>;
}

function RelationsList({ relations, entities }) {
  const entityMap = useMemo(() => Object.fromEntries(entities.map((e) => [e.id, e.text])), [entities]);
  if (!relations.length) return <p>No evidence-backed clinical relations found.</p>;

  return (
    <div className="relation-grid">
      {relations.map((rel) => {
        const source = entityMap[rel.source_entity_id] || rel.source_entity_id;
        const target = entityMap[rel.target_entity_id] || rel.target_entity_id;
        return (
          <div key={rel.id} className="relation-card">
            <span className="rel-entity">{source}</span>
            <span className={`rel-type rel-${rel.relation_type.toLowerCase()}`}>{rel.relation_type}</span>
            <span className="rel-entity">{target}</span>
          </div>
        );
      })}
    </div>
  );
}

function GroundingList({ concepts, entities }) {
  const groundedEntities = entities.filter((e) => e.grounding);
  if (!groundedEntities.length && !concepts.length) return <p>No mapped ontology concepts.</p>;

  return (
    <div className="cards">
      {groundedEntities.map((e) => (
        <article key={e.id}>
          <strong>{e.text}</strong>
          <span className="ontology-tag">{e.grounding.ontology}: {e.grounding.code}</span>
          <small>{e.grounding.name}</small>
        </article>
      ))}
    </div>
  );
}

function VerificationView({ flags, status, reviewedFlags, resolveFlag }) {
  return (
    <div className="verification-container">
      <div className={`verification-banner ${status === "NEEDS_REVIEW" ? "banner-warning" : "banner-pass"}`}>
        <strong>Status: {status || "PASS"}</strong>
        <span>{status === "NEEDS_REVIEW" ? "Human-In-The-Loop review recommended" : "All safety checks verified"}</span>
      </div>
      {flags.length > 0 ? (
        <div className="flags-list">
          {flags.map((f) => {
            const review = reviewedFlags[f.id];
            return (
              <div key={f.id} className="flag-card">
                <span className={`flag-status ${f.status === "NEEDS_REVIEW" ? "status-warning" : "status-error"}`}>{f.status}</span>
                <strong>Check: {f.check_type}</strong>
                <p>{f.justification}</p>
                <small>Confidence Score: {confidence(f.confidence_score)}</small>
                <div className="review-actions">
                  {review ? (
                    <span>Locally marked {review}; the stored report is unchanged.</span>
                  ) : (
                    <>
                      <button onClick={() => resolveFlag(f.id, "approved")}>Approve</button>
                      <button onClick={() => resolveFlag(f.id, "rejected")}>Reject</button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p style={{ marginTop: "14px", color: "#76d7a5" }}>✓ No safety contraindications, dosage contradictions, or OCR uncertainties detected.</p>
      )}
    </div>
  );
}

function ProvenanceList({ entities, ocrResult }) {
  return (
    <div>
      <div style={{ marginBottom: "14px" }}>
        <strong>OCR Extraction Method:</strong> {ocrResult ? "Windows Native OCR (winocr) & High-Resolution Renderer" : "Native Digital PDF Text Gating"}
        {ocrResult && <span> | Overall Recognition Confidence: {confidence(ocrResult.overall_confidence)}</span>}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Entity</th>
              <th>Type</th>
              <th>Source Kind</th>
              <th>Page</th>
              <th>Bounding Box [x1, y1, x2, y2]</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {entities.map((e) => (
              <tr key={e.id}>
                <td><strong>{e.text}</strong></td>
                <td>{e.label}</td>
                <td>{e.provenance?.source_kind || "text"}</td>
                <td>{e.provenance?.page_number || "1"}</td>
                <td><code>{e.provenance?.bbox ? `[${e.provenance.bbox.join(", ")}]` : "N/A"}</code></td>
                <td>{confidence(e.provenance?.ocr_confidence || e.confidence)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Inspector({ item, close, sourceName }) {
  const output = item?.output;
  return (
    <div className="overlay" role="dialog" aria-modal="true">
      <section className="inspector">
        <button className="close" onClick={close}>×</button>
        <p className="eyebrow">AGENT INSPECTOR</p>
        <h2>{prettify(item.agent)}</h2>
        <dl>
          <dt>Status</dt>
          <dd>{item.status}</dd>
          <dt>Dispatch reason</dt>
          <dd>{item.reason}</dd>
          <dt>Source</dt>
          <dd>{sourceName}</dd>
        </dl>
        <h3>Actual backend output</h3>
        <pre>{JSON.stringify(output, null, 2)}</pre>
      </section>
    </div>
  );
}
