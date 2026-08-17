const resultsBody = document.getElementById("results-body");
const resultsSub = document.getElementById("results-sub");
const verifySlot = document.getElementById("verify-slot");
const layoutEl = document.querySelector(".layout");
let cardsByName = {};
function normName(s) { return String(s || "").toLowerCase().replace(/[^a-z0-9]/g, ""); }

const VERIFICATION_STATUS_LABELS = {
  sound: "Verified — no issues found",
  caveats: "Verified with caveats",
  needs_attention: "Needs attention",
};

function clearVerification() {
  verifySlot.replaceChildren();
}

function verifyPending() {
  clearVerification();
  const panel = el("div", "verify-panel verify-panel--pending");
  panel.dataset.status = "pending";
  const head = el("div", "verify-panel__head");
  head.appendChild(el("span", "verify-dot verify-dot--pending"));
  head.appendChild(el("span", "verify-panel__label", "Verifying recommendations…"));
  panel.appendChild(head);
  verifySlot.appendChild(panel);
  layoutEl.classList.add("has-results");
}

function showVerification(status, markdown) {
  clearVerification();
  const label = VERIFICATION_STATUS_LABELS[status] || VERIFICATION_STATUS_LABELS.caveats;
  const panel = el("details", "verify-panel");
  panel.dataset.status = status || "caveats";
  const head = el("summary", "verify-panel__head");
  head.appendChild(el("span", "verify-chevron", "▸"));
  head.appendChild(el("span", "verify-dot"));
  head.appendChild(el("span", "verify-panel__label", label));
  panel.appendChild(head);
  const body = el("div", "verify-panel__body md");
  body.innerHTML = renderMarkdown(markdown || "");
  panel.appendChild(body);
  verifySlot.appendChild(panel);
  layoutEl.classList.add("has-results");
}

const TIER_TOKEN = { "2d_line": "cellline", organoid: "organoid", coculture: "pdx", in_vivo: "mouse" };

function pcRow(d, kind) {
  const row = el("div", "rec-pc__row");
  row.appendChild(el("span", "rec-pc__mark rec-pc__mark--" + kind, kind === "pro" ? "✓" : "✗"));
  const body = el("div", "rec-pc__body");
  body.appendChild(el("span", "rec-pc__text", d.label));
  const src = el("span", "rec-pc__src");
  if (d.source_url) {
    const a = el("a", null, d.source + " ↗");
    a.href = d.source_url; a.target = "_blank"; a.rel = "noopener";
    src.appendChild(a);
  } else if (d.source) {
    src.appendChild(document.createTextNode(d.source));
  }
  body.appendChild(src);
  row.appendChild(body);
  return row;
}

function section(label, nodes) {
  if (!nodes.length) return null;
  const s = el("div", "rec-section");
  s.appendChild(el("div", "rec-section__label", label));
  nodes.forEach((nd) => s.appendChild(nd));
  return s;
}

function recCard(c) {
  const card = el("details", "rec-card" + (c.recommended ? "" : " rec-card--rejected"));

  const head = el("summary", "rec-head");
  head.appendChild(el("span", "rec-chevron", "▸"));
  head.appendChild(el("span", "rec-rank", "#" + c.rank));
  head.appendChild(el("span", "rec-name", c.model_name));
  const tier = el("span", "rec-chip", c.tier_label);
  const tok = TIER_TOKEN[c.tier] || "cellline";
  tier.style.color = "var(--cellar-" + tok + ")";
  tier.style.background = "var(--cellar-" + tok + "-tint)";
  tier.style.borderColor = "var(--cellar-" + tok + "-border)";
  head.appendChild(tier);
  head.appendChild(el("span", "rec-badge " + (c.recommended ? "rec-badge--yes" : "rec-badge--no"),
    c.recommended ? "Recommended" : "Rejected"));
  const buyable = !!(c.sourcing && c.sourcing.purchasable);
  const buy = el("span", "rec-buy rec-buy--" + (buyable ? "yes" : "no"));
  buy.title = buyable ? "Available to purchase" : "No direct purchase source found";
  buy.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>';
  head.appendChild(buy);
  card.appendChild(head);

  const body = el("div", "rec-body");

  const grid = el("div", "rec-proscons");
  const proCol = el("div", "rec-pc__col rec-pc__col--pro");
  proCol.appendChild(el("div", "rec-pc__head", "Pros"));
  const pros = c.reasons || [];
  if (pros.length) pros.forEach((d) => proCol.appendChild(pcRow(d, "pro")));
  else proCol.appendChild(el("div", "rec-pc__none", "None noted"));
  const conCol = el("div", "rec-pc__col rec-pc__col--con");
  conCol.appendChild(el("div", "rec-pc__head", "Cons"));
  const cons = c.watch_outs || [];
  if (cons.length) cons.forEach((d) => conCol.appendChild(pcRow(d, "con")));
  else conCol.appendChild(el("div", "rec-pc__none", "None noted"));
  grid.appendChild(proCol);
  grid.appendChild(conCol);
  body.appendChild(grid);

  const actions = (c.mechanism && c.mechanism.actions) || [];
  const actNodes = actions.map((a) => {
    const line = a.action + (a.readout_hint ? " — unlocks: " + a.readout_hint : "");
    return el("div", "rec-action", line);
  });
  const act = section("Culture actions to make the mechanism observable", actNodes);
  if (act) body.appendChild(act);

  const notes = (c.context_notes || []).map((t) => el("div", "rec-note", t));
  const ctx = section("Context for your decision", notes);
  if (ctx) body.appendChild(ctx);

  const flags = (c.verification_notes || []).map((t) => el("div", "rec-flag", t));
  const flagSec = section("Verification flags", flags);
  if (flagSec) body.appendChild(flagSec);

  const src = c.sourcing || {};
  const foot = el("div", "rec-foot");
  foot.appendChild(el("div", "rec-foot__label", "Where to buy"));
  const val = el("div", "rec-foot__val");
  if (src.purchasable && (src.supplier_or_cro || src.catalog_url)) {
    if (src.catalog_url) {
      const a = el("a", null, (src.supplier_or_cro || "Purchase") + " ↗");
      a.href = src.catalog_url; a.target = "_blank"; a.rel = "noopener";
      val.appendChild(a);
    } else {
      val.textContent = src.supplier_or_cro;
    }
  } else if (src.catalog_url) {
    val.appendChild(document.createTextNode("Not sold through a standard catalog — "));
    const a = el("a", null, "see record ↗");
    a.href = src.catalog_url; a.target = "_blank"; a.rel = "noopener";
    val.appendChild(a);
  } else {
    val.textContent = "No direct purchase source found.";
  }
  foot.appendChild(val);
  body.appendChild(foot);
  card.appendChild(body);
  return card;
}

