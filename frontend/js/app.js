const API_BASE = window.location.origin.includes("5000") ? "" : "http://localhost:5000";

const sourceVendorSel = document.getElementById("sourceVendor");
const targetVendorSel = document.getElementById("targetVendor");
const sourceCodeEl = document.getElementById("sourceCode");
const targetCodeEl = document.getElementById("targetCode");
const sourceLabelEl = document.getElementById("sourceLabel");
const targetLabelEl = document.getElementById("targetLabel");
const statusMsg = document.getElementById("statusMsg");
const resultsPanel = document.getElementById("resultsPanel");
const confidenceBadge = document.getElementById("confidenceBadge");
const confidenceDetail = document.getElementById("confidenceDetail");
const tagTableBody = document.querySelector("#tagTable tbody");
const warningsList = document.getElementById("warningsList");
const equivalenceBox = document.getElementById("equivalenceBox");

const EXAMPLES = {
  Siemens: `I0.0 AND I0.1 -> Q0.0
I0.2 OR I0.3 -> Q0.1
NOT I0.4 -> Q0.2
SET Q0.3
RESET Q0.4
TON Timer_1 IN:=I0.0 PT:=T#5s
CTU Counter_1 CU:=I0.0 R:=I0.1 PV:=10`,
  Rockwell: `XIC(I0.0) XIC(I0.1) OTE(Q0.0)
XIC(I0.2) OTE(Q0.1)
XIC(I0.3) OTE(Q0.1)
XIO(I0.4) OTE(Q0.2)
OTL(Q0.3)
OTU(Q0.4)
TON(Timer_1,5000)
CTU(Counter_1,10)`,
};

function updateLabels() {
  sourceLabelEl.textContent = `${sourceVendorSel.value} source`;
  targetLabelEl.textContent = `${targetVendorSel.value} output`;
}

sourceVendorSel.addEventListener("change", updateLabels);
targetVendorSel.addEventListener("change", updateLabels);

document.getElementById("swapBtn").addEventListener("click", () => {
  const s = sourceVendorSel.value;
  sourceVendorSel.value = targetVendorSel.value;
  targetVendorSel.value = s;
  const codeTmp = sourceCodeEl.value;
  sourceCodeEl.value = targetCodeEl.value;
  targetCodeEl.value = codeTmp;
  updateLabels();
});

document.getElementById("loadExampleBtn").addEventListener("click", () => {
  sourceCodeEl.value = EXAMPLES[sourceVendorSel.value] || EXAMPLES.Siemens;
});

document.getElementById("convertBtn").addEventListener("click", async () => {
  const source = sourceCodeEl.value.trim();
  if (!source) {
    statusMsg.textContent = "Enter some PLC code first.";
    return;
  }

  statusMsg.textContent = "Converting...";
  resultsPanel.style.display = "none";

  try {
    const res = await fetch(`${API_BASE}/convert`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source,
        source_vendor: sourceVendorSel.value,
        target_vendor: targetVendorSel.value,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      statusMsg.textContent = data.error || "Conversion failed.";
      return;
    }

    targetCodeEl.value = data.converted_code;
    renderResults(data);
    statusMsg.textContent = "Done.";
  } catch (err) {
    statusMsg.textContent = "Could not reach the API. Is the Flask backend running on port 5000?";
    console.error(err);
  }
});

function renderResults(data) {
  resultsPanel.style.display = "block";

  confidenceBadge.textContent = `${data.confidence.overall}%`;
  const c = data.confidence.components;
  confidenceDetail.innerHTML = `
    Instruction mapping: ${c.instruction_score}%<br/>
    Syntax validation: ${c.syntax_score}%<br/>
    Tag mapping: ${c.tag_score}%<br/>
    Logic equivalence: ${c.equivalence_score}%<br/>
    Rule-based vs AI: ${data.confidence.rule_based_instructions} rule / ${data.confidence.ai_based_instructions} AI
  `;

  tagTableBody.innerHTML = "";
  (data.tag_mapping || []).forEach((m) => {
    const row = document.createElement("tr");
    const keys = Object.keys(m);
    row.innerHTML = `<td>${m[keys[0]]}</td><td>${m[keys[1]]}</td>`;
    tagTableBody.appendChild(row);
  });

  warningsList.innerHTML = "";
  (data.warnings || []).forEach((w) => {
    const li = document.createElement("li");
    li.textContent = `⚠ ${w}`;
    warningsList.appendChild(li);
  });

  const eq = data.equivalence || {};
  equivalenceBox.className = "";
  if (eq.status === "PASS") {
    equivalenceBox.classList.add("eq-pass");
    equivalenceBox.textContent = `PASS — ${eq.rows_passed}/${eq.rows_tested} truth-table rows matched.`;
  } else if (eq.status === "FAIL") {
    equivalenceBox.classList.add("eq-fail");
    equivalenceBox.textContent = `FAIL — ${eq.rows_passed}/${eq.rows_tested} rows matched. See mismatches in API response.`;
  } else {
    equivalenceBox.classList.add("eq-skip");
    equivalenceBox.textContent = eq.reason || "Skipped (no combinational boolean logic to test, or stateful-only program).";
  }
}

updateLabels();
