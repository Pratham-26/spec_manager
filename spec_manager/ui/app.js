// Read-only spec browser. Talks to the FastAPI API on the same origin.
// Filtering (content / exact-name / multi-project) lives in filter.js and is
// unit-tested in tests-ui/filter.test.cjs — this file is just DOM glue.
const $ = (id) => document.getElementById(id);
let allSpecs = [];

async function json(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function selectedProjects() {
  return [...document.querySelectorAll('#projects input[type=checkbox]:checked')].map((cb) => cb.value);
}

function populateProjects(specs) {
  const distinct = [...new Set(specs.map((s) => s.project_slug))].sort();
  $("projects").innerHTML = distinct
    .map((p) => `<label><input type="checkbox" value="${escapeHtml(p)}" checked /> ${escapeHtml(p)}</label>`)
    .join("");
}

function currentCriteria() {
  return { content: $("content").value, name: $("name").value, projects: selectedProjects() };
}

function applyFilters() {
  render(filterSpecs(allSpecs, currentCriteria()));
}

async function loadSpecs() {
  allSpecs = await json("/specs");
  populateProjects(allSpecs);
  applyFilters();
}

function render(list) {
  const el = $("results");
  el.innerHTML = "";
  if (!list.length) {
    el.innerHTML = "<p class='hint'>No specs match these filters.</p>";
    return;
  }
  list.forEach((s) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML =
      `<div class="slug">${escapeHtml(s.project_slug)} / ${escapeHtml(s.slug)}</div>` +
      `<div class="title">${escapeHtml(s.title)}</div>` +
      `<span class="status ${s.status}">${escapeHtml(s.status)}</span>`;
    card.onclick = () => view(s.project_slug, s.slug);
    el.appendChild(card);
  });
}

async function view(project, slug) {
  const enc = encodeURIComponent;
  const spec = await json(`/projects/${enc(project)}/specs/${enc(slug)}`);
  const versions = await json(`/projects/${enc(project)}/specs/${enc(slug)}/versions`);
  $("detail").innerHTML =
    `<h2>${escapeHtml(spec.title)} <span class="status ${spec.status}">${escapeHtml(spec.status)}</span></h2>` +
    `<div class="meta">${escapeHtml(project)} / ${escapeHtml(slug)} · v${spec.current_version}` +
    `${spec.is_template ? " · template" : ""}</div>` +
    `<div class="versions" id="versions"></div><pre id="body"></pre>`;
  $("body").textContent = spec.current_body;
  const vd = $("versions");
  [...versions].reverse().forEach((v) => {
    const b = document.createElement("button");
    b.className = "ver";
    b.textContent = `v${v.version}`;
    b.onclick = () => { $("body").textContent = v.body; };
    vd.appendChild(b);
  });
}

$("content").addEventListener("input", applyFilters);
$("name").addEventListener("input", applyFilters);
$("projects").addEventListener("change", applyFilters);

loadSpecs();
