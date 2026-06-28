// Zero-dependency test for the pure filterSpecs function. Run: node tests-ui/filter.test.cjs
const assert = require("node:assert");
const { filterSpecs } = require("../spec_manager/ui/filter.js");

const SPECS = [
  { project_slug: "shop", slug: "cart", title: "Cart", current_body: "Holds items a customer intends to purchase." },
  { project_slug: "shop", slug: "order", title: "Order", current_body: "Created from a cart at checkout." },
  { project_slug: "payments", slug: "payment", title: "Payment", current_body: "Captures funds for an order." },
  { project_slug: "payments", slug: "refund", title: "Refund", current_body: "Returns captured funds." },
];

const slugs = (list) => list.map((s) => s.slug).sort();
let n = 0;
function ok(name, actual, expected) {
  n++;
  assert.deepStrictEqual(actual, expected, name);
  console.log("  ok - " + name);
}

console.log("# content search (body + title, case-insensitive)");
ok("body match 'funds' -> payment, refund", slugs(filterSpecs(SPECS, { content: "funds" })), ["payment", "refund"]);
ok("title match 'refund'", slugs(filterSpecs(SPECS, { content: "refund" })), ["refund"]);
ok("'cart' spans title + body", slugs(filterSpecs(SPECS, { content: "cart" })), ["cart", "order"]);
ok("no match", slugs(filterSpecs(SPECS, { content: "zzzzz" })), []);
ok("empty content -> all", slugs(filterSpecs(SPECS, { content: "" })), ["cart", "order", "payment", "refund"]);

console.log("# exact-name filter (slug, case-insensitive)");
ok("exact 'payment'", slugs(filterSpecs(SPECS, { name: "payment" })), ["payment"]);
ok("partial 'pay' is NOT a match", slugs(filterSpecs(SPECS, { name: "pay" })), []);
ok("case-insensitive 'PAYMENT'", slugs(filterSpecs(SPECS, { name: "PAYMENT" })), ["payment"]);
ok("empty name -> all", slugs(filterSpecs(SPECS, { name: "" })), ["cart", "order", "payment", "refund"]);

console.log("# multi-project selector");
ok("only shop", slugs(filterSpecs(SPECS, { projects: ["shop"] })), ["cart", "order"]);
ok("shop + payments", slugs(filterSpecs(SPECS, { projects: ["shop", "payments"] })), ["cart", "order", "payment", "refund"]);
ok("none selected -> none", slugs(filterSpecs(SPECS, { projects: [] })), []);
ok("projects omitted -> all", slugs(filterSpecs(SPECS, {})), ["cart", "order", "payment", "refund"]);

console.log("# combinations (AND)");
ok("content 'funds' + payments", slugs(filterSpecs(SPECS, { content: "funds", projects: ["payments"] })), ["payment", "refund"]);
ok("content 'funds' + name 'refund'", slugs(filterSpecs(SPECS, { content: "funds", name: "refund" })), ["refund"]);
ok("name 'order' + shop", slugs(filterSpecs(SPECS, { name: "order", projects: ["shop"] })), ["order"]);

console.log("\nAll " + n + " filter assertions passed.");
