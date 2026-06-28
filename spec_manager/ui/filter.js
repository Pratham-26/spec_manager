// Pure spec filtering. Shared by the browser UI (ui/app.js) and the Node test
// (tests-ui/filter.test.cjs). No DOM access here so it stays trivially testable.
//
// Three independent filters combined with AND:
//   content  — case-insensitive substring over title + body ("content of the spec")
//   name     — exact, case-insensitive match on the slug ("exact spec name")
//   projects — membership in a set of project slugs ("select multiple projects").
//              null/undefined = no project filter; an empty set = match nothing.
function filterSpecs(specs, { content = "", name = "", projects = null } = {}) {
  const c = (content || "").trim().toLowerCase();
  const n = (name || "").trim().toLowerCase();
  const proj = projects ? new Set(projects) : null;
  return specs.filter((s) => {
    if (c) {
      const hay = `${s.title || ""}\n${s.current_body || ""}`.toLowerCase();
      if (!hay.includes(c)) return false;
    }
    if (n && (s.slug || "").toLowerCase() !== n) return false;
    if (proj && !proj.has(s.project_slug)) return false;
    return true;
  });
}

if (typeof module !== "undefined" && module.exports) module.exports = { filterSpecs };
