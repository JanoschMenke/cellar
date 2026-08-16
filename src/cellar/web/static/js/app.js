const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const modelChip = document.getElementById("model");
const apiKeyDialog = document.getElementById("api-key-dialog");
const apiKeyForm = document.getElementById("api-key-form");
const apiKeyInput = document.getElementById("api-key-input");
const apiKeyError = document.getElementById("api-key-error");

let activeES = null;
let activeFinish = null;

function setGenerating(on) {
  input.disabled = on;
  sendBtn.textContent = on ? "Stop" : "Send";
  sendBtn.classList.toggle("send--stop", on);
}

function stopGeneration() {
  if (activeFinish) activeFinish(true);
}

function setComposerEnabled(on) {
  input.disabled = !on;
  sendBtn.disabled = !on;
}

function refreshConfig() {
  return fetch("/config").then((r) => r.ok ? r.json() : null).then((c) => {
    if (c) modelChip.textContent = c.model;
    return c;
  }).catch(() => { modelChip.textContent = "ready"; return null; });
}

refreshConfig().then((c) => {
  if (c && c.needs_api_key) {
    setComposerEnabled(false);
    apiKeyDialog.showModal();
  }
});

apiKeyForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const key = apiKeyInput.value.trim();
  apiKeyError.textContent = "";
  fetch("/api-key", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: key }),
  })
    .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
    .then(({ data }) => {
      if (data && data.ok) {
        apiKeyInput.value = "";
        apiKeyDialog.close();
        setComposerEnabled(true);
        refreshConfig();
      } else {
        apiKeyError.textContent = (data && data.error) || "Something went wrong.";
      }
    })
    .catch(() => {
      apiKeyError.textContent = "Could not reach the server.";
    });
});

function send(text) {
  if (!text.trim()) return;
  clearEmptyState();
  resetResultsPanel();
  input.value = "";
  setGenerating(true);
  addUser(text);
  const a = addAssistant();
  scrollDown();
  const openTools = [];
  let pendingReport = null;
  let pendingRationales = [];
  let revealed = false;
  const es = new EventSource("/chat?message=" + encodeURIComponent(text));
  activeES = es;

  es.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    const stick = isNearBottom();
    if (ev.kind === "text") { appendText(a, ev.text); }
    else if (ev.kind === "tool_use") {
      if (SERVER_TOOLS.has(ev.tool_name)) { activityServerDone(a, activityStep(a, ev.tool_name)); }
      else { openTools.push(activityStep(a, ev.tool_name)); }
    }
    else if (ev.kind === "tool_result") {
      activityDone(a, openTools.shift(), ev);
      if (!ev.is_error && (ev.tool_name === "build_recommendations" || ev.tool_name === "recommend_models")) {
        try { pendingReport = JSON.parse(ev.content); } catch (err) { pendingReport = null; }
        if (pendingReport && Array.isArray(pendingReport.cards) && !pendingReport.cards.length) {
          showNoRecommendations(pendingReport); revealed = true;
        }
      } else if (!ev.is_error && ev.tool_name === "annotate_recommendations") {
        try { const d = JSON.parse(ev.content); if (d && Array.isArray(d.rationales)) pendingRationales = d.rationales; } catch (err) {}
        if (pendingReport && !revealed) { revealRecommendations(pendingReport, pendingRationales); revealed = true; }
      }
    }
    else if (ev.kind === "verify_start") { verifyPending(); }
    else if (ev.kind === "verify_result") { showVerification(ev.verification_status, ev.text); }
    else if (ev.kind === "error") { appendText(a, "\n[error] " + (ev.content || "")); }
    else if (ev.kind === "done") {
      if (!revealed && pendingReport) revealRecommendations(pendingReport, pendingRationales);
      finish();
    }
    if (stick) scrollDown();
  };
  es.onerror = () => finish();

  let finished = false;
  function finish(stopped) {
    if (finished) return;
    finished = true;
    es.close();
    activityFinish(a);
    a.caret.remove();
    if (stopped) a.body.appendChild(el("div", "stopped", "■ stopped"));
    activeES = null;
    activeFinish = null;
    setGenerating(false);
    input.focus();
  }
  activeFinish = finish;
}

function newInvestigation() {
  if (activeES) stopGeneration();
  fetch("/reset", { method: "POST" }).catch(() => {});
  messagesEl.replaceChildren();
  layoutEl.classList.remove("has-results");
  resultsBody.replaceChildren();
  clearVerification();
  resultsSub.textContent = "Ranked models appear here.";
  renderEmptyState();
  input.value = "";
  input.focus();
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (activeES) { stopGeneration(); return; }
  send(input.value);
});
document.getElementById("new-btn").addEventListener("click", newInvestigation);
renderEmptyState();
input.focus();
