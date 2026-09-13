"""Interactive Web Dashboard for Clinical Multi-Agent Document Understanding.
Served directly by FastAPI at http://localhost:8000/
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Clinical Document Analysis | Multi-Agent System</title>
  <style>
    :root {
      --bg: #0d1117; --panel-bg: #161b22; --border: #30363d;
      --text: #c9d1d9; --text-bright: #f0f6fc; --accent: #58a6ff;
      --teal: #39d353; --teal-accent: #2ea043; --warning: #d29922;
      --danger: #f85149; --card-bg: #21262d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; background: var(--bg); color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
    }
    .container { max-width: 1450px; margin: 0 auto; padding: 24px 20px 60px; }
    header { border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 20px; }
    .eyebrow { color: #58a6ff; font: bold 11px ui-monospace, monospace; letter-spacing: .12em; text-transform: uppercase; margin: 0 0 4px; }
    h1 { margin: 0 0 6px; font-size: 26px; color: var(--text-bright); font-weight: 600; }
    header p { margin: 0; color: #8b949e; font-size: 14px; }

    .mode-switch { display: flex; gap: 8px; margin: 18px 0; flex-wrap: wrap; }
    button, select, textarea, input { font: inherit; }
    button {
      background: var(--card-bg); color: var(--text-bright); border: 1px solid var(--border);
      padding: 9px 16px; cursor: pointer; border-radius: 6px; transition: all 0.15s ease; font-weight: 500;
    }
    button:hover, button.active { border-color: var(--accent); color: var(--accent); background: #1f242c; }
    button:disabled { opacity: 0.45; cursor: not-allowed; }
    button.primary {
      width: 100%; margin-top: 14px; background: #238636; color: #fff;
      font-weight: 600; border-color: #2ea043; padding: 12px; font-size: 15px;
    }
    button.primary:hover:not(:disabled) { background: #2ea043; }

    .top-grid { display: grid; grid-template-columns: minmax(320px, 1.2fr) minmax(320px, 1fr) minmax(280px, .85fr); gap: 14px; align-items: start; }
    .panel, .result-panel { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 6px; padding: 18px; }
    .panel h2, .result-panel h2 { margin: 0 0 12px; font-size: 14px; text-transform: uppercase; letter-spacing: .08em; color: #8b949e; }
    .badge { color: #fff; background: #238636; padding: 4px 10px; font: bold 10px ui-monospace, monospace; border-radius: 4px; }

    .source label { display: block; margin: 14px 0 6px; color: var(--text-bright); font-size: 13px; font-weight: 500; }
    .source select, .source textarea {
      width: 100%; background: #0d1117; color: var(--text-bright); border: 1px solid var(--border);
      padding: 12px; border-radius: 6px; font-family: inherit; font-size: 13px;
    }
    .source textarea { resize: vertical; font-family: ui-monospace, monospace; font-size: 13px; line-height: 1.6; }
    .source textarea:focus { outline: none; border-color: var(--accent); }
    .source-meta {
      display: grid; gap: 5px; margin: 12px 0; background: #0d1117; padding: 10px;
      border-radius: 6px; border: 1px solid var(--border); font-size: 12px; font-family: ui-monospace, monospace;
    }
    .source-meta strong { color: var(--accent); }
    .preview-box { margin: 10px 0; padding: 8px; background: #0d1117; border: 1px solid var(--border); border-radius: 6px; }
    .preview-box img { max-width: 100%; max-height: 150px; object-fit: contain; display: block; border-radius: 4px; }

    .trace-row {
      width: 100%; display: grid; grid-template-columns: 24px 1fr auto; text-align: left;
      margin: 6px 0; padding: 9px 12px; border-radius: 6px; border: 1px solid var(--border);
      background: var(--card-bg); font-size: 13px;
    }
    .trace-row small { display: block; margin-top: 2px; color: #8b949e; font-size: 11px; }
    .trace-row.done > span:first-child { color: var(--teal); font-weight: bold; }
    .trace-row.skipped { opacity: 0.6; }
    .trace-row.selected { border-color: var(--accent); background: #1c2634; }
    .inspect-btn { font-size: 11px; color: var(--accent); text-decoration: underline; background: none; border: 0; padding: 0; cursor: pointer; }

    .audit { max-height: 650px; overflow-y: auto; font-size: 12px; }
    .audit-item { padding: 10px 0; border-bottom: 1px solid var(--border); display: grid; grid-template-columns: 75px 1fr; gap: 4px 8px; }
    .audit-item time, .audit-item span { color: #8b949e; }
    .audit-item p { grid-column: 1 / -1; margin: 2px 0; color: var(--text-bright); }

    .result-panel { margin-top: 20px; }
    .tabs { display: flex; gap: 8px; border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    .metrics { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }
    .metric-card { min-width: 130px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
    .metric-card small { display: block; color: #8b949e; font-size: 11px; }
    .metric-card strong { display: block; font-size: 18px; color: var(--accent); margin-top: 4px; }

    .cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
    .entity-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
    .entity-card strong { color: var(--text-bright); display: block; font-size: 14px; }
    .tag { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: bold; text-transform: uppercase; margin-top: 6px; }
    .tag-medication { background: #1f3d32; color: #7ee787; border: 1px solid #2ea043; }
    .tag-diagnosis { background: #3d2325; color: #ff7b72; border: 1px solid #da3633; }
    .tag-symptom { background: #392b1a; color: #f2cc60; border: 1px solid #bb8009; }
    .tag-lab_result { background: #192d42; color: #79c0ff; border: 1px solid #388bfd; }
    .ontology-pill { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 11px; background: #1c2b36; color: #80ded4; border: 1px solid #3d636b; font-family: ui-monospace, monospace; margin-top: 4px; }

    .relation-row { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; margin-bottom: 8px; font-size: 13px; }
    .rel-badge { font-size: 10px; font-weight: bold; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; }
    .rel-treats { background: #19382b; color: #7ee787; border: 1px solid #238636; }
    .rel-causes { background: #3c1e21; color: #ff7b72; border: 1px solid #da3633; }
    .rel-indicates { background: #1f2d40; color: #79c0ff; border: 1px solid #388bfd; }

    .banner { padding: 12px 16px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; font-weight: 500; }
    .banner-pass { background: #12281e; border: 1px solid #238636; color: #7ee787; }
    .banner-warning { background: #33200f; border: 1px solid #bb8009; color: #e3b341; }
    .flag-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; margin-bottom: 8px; }
    .flag-card strong { color: var(--text-bright); display: block; }
    .flag-card p { margin: 4px 0; color: #c9d1d9; font-size: 13px; }

    .summary-box { background: #0d1117; border: 1px solid var(--border); border-radius: 6px; padding: 16px; font-family: ui-monospace, monospace; font-size: 13px; white-space: pre-wrap; line-height: 1.6; }

    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 10px 12px; border-bottom: 1px solid var(--border); text-align: left; }
    th { color: var(--accent); background: var(--card-bg); font-weight: 600; }
    tbody tr:hover { background: #1f242c; }
    code { font-family: ui-monospace, monospace; font-size: 11px; background: #0d1117; padding: 2px 5px; border-radius: 4px; border: 1px solid var(--border); }

    .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.75); display: grid; place-items: center; padding: 20px; z-index: 100; }
    .modal-content { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 8px; padding: 22px; max-width: 760px; width: 100%; max-height: 85vh; overflow-y: auto; position: relative; }
    .modal-close { position: absolute; top: 14px; right: 16px; font-size: 20px; background: none; border: 0; color: #8b949e; cursor: pointer; }
    pre { background: #0d1117; border: 1px solid var(--border); border-radius: 6px; padding: 12px; overflow-x: auto; font-size: 12px; }

    .helper-text { font-size: 12px; color: #8b949e; margin-top: 4px; }

    @media (max-width: 980px) { .top-grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="eyebrow">CLINICAL INTELLIGENCE PLATFORM · MULTI-AGENT ARCHITECTURE</div>
      <h1>Clinical Document Understanding & Decision Support</h1>
      <p>Intelligent extraction, multimodal OCR transcription, ontology grounding, and safety verification for clinical documentation.</p>
    </header>

    <div class="mode-switch">
      <button id="btnText" class="active" onclick="setMode('text')">✍️ Clinical Text Entry</button>
      <button id="btnUpload" onclick="setMode('upload')">📄 Document Scan / PDF (OCR)</button>
    </div>

    <div class="top-grid">
      <!-- 1. Source Panel -->
      <section class="panel source">
        <h2>Clinical Intake</h2>
        <span id="modeBadge" class="badge">DIRECT TEXT ENTRY</span>

        <!-- Free Text Mode -->
        <div id="freeTextSection">
          <label for="sourceTextArea">Enter or Paste Clinical Text / Prescription:
            <span class="helper-text">(Type or paste patient notes, discharge orders, or clinical records)</span>
          </label>
        </div>

        <!-- Upload Mode -->
        <div id="uploadSection" style="display:none;">
          <label>Upload Clinical Record / Prescription (PNG, JPG, PDF):
            <input type="file" id="fileInput" accept="application/pdf,image/png,image/jpeg" onchange="handleFileSelect(event)" style="display:block; margin-top:8px;" />
          </label>
          <div id="previewBox" class="preview-box" style="display:none;">
            <small style="color:#8b949e; display:block; margin-bottom:4px;">Document Preview:</small>
            <img id="previewImg" src="" alt="Document preview" />
          </div>
          <p id="fileNameText" style="font-size:12px; color:#8b949e; font-family:ui-monospace, monospace;">Select a document or prescription image to process.</p>
        </div>

        <!-- The Editable Text Area -->
        <div style="margin-top: 10px;">
          <textarea id="sourceTextArea" rows="12" placeholder="Type or paste ANY prescription, clinical note, diagnosis, or patient scenario here freely...&#10;&#10;Example:&#10;Patient John Doe (Age 55)&#10;Prescribed Metformin 500 mg oral twice daily for Type 2 Diabetes Mellitus.&#10;Also prescribed Lisinopril 10 mg oral once daily for Hypertension."></textarea>
        </div>

        <div class="source-meta" id="sourceMeta">
          <strong id="metaDocName">Custom Clinical Input</strong>
          <span id="metaDocType">Type: Direct Clinical Text</span>
          <span id="metaMethod">Intake Method: Direct Input / Gating</span>
          <span id="metaConfidence">OCR Confidence: N/A</span>
        </div>

        <button id="btnAnalyze" class="primary" onclick="runAnalysis()">Run Clinical Analysis →</button>
      </section>

      <!-- 2. Trace Panel -->
      <section class="panel">
        <h2>Multi-Agent Execution Trace</h2>
        <p style="font-size:12px; color:#8b949e; margin-top:0;">Live execution plan and specialist dispatch status:</p>
        <div id="traceList"></div>
      </section>

      <!-- 3. Audit Panel -->
      <section class="panel audit">
        <h2>Audit & Safety Trail</h2>
        <div id="auditList">
          <p style="color:#8b949e; font-size:12px;">Run an analysis to observe immutable agent decision logs.</p>
        </div>
      </section>
    </div>

    <!-- Results Panel -->
    <section class="result-panel" id="resultPanel" style="display:none;">
      <h2>Clinical Decision Support Output</h2>
      <p style="color:#8b949e; font-size:12px; margin-bottom:14px;">Automated clinical information extraction for physician review and documentation support.</p>

      <div class="metrics" id="metricsRow"></div>

      <div class="tabs" id="tabsNav">
        <button class="active" onclick="switchTab('summary')">Clinical Summary</button>
        <button onclick="switchTab('entities')">Extracted Entities</button>
        <button onclick="switchTab('medications')">Medications</button>
        <button onclick="switchTab('relations')">Clinical Relations</button>
        <button onclick="switchTab('grounding')">Ontology Grounding</button>
        <button onclick="switchTab('verification')">Safety Verification</button>
        <button onclick="switchTab('provenance')">Visual Provenance</button>
      </div>

      <div id="tabContent"></div>
    </section>
  </div>

  <!-- Agent Inspector Modal -->
  <div id="inspectorModal" class="modal-overlay" style="display:none;">
    <div class="modal-content">
      <button class="modal-close" onclick="closeInspector()">×</button>
      <div class="eyebrow">AGENT INSPECTOR</div>
      <h2 id="inspectorTitle" style="margin-top:4px;">Agent</h2>
      <p id="inspectorMeta" style="font-size:12px; color:#8b949e;"></p>
      <h3>Actual Backend Output</h3>
      <pre id="inspectorBody"></pre>
    </div>
  </div>

  <script>
    const AGENTS = [
      ["document", "Document agent"], ["ocr", "OCR agent"], ["orchestrator", "Orchestrator"],
      ["ner", "NER agent"], ["medication", "Medication agent"], ["clinical_context", "Clinical context"],
      ["relation", "Relation agent"], ["timeline", "Timeline agent"], ["grounding", "Grounding agent"],
      ["summary", "Summary agent"], ["verifier", "Verifier / critic"]
    ];

    let currentMode = "text";
    let selectedFile = null;
    let latestResult = null;
    let currentTab = "summary";

    function setMode(mode) {
      currentMode = mode;
      document.getElementById("btnText").className = mode === "text" ? "active" : "";
      document.getElementById("btnUpload").className = mode === "upload" ? "active" : "";

      document.getElementById("freeTextSection").style.display = mode === "text" ? "block" : "none";
      document.getElementById("uploadSection").style.display = mode === "upload" ? "block" : "none";

      const badge = document.getElementById("modeBadge");
      const metaName = document.getElementById("metaDocName");
      const metaType = document.getElementById("metaDocType");
      const metaMethod = document.getElementById("metaMethod");
      const metaConf = document.getElementById("metaConfidence");
      const btn = document.getElementById("btnAnalyze");
      const textArea = document.getElementById("sourceTextArea");

      if (mode === "text") {
        badge.textContent = "DIRECT TEXT ENTRY";
        badge.style.background = "#238636";
        metaName.textContent = "Clinical Text Input";
        metaType.textContent = "Type: Direct Clinical Text";
        metaMethod.textContent = "Intake Method: Direct Gating";
        metaConf.textContent = "OCR Confidence: N/A";
        btn.disabled = false;
        textArea.readOnly = false;
      } else if (mode === "upload") {
        badge.textContent = "DOCUMENT SCAN / OCR";
        badge.style.background = "#1f6feb";
        metaName.textContent = selectedFile ? selectedFile.name : "No file selected";
        metaType.textContent = "Type: Awaiting File Analysis";
        metaMethod.textContent = "Intake Method: Multimodal OCR / PDF Gating";
        metaConf.textContent = "OCR Confidence: Pending";
        btn.disabled = !selectedFile;
        textArea.readOnly = false;
      }
    }

    function handleFileSelect(e) {
      const file = e.target.files[0];
      selectedFile = file || null;
      if (file) {
        document.getElementById("fileNameText").textContent = "Selected: " + file.name + " (" + (file.size / 1024).toFixed(1) + " KB)";
        document.getElementById("metaDocName").textContent = file.name;
        document.getElementById("btnAnalyze").disabled = false;
        if (file.type.startsWith("image/")) {
          document.getElementById("previewImg").src = URL.createObjectURL(file);
          document.getElementById("previewBox").style.display = "block";
        } else {
          document.getElementById("previewBox").style.display = "none";
        }
      } else {
        document.getElementById("btnAnalyze").disabled = true;
        document.getElementById("previewBox").style.display = "none";
      }
    }

    function renderTrace(traceList) {
      const traceMap = {};
      (traceList || []).forEach(item => { traceMap[item.agent] = item; });
      const container = document.getElementById("traceList");
      container.innerHTML = "";
      AGENTS.forEach(([id, label]) => {
        const item = traceMap[id];
        const done = item && item.status === "completed";
        const row = document.createElement("div");
        row.className = "trace-row " + (done ? "done" : "skipped");
        row.innerHTML = `
          <span>${done ? "✓" : "○"}</span>
          <span>
            <strong>${label}</strong>
            <small>${item ? (done ? item.reason : "Not dispatched — " + item.reason) : "Awaiting execution."}</small>
          </span>
          ${item ? `<button class="inspect-btn" onclick="openInspector('${id}')">Inspect</button>` : ""}
        `;
        container.appendChild(row);
      });
    }

    function renderAudit(auditList) {
      const container = document.getElementById("auditList");
      if (!auditList || !auditList.length) {
        container.innerHTML = "<p style='color:#8b949e; font-size:12px;'>No audit events recorded.</p>";
        return;
      }
      container.innerHTML = auditList.map(ev => `
        <div class="audit-item">
          <time>${new Date(ev.timestamp).toLocaleTimeString()}</time>
          <div>
            <strong>${ev.agent_name.replace(/_/g, " ")}</strong> · <span style="font-size:11px;">${ev.action_type}</span>
            <p>${ev.details?.message || ev.details?.reason || JSON.stringify(ev.details)}</p>
          </div>
        </div>
      `).join("");
    }

    async function runAnalysis() {
      const textArea = document.getElementById("sourceTextArea");
      const textVal = textArea.value.trim();

      if (currentMode !== "upload" && !textVal) {
        alert("Please enter or paste some clinical text to analyze!");
        return;
      }
      if (currentMode === "upload" && !selectedFile) {
        alert("Please select a file to upload!");
        return;
      }

      const btn = document.getElementById("btnAnalyze");
      btn.disabled = true;
      btn.textContent = "Executing Multi-Agent Graph…";

      try {
        let res;
        if (currentMode === "upload") {
          const form = new FormData();
          form.append("document_id", "DOC-" + Date.now());
          form.append("file", selectedFile);
          res = await fetch("/process/upload", { method: "POST", body: form });
        } else {
          // Free text or edited demo text
          res = await fetch("/process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ document_id: "FREE-" + Date.now(), text: textVal })
          });
        }

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Analysis request failed");
        
        latestResult = data;
        displayResults(data);
      } catch (err) {
        alert("Error during analysis: " + err.message);
      } finally {
        btn.disabled = false;
        btn.textContent = "Run Clinical Analysis →";
      }
    }

    function displayResults(data) {
      document.getElementById("sourceTextArea").value = data.source_text || data.original_text || "";
      if (data.document_analysis) {
        document.getElementById("metaDocType").textContent = "Type: " + data.document_analysis.document_type;
        document.getElementById("metaMethod").textContent = "Intake Method: " + (data.ocr_result ? "High-Resolution OCR (winocr)" : "Native Text Gating");
        document.getElementById("metaConfidence").textContent = "OCR Confidence: " + (data.ocr_result?.overall_confidence != null ? (data.ocr_result.overall_confidence * 100).toFixed(0) + "%" : "N/A");
      }

      renderTrace(data.execution_trace);
      renderAudit(data.audit_trail);

      // Render Metrics
      const vStatus = data.final_result?.verification?.status || "PASS";
      document.getElementById("metricsRow").innerHTML = `
        <div class="metric-card"><small>Document Type</small><strong>${data.document_analysis?.document_type || "clinical_report"}</strong></div>
        <div class="metric-card"><small>Entities Found</small><strong>${data.extracted_entities?.length || 0}</strong></div>
        <div class="metric-card"><small>Medications</small><strong>${data.medications?.length || 0}</strong></div>
        <div class="metric-card"><small>Relations</small><strong>${data.relations?.length || 0}</strong></div>
        <div class="metric-card"><small>Verification Status</small><strong style="color:${vStatus === 'PASS' ? '#39d353' : '#d29922'};">${vStatus}</strong></div>
      `;

      document.getElementById("resultPanel").style.display = "block";
      switchTab(currentTab);
    }

    function switchTab(tabName) {
      currentTab = tabName;
      const navBtns = document.getElementById("tabsNav").querySelectorAll("button");
      navBtns.forEach((btn) => {
        btn.className = (btn.textContent.toLowerCase().includes(tabName)) ? "active" : "";
      });

      const container = document.getElementById("tabContent");
      const data = latestResult;
      if (!data) return;

      if (tabName === "summary") {
        container.innerHTML = `<div class="summary-box">${data.summary || "No clinical summary generated."}</div>`;
      } else if (tabName === "entities") {
        const ents = data.extracted_entities || [];
        container.innerHTML = ents.length ? `
          <div class="cards-grid">
            ${ents.map(e => `
              <div class="entity-card">
                <strong>${e.text}</strong>
                <span class="tag tag-${e.label.toLowerCase()}">${e.label} · ${(e.confidence * 100).toFixed(0)}%</span>
                <small style="color:#8b949e; display:block; margin-top:4px;">
                  Page ${e.provenance?.page_number || 1} ${e.provenance?.bbox ? `| Bounding Box: [${e.provenance.bbox.join(", ")}]` : ""}
                </small>
              </div>
            `).join("")}
          </div>
        ` : "<p>No entities found.</p>";
      } else if (tabName === "medications") {
        const meds = data.medications || [];
        container.innerHTML = meds.length ? `
          <div style="overflow-x:auto;">
            <table>
              <thead><tr><th>Drug</th><th>Dose</th><th>Route</th><th>Frequency</th><th>Duration</th><th>Confidence</th></tr></thead>
              <tbody>
                ${meds.map(m => `
                  <tr>
                    <td><strong>${m.drug}</strong></td>
                    <td>${m.dose || "—"}</td>
                    <td>${m.route || "—"}</td>
                    <td>${m.frequency || "—"}</td>
                    <td>${m.duration || "—"}</td>
                    <td>${(m.confidence * 100).toFixed(0)}%</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        ` : "<p>No medications recorded.</p>";
      } else if (tabName === "relations") {
        const rels = data.relations || [];
        const entMap = {};
        (data.extracted_entities || []).forEach(e => { entMap[e.id] = e.text; });
        container.innerHTML = rels.length ? `
          <div>
            ${rels.map(r => `
              <div class="relation-row">
                <span style="font-weight:600; color:#f0f6fc;">${entMap[r.source_entity_id] || r.source_entity_id}</span>
                <span class="rel-badge rel-${r.relation_type.toLowerCase()}">${r.relation_type}</span>
                <span style="font-weight:600; color:#f0f6fc;">${entMap[r.target_entity_id] || r.target_entity_id}</span>
              </div>
            `).join("")}
          </div>
        ` : "<p>No clinical relations found.</p>";
      } else if (tabName === "grounding") {
        const grounded = (data.extracted_entities || []).filter(e => e.grounding);
        container.innerHTML = grounded.length ? `
          <div class="cards-grid">
            ${grounded.map(e => `
              <div class="entity-card">
                <strong>${e.text}</strong>
                <span class="ontology-pill">${e.grounding.ontology}: ${e.grounding.code}</span>
                <small style="color:#8b949e; display:block; margin-top:4px;">${e.grounding.name}</small>
              </div>
            `).join("")}
          </div>
        ` : "<p>No mapped ontology concepts.</p>";
      } else if (tabName === "verification") {
        const flags = data.verifier_flags || [];
        const status = data.final_result?.verification?.status || "PASS";
        container.innerHTML = `
          <div class="banner ${status === 'NEEDS_REVIEW' ? 'banner-warning' : 'banner-pass'}">
            <span>Status: <strong>${status}</strong> — ${status === 'NEEDS_REVIEW' ? 'Human Review Required' : 'All Safety Checks Verified'}</span>
          </div>
          ${flags.length ? flags.map(f => `
            <div class="flag-card">
              <span class="tag ${f.status === 'NEEDS_REVIEW' ? 'tag-symptom' : 'tag-diagnosis'}">${f.status}</span>
              <strong style="margin-top:6px;">Check: ${f.check_type}</strong>
              <p>${f.justification}</p>
              <small style="color:#8b949e;">Confidence: ${(f.confidence_score * 100).toFixed(0)}%</small>
            </div>
          `).join("") : `<p style="color:#39d353;">✓ No safety contraindications, dosage contradictions, or OCR uncertainties detected.</p>`}
        `;
      } else if (tabName === "provenance") {
        const ents = data.extracted_entities || [];
        container.innerHTML = `
          <div style="margin-bottom:12px; font-size:13px;">
            <strong>Intake Method:</strong> ${data.ocr_result ? "High-Resolution OCR (winocr) with Bounding Box Extraction" : "Native PDF Text Gating"}
            ${data.ocr_result ? ` | <strong>Overall OCR Confidence:</strong> ${(data.ocr_result.overall_confidence * 100).toFixed(0)}%` : ""}
          </div>
          <div style="overflow-x:auto;">
            <table>
              <thead><tr><th>Entity</th><th>Label</th><th>Source</th><th>Page</th><th>Bounding Box [x1, y1, x2, y2]</th><th>Confidence</th></tr></thead>
              <tbody>
                ${ents.map(e => `
                  <tr>
                    <td><strong>${e.text}</strong></td>
                    <td>${e.label}</td>
                    <td>${e.provenance?.source_kind || "text"}</td>
                    <td>${e.provenance?.page_number || "1"}</td>
                    <td><code>${e.provenance?.bbox ? "[" + e.provenance.bbox.join(", ") + "]" : "N/A"}</code></td>
                    <td>${((e.provenance?.ocr_confidence || e.confidence) * 100).toFixed(0)}%</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        `;
      }
    }

    function openInspector(agentId) {
      if (!latestResult) return;
      const trace = latestResult.execution_trace || [];
      const item = trace.find(t => t.agent === agentId);
      if (!item) return;

      document.getElementById("inspectorTitle").textContent = item.agent.replace(/_/g, " ").toUpperCase();
      document.getElementById("inspectorMeta").textContent = "Status: " + item.status + " | Reason: " + item.reason;
      document.getElementById("inspectorBody").textContent = JSON.stringify(item.output, null, 2);
      document.getElementById("inspectorModal").style.display = "grid";
    }

    function closeInspector() {
      document.getElementById("inspectorModal").style.display = "none";
    }

    // Default to free text mode on page load
    setMode("text");
    renderTrace([]);
  </script>
</body>
</html>
"""