function injectWhy(model, why) {
  const card = cardsByName[normName(model)];
  if (!card || !why) return;
  const body = card.querySelector(".rec-body");
  if (!body) return;
  if (!card._why) {
    const block = el("div", "rec-why");
    block.appendChild(el("div", "rec-why__label", "Why this model"));
    const text = el("div", "rec-why__text md");
    block.appendChild(text);
    body.insertBefore(block, body.firstChild);
    card._why = text;
  }
  card._why.innerHTML = renderMarkdown(why);
}

function _resultsContext(report) {
  const q = report.query || {};
  return [q.target_symbol, q.disease, q.question_type].filter(Boolean).join(" · ");
}

function _escalationBanner(report) {
  if (!Array.isArray(report.cards) || !report.cards.length) return null;
  if (report.cards.some((c) => c.recommended)) return null;
  const verdict = (report.verdict || "").trim();
  if (!verdict) return null;
  const banner = el("div", "verdict-banner");
  const heading = report.in_vivo_recommended
    ? "No in-vitro model is adequate here"
    : "Every candidate below was rejected";
  banner.appendChild(el("div", "verdict-banner__head", heading));
  banner.appendChild(el("div", "verdict-banner__body", verdict));
  return banner;
}

function showRecommendations(report) {
  resultsSub.textContent = _resultsContext(report) || (report.verdict || "");
  resultsBody.replaceChildren();
  clearVerification();
  cardsByName = {};
  const escalation = _escalationBanner(report);
  if (escalation) resultsBody.appendChild(escalation);
  const v = report.verification;
  if (v && v.status && v.status !== "sound") {
    const banner = el("div", "verify-banner verify-banner--" + v.status);
    banner.textContent = v.status === "needs_attention"
      ? "Verification flagged possible issues. See the notes on the affected cards."
      : "Verified with minor caveats. See the notes on the affected cards.";
    resultsBody.appendChild(banner);
  }
  report.cards.forEach((c) => {
    const card = recCard(c);
    cardsByName[normName(c.model_name)] = card;
    resultsBody.appendChild(card);
  });
  resultsBody.scrollTop = 0;
  layoutEl.classList.add("has-results");
}

function showNoRecommendations(report) {
  resultsSub.textContent = _resultsContext(report) || "No models ranked";
  resultsBody.replaceChildren();
  clearVerification();
  const note = el("div", "results__empty");
  note.textContent = report.verdict || "No candidate models were ranked for this question.";
  resultsBody.appendChild(note);
  resultsBody.scrollTop = 0;
  layoutEl.classList.add("has-results");
}

function resetResultsPanel() {
  if (!layoutEl.classList.contains("has-results")) return;
  resultsSub.textContent = "Ranked models appear here.";
  resultsBody.replaceChildren();
  clearVerification();
  const note = el("div", "results__empty");
  note.textContent = "Ranked models for this question will appear here.";
  resultsBody.appendChild(note);
}

function revealRecommendations(report, rationales) {
  if (!report || !Array.isArray(report.cards)) return;
  if (report.cards.length) {
    showRecommendations(report);
    (rationales || []).forEach((r) => injectWhy(r.model, r.why));
  } else {
    showNoRecommendations(report);
  }
}
