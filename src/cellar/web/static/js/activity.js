const TOOL_LABELS = {
  target_disease_evidence: "Checking target–disease evidence",
  protein_evidence: "Checking protein evidence",
  protein_atlas_profile: "Reading the protein atlas",
  isoform_risk: "Checking isoform risk",
  pathway_relations: "Mapping pathway relations",
  literature_search: "Searching the literature",
  find_cell_model: "Finding the cell model",
  cell_line_provenance: "Checking cell-line provenance",
  gene_dependency: "Checking CRISPR dependency",
  cell_model_gene_mutations: "Checking mutations",
  build_recommendations: "Building recommendations",
  recommend_models: "Building recommendations",
  annotate_recommendations: "Annotating recommendations",
  web_search: "Searching the web",
  web_fetch: "Fetching a web page",
  code_execution: "Filtering web results",
  bash_code_execution: "Filtering web results",
};
const SERVER_TOOLS = new Set(["web_search", "web_fetch", "code_execution", "bash_code_execution"]);
function toolLabel(name) {
  return TOOL_LABELS[name] || (name || "tool").replace(/_/g, " ");
}

function toolSummary(name, ev) {
  if (ev.is_error) return "failed";
  let d = null;
  try { d = JSON.parse(ev.content); } catch (e) { d = null; }
  if (!d || typeof d !== "object") return "done";
  if (d.found === false) return "not found";
  if (name === "find_cell_model" && d.sidm_id) return d.sidm_id;
  if (name === "cell_model_gene_mutations" && Array.isArray(d.mutations))
    return d.mutations.length + " mutation" + (d.mutations.length === 1 ? "" : "s");
  if ((name === "build_recommendations" || name === "recommend_models") && Array.isArray(d.cards))
    return d.cards.length + " model" + (d.cards.length === 1 ? "" : "s") + " ranked";
  if (name === "gene_dependency" && "is_dependency" in d) return d.is_dependency ? "is a dependency" : "not a dependency";
  if (name === "protein_evidence" && d.synthesis && d.synthesis.confidence) return d.synthesis.confidence + " protein evidence";
  if (name === "isoform_risk" && d.isoform_specificity_risk) return d.isoform_specificity_risk + " risk";
  if (name === "pathway_relations" && d.literature_relations) return Object.keys(d.literature_relations).length + " relations";
  if (name === "literature_search" && Array.isArray(d.papers)) return d.papers.length + " paper" + (d.papers.length === 1 ? "" : "s");
  if (name === "target_disease_evidence" && typeof d.overall_score === "number") return "assoc " + d.overall_score.toFixed(2);
  return "done";
}

function ensureActivity(a) {
  if (a.activity) return a.activity;
  const box = el("details", "activity");
  box.open = true;
  const head = el("summary", "activity__head");
  head.appendChild(el("span", "activity__dot"));
  const title = el("span", "activity__title", "Working…");
  head.appendChild(title);
  const count = el("span", "activity__count", "");
  head.appendChild(count);
  head.appendChild(el("span", "activity__chev", "▸"));
  box.appendChild(head);
  const steps = el("div", "activity__steps");
  box.appendChild(steps);
  a.body.insertBefore(box, a.caret);
  a.cursorText = null;
  a.activity = { box, title, count, steps, n: 0, done: false };
  return a.activity;
}

function activityStep(a, name) {
  const act = ensureActivity(a);
  act.n += 1;
  act.count.textContent = act.n;
  act.title.textContent = toolLabel(name) + "…";
  const row = el("div", "step running");
  row.appendChild(el("span", "step__dot"));
  row.appendChild(el("span", "step__label", toolLabel(name)));
  const sum = el("span", "step__sum", "…");
  row.appendChild(sum);
  act.steps.appendChild(row);
  row._sum = sum;
  return row;
}

function activityDone(a, row, ev) {
  if (row) {
    row.classList.remove("running");
    row.classList.add(ev.is_error ? "error" : "done");
    row._sum.textContent = toolSummary(ev.tool_name, ev);
  }
}

function activityServerDone(a, row) {
  if (!row) return;
  row.classList.remove("running");
  row.classList.add("done");
  row._sum.textContent = "done";
}

function activityFinish(a) {
  const act = a.activity;
  if (!act || act.done) return;
  act.done = true;
  act.box.classList.add("is-done");
  act.box.open = false;
  act.title.textContent = "Gathered evidence from " + act.n + " source" + (act.n === 1 ? "" : "s");
}
