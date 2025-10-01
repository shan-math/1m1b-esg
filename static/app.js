const apiBase = "/api";

// --- Helper to format score with Risk Level
function formatScore(val) {
  let txt, color;
  if (val >= 66) { txt = "HIGH RISK"; color = "#ff6b6b"; }
  else if (val >= 33) { txt = "MED RISK"; color = "#ffb86b"; }
  else { txt = "LOW RISK"; color = "#7af27a"; }
  return `<span style="font-weight:bold;color:${color}">${val.toFixed(2)} (${txt})</span>`;
}

// --- Navigation
document.getElementById("nav-upload").onclick = () => showView("upload");
document.getElementById("nav-company").onclick = () => { showView("company"); loadCompanyList(); };
document.getElementById("nav-comparative").onclick = () => { showView("comparative"); loadComparative(); };

function showView(name) {
  document.getElementById("view-upload").style.display = name === "upload" ? "" : "none";
  document.getElementById("view-company").style.display = name === "company" ? "" : "none";
  document.getElementById("view-comparative").style.display = name === "comparative" ? "" : "none";
}

// --- Uploading a file
async function uploadFile() {
  const fileInput = document.getElementById("fileInput");
  if (!fileInput.files.length) { alert("Choose a PDF file"); return; }
  const file = fileInput.files[0];
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(apiBase + "/upload", { method: "POST", body: fd });
  const j = await res.json();
  if (j.success) {
    document.getElementById("uploadedInfo").innerText = `Uploaded: ${j.filename}`;
    document.getElementById("analyzeControls").style.display = "";
    document.getElementById("analyzeBtn").dataset.filename = j.filename;
    document.getElementById("uploadStatus").innerText = "";
  } else {
    document.getElementById("uploadStatus").innerText = "Upload failed: " + (j.message || "unknown");
  }
}
document.getElementById("uploadBtn").onclick = uploadFile;

// --- Analyzing a file
async function analyzeFile() {
  const btn = document.getElementById("analyzeBtn");
  const filename = btn.dataset.filename;
  const companyOverride = document.getElementById("companyOverride").value.trim();
  if (!filename) { alert("No uploaded file selected"); return; }
  btn.disabled = true;
  btn.innerText = "Analyzing...";
  const body = { filename };
  if (companyOverride) body.company_name = companyOverride;
  const res = await fetch(apiBase + "/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await res.json();
  btn.disabled = false;
  btn.innerText = "Analyze this file";
  if (j.success) {
    document.getElementById("uploadStatus").innerHTML =
      `Processed: ${j.processed_file} → ${j.num_records} records appended.<br/>
       <a href="/api/download/explorer">Download Explorer CSV</a> • 
       <a href="/api/download/summary">Download Summary CSV</a>`;
  } else {
    document.getElementById("uploadStatus").innerText = "Analyze failed: " + (j.message || "unknown");
  }
}
document.getElementById("analyzeBtn").onclick = analyzeFile;

// --- Company snapshot ---
async function loadCompanyList() {
  const res = await fetch(apiBase + "/companies");
  const j = await res.json();
  const sel = document.getElementById("companySelect");
  sel.innerHTML = "";
  if (j.companies.length === 0) {
    sel.innerHTML = "<option>(no companies yet)</option>";
    document.getElementById("companySnapshot").innerHTML = "<div>No data. Upload & analyze a report first.</div>";
    return;
  }
  j.companies.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c; opt.text = c;
    sel.appendChild(opt);
  });
  sel.onchange = () => showCompany(sel.value);
  showCompany(j.companies[0]);
}

async function showCompany(name) {
  const res = await fetch(apiBase + "/company/" + encodeURIComponent(name));
  const j = await res.json();
  renderCompanySnapshot(j);
}

