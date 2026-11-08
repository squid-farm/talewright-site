import { createExcerpt, createSearchIndex, searchRecords } from "./search-core.js";

let initialization;

export function bindSearchForm(form, input, render) {
  input.addEventListener("input", render);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    render();
  });
}

function showResults(document, resultsElement, status, index, query) {
  resultsElement.replaceChildren();
  if (!query.trim()) {
    status.textContent = "Type a word or Talemark syntax to search.";
    return;
  }

  const matches = searchRecords(index, query);
  status.textContent = matches.length === 1
    ? "1 result"
    : `${matches.length} results`;

  for (const match of matches) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.className = "search-result-link";
    link.href = match.url;

    const heading = document.createElement("strong");
    heading.textContent = match.heading;
    const pageTitle = document.createElement("small");
    pageTitle.textContent = match.pageTitle;
    link.append(heading, pageTitle);
    item.append(link);

    const excerpt = createExcerpt(match.body, query);
    if (excerpt) {
      const paragraph = document.createElement("p");
      paragraph.textContent = excerpt;
      item.append(paragraph);
    }
    resultsElement.append(item);
  }

  if (matches.length === 0) {
    status.textContent = `No results for “${query.trim()}”.`;
  }
}

export function initializeSearch(document = globalThis.document) {
  if (initialization) {
    return initialization;
  }

  initialization = (async () => {
    const indexUrl = document.documentElement.dataset.searchIndexUrl;
    if (!indexUrl) {
      throw new Error("The search index URL is missing from the page.");
    }

    const response = await fetch(indexUrl, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error(`The search index request failed with HTTP ${response.status}.`);
    }

    const payload = await response.json();
    if (!Array.isArray(payload.records) || payload.records.length === 0) {
      throw new Error("The generated search index is empty or invalid.");
    }

    const index = createSearchIndex(payload.records);
    const form = document.getElementById("search-form");
    const input = document.getElementById("search-query");
    const results = document.getElementById("search-results");
    const status = document.getElementById("search-status");
    const render = () => showResults(document, results, status, index, input.value);
    bindSearchForm(form, input, render);
    render();
    return index;
  })().catch((error) => {
    initialization = undefined;
    throw error;
  });

  return initialization;
}
