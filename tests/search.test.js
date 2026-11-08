import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { attachSearch } from "../assets/search-loader.js";
import { createExcerpt, createSearchIndex, searchRecords, tokenize } from "../scripts/search-core.js";
import { bindSearchForm } from "../scripts/search.js";

const root = new URL("../", import.meta.url);

test("tokenization preserves required Talemark syntax and diagnostics", () => {
  assert.deepEqual(tokenize("@hub #one-many -> {player:pronoun} TW3009"), [
    "@hub",
    "#one-many",
    "->",
    "{player:pronoun}",
    "tw3009",
  ]);
});

test("page titles and section headings rank above body-only matches", () => {
  const index = createSearchIndex([
    {
      id: "body",
      pageTitle: "General guide",
      heading: "Overview",
      body: "Searchable phrase appears in this body.",
      url: "/guide/#overview",
    },
    {
      id: "title",
      pageTitle: "Searchable phrase guide",
      heading: "Overview",
      body: "",
      url: "/guide/#title",
    },
    {
      id: "heading",
      pageTitle: "General guide",
      heading: "Searchable phrase",
      body: "",
      url: "/guide/#heading",
    },
  ]);

  assert.equal(searchRecords(index, "searchable phrase")[0].id, "title");
});

test("excerpts are concise and find typo-tolerant matches", () => {
  const body = "The introduction is deliberately long. ".repeat(8)
    + "Use a text manipulator to change the rendered wording. "
    + "Additional details follow. ".repeat(8);

  const excerpt = createExcerpt(body, "manipulater", 100);

  assert.ok(excerpt.length <= 110);
  assert.match(excerpt, /manipulator/);
  assert.ok(excerpt.startsWith("... "));
});

test("search form submission runs for keyboard activation", () => {
  const input = new FakeElement();
  const form = new FakeElement();
  let renders = 0;
  bindSearchForm(form, input, () => { renders += 1; });

  let prevented = false;
  form.emit("submit", { preventDefault: () => { prevented = true; } });

  assert.equal(prevented, true);
  assert.equal(renders, 1);
});

test("search code loads on demand and closing the dialog restores focus", async () => {
  const document = new FakeDocument();
  let loads = 0;
  attachSearch(document, async () => {
    loads += 1;
    return { initializeSearch: async () => {} };
  });

  assert.equal(loads, 0);
  assert.equal(document.elements.get("search-trigger").hidden, false);
  await document.elements.get("search-trigger").emitAsync("click");
  assert.equal(loads, 1);
  assert.equal(document.elements.get("site-search").open, true);

  document.elements.get("site-search").emit("cancel", { preventDefault() {} });
  assert.equal(document.elements.get("site-search").open, false);
  assert.equal(document.elements.get("search-trigger").focused, true);
});

test("the built index returns the required syntax, diagnostic, and typo searches", async () => {
  const indexUrl = new URL("_site/search-index.json", root);
  const payload = JSON.parse(await readFile(fileURLToPath(indexUrl), "utf8"));
  const index = createSearchIndex(payload.records);
  const cases = [
    ["@hub", "/docs/guide/writing-stories.html#hubs"],
    ["#one-many", "/docs/reference/talemark-operators.html#manipulator-arguments"],
    ["->", "/docs/guide/writing-stories.html#scenes-run-top-to-bottom"],
    ["{player:pronoun}", "/docs/reference/talemark-syntax.html#3-substitutions"],
    ["TW3009", "/docs/reference/diagnostics.html#tw3xxx-story-structure"],
    ["manipula", "/docs/reference/talemark-operators.html#manipulator-arguments"],
    ["manipulater", "/docs/reference/talemark-operators.html#manipulator-arguments"],
  ];

  for (const [query, expectedUrl] of cases) {
    const results = searchRecords(index, query);
    assert.ok(results.length > 0, `Expected results for ${query}`);
    assert.ok(results.some((result) => result.url === expectedUrl), `Expected ${expectedUrl} for ${query}`);
    assert.ok(results.every((result) => result.url.includes("#")));
  }

  assert.ok(
    searchRecords(index, "RPG rules built in")
      .some((result) => result.url === "/#rpg-rules-built-in"),
    "Expected marketing-page search results",
  );
});

class FakeElement {
  constructor() {
    this.listeners = new Map();
    this.focused = false;
    this.hidden = true;
    this.open = false;
  }

  addEventListener(type, listener) {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  emit(type, event = {}) {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }

  async emitAsync(type, event = {}) {
    await Promise.all((this.listeners.get(type) ?? []).map((listener) => listener(event)));
  }

  focus() {
    this.focused = true;
  }

  showModal() {
    this.open = true;
  }

  close() {
    this.open = false;
    this.emit("close");
  }
}

class FakeDocument {
  constructor() {
    this.elements = new Map([
      ["search-trigger", new FakeElement()],
      ["site-search", new FakeElement()],
      ["search-query", new FakeElement()],
      ["search-status", new FakeElement()],
      ["search-close", new FakeElement()],
    ]);
  }

  getElementById(id) {
    return this.elements.get(id);
  }
}
