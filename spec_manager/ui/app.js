// Read-only spec browser. Talks to the FastAPI API on the same origin.
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

async function loadSpecs() {
  allSpecs = await json("/specs");
  populateProjects(allSpecs);
  render(allSpecs);
}

function populateProjects(specs) {
  const sel = $("project");
  const seen = new Set(sel.textContent ? Array.from(sel.options).map((o) => o.value) : []);
  specs.forEach((s) => {
    if (!seen.has(s.project_slug)) {
      seen.add(s.project_slug);
      const o = document.createElement("option");
      o.value = s.project_slug;
      o.textContent = s.project_slug;
      sel.appendChild(o);
    }
  });
}

function render(list) {
  const el = $("results");
  el.innerHTML = "";
  if (!list.length) {
    el.innerHTML = "<p class='hint'>No specs found.</p>";
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
    b.onclick = () => {
      $("body").textContent = v.body;
    };
    vd.appendChild(b);
  });
}

$("q").addEventListener("input", async () => {
  const q = $("q").value.trim();
  const project = $("project").value;
  if (!q) {
    render(project ? allSpecs.filter((s) => s.project_slug === project) : allSpecs);
    return;
  }
  const hits = await json(`/search?q=${encodeURIComponent(q)}${project ? `&project=${encodeURIComponent(project)}` : ""}`);
  render(hits);
});
$("project").addEventListener("change", () => $("q").dispatchEvent(new Event("input")));

loadSpecs();
