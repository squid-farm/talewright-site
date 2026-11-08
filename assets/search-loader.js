export function attachSearch(document, loadSearch = () => import("./search.js")) {
  const trigger = document.getElementById("search-trigger");
  const dialog = document.getElementById("site-search");
  const input = document.getElementById("search-query");
  const status = document.getElementById("search-status");
  const close = document.getElementById("search-close");

  if (!trigger || !dialog || !input || !status || !close) {
    return;
  }

  trigger.hidden = false;
  trigger.addEventListener("click", async () => {
    if (!dialog.open) {
      dialog.showModal();
    }
    status.textContent = "Loading search…";
    input.focus();

    try {
      const { initializeSearch, refreshSearch } = await loadSearch();
      const index = await initializeSearch(document);
      refreshSearch(document, index);
      input.disabled = false;
      document.getElementById("search-submit").disabled = false;
      if (dialog.open) {
        input.focus();
      }
    } catch (error) {
      console.error("Could not load site search.", error);
      status.textContent = "Search could not be loaded. Please try again later.";
    }
  });
  close.addEventListener("click", () => dialog.close());
  dialog.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      dialog.close();
    }
  });
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    dialog.close();
  });
  dialog.addEventListener("close", () => trigger.focus());

  if (document.location && new URL(document.location.href).searchParams.has("search")) {
    loadSearch().then(({ highlightDestination }) => highlightDestination(document)).catch((error) => {
      console.error("Could not highlight search matches.", error);
      status.textContent = "Search matches could not be highlighted. Please try opening search again.";
    });
  }
}

if (typeof document !== "undefined") {
  attachSearch(document);
}