function renderCompanySnapshot(data) {
  const div = document.getElementById("companySnapshot");
  div.innerHTML = "";

  const left = document.createElement("div"); left.className = "snapshot-left";
  const right = document.createElement("div"); right.className = "snapshot-right";

  // donut chart
  const canvas = document.createElement("canvas");
  canvas.width = 320; canvas.height = 320;
  left.appendChild(canvas);

  // heading
  const heading = document.createElement("h3");
  heading.innerText = data.company;
  left.appendChild(heading);

  // user guide box
  const guide = document.createElement("div");
  guide.className = "info-box";
  guide.innerHTML = `
    <strong>How to read these scores:</strong><br/>
    ✅ LOW RISK (green) = fewer ESG issues, stronger profile.<br/>
    ⚠️ MED RISK (yellow) = moderate ESG exposure.<br/>
    ❌ HIGH RISK (red) = frequent ESG issues flagged.<br/>
    Scores are based on ESG-related sentences in the report. Higher scores = higher risk.
  `;
  left.appendChild(guide);

  // top topics
  const topics = document.createElement("div");
  topics.className = "snapshot-list";
  topics.innerHTML = "<strong>Top flagged topics:</strong><br/>";
  if ((data.top_topics || []).length === 0) topics.innerHTML += "(none)";
  else topics.innerHTML += (data.top_topics || []).map(t => `${t.term} (${t.count})`).join(", ");
  left.appendChild(topics);

  // sentiment counts
  const sc = data.sentiment_counts || {};
  const scDiv = document.createElement("div");
  scDiv.innerHTML = `<strong>Sentiment counts</strong><br/>
    Positive: ${sc["Positive"] || 0} • Negative: ${sc["Negative"] || 0} • Neutral: ${sc["Neutral"] || 0}`;
  left.appendChild(scDiv);

  // right: summary with LOW/MED/HIGH tags
  const s = data.summary || {};
  const sumHtml = document.createElement("div");
  sumHtml.className = "scorecard";
  sumHtml.innerHTML = `
    <strong>Risk Scorecard</strong><br/>
    Environmental: ${formatScore(Number(s["Environmental"] || 0))}<br/>
    Social: ${formatScore(Number(s["Social"] || 0))}<br/>
    Governance: ${formatScore(Number(s["Governance"] || 0))}<br/>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:6px 0"/>
    <div style="font-size:14px">
      <b>Total:</b> ${Number(s["Total"] || 0).toFixed(2)}<br/>
      <b>Normalized:</b> ${Number(s["Total_Normalized"] || 0).toFixed(2)}
    </div>
  `;
  right.appendChild(sumHtml);

  // flagged sentences
  const samplesDiv = document.createElement("div");
  samplesDiv.style.marginTop = "12px";
  samplesDiv.innerHTML = "<strong>Example flagged sentences</strong>";
  (data.example_sentences || []).forEach(row => {
    const p = document.createElement("p");
    p.style.fontSize = "13px";
    p.style.margin = "6px 0";
    p.textContent = `${row.Sentence} [${row.ESG_Keyword}] (${row.Predicted_Label}, ${row.Sentiment})`;
    samplesDiv.appendChild(p);
  });
  right.appendChild(samplesDiv);

  div.appendChild(left);
  div.appendChild(right);

  // Chart.js donut
  const env = Number(s["Environmental"] || 0);
  const soc = Number(s["Social"] || 0);
  const gov = Number(s["Governance"] || 0);
  const ctx = canvas.getContext("2d");
  if (window.currentChart) window.currentChart.destroy();
  window.currentChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Environmental', 'Social', 'Governance'],
      datasets: [{
        data: [Math.abs(env), Math.abs(soc), Math.abs(gov)],
        backgroundColor: ["#34c3ff", "#ffb86b", "#7af27a"],
        borderWidth: 0
      }]
    },
    options: {
      cutout: "70%",
      plugins: { legend: { labels: { color: '#fff' } } }
    }
  });
}

// --- Comparative view ---
async function loadComparative() {
  const res = await fetch(apiBase + "/comparative");
  const j = await res.json();
  const data = j.data || [];
  const container = document.getElementById("comparativeArea");
  container.innerHTML = "";
  if (data.length === 0) { container.innerText = "No summary data yet. Upload & analyze."; return; }

  data.forEach(r => {
    const card = document.createElement("div");
    card.className = "comp-card";
    card.innerHTML = `
      <div class="comp-title">${r.Company}</div>
      <div>Environmental: ${formatScore(Number(r.Environmental || 0))}</div>
      <div>Social: ${formatScore(Number(r.Social || 0))}</div>
      <div>Governance: ${formatScore(Number(r.Governance || 0))}</div>
      <div class="comp-foot">Total: ${Number(r.Total || 0).toFixed(2)} • Topics: (see snapshot)</div>
    `;
    container.appendChild(card);
  });
}
