import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { after, before, test } from "node:test";
import { chromium } from "playwright";

let browser;
let server;
let origin;
const site = new URL("../_site/", import.meta.url);

before(async () => {
  server = createServer(async (request, response) => {
    const url = new URL(request.url, "http://localhost");
    const path = url.pathname.endsWith("/") ? `${url.pathname}index.html` : url.pathname;
    try {
      const content = await readFile(new URL(`.${path}`, site));
      const type = path.endsWith(".js") ? "text/javascript"
        : path.endsWith(".json") ? "application/json"
        : path.endsWith(".css") ? "text/css" : "text/html";
      response.writeHead(200, { "Content-Type": type });
      response.end(content);
    } catch (error) {
      response.writeHead(error.code === "ENOENT" ? 404 : 500);
      response.end(String(error));
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch();
});

after(async () => {
  await browser?.close();
  if (server) {
    await new Promise((resolve) => server.close(resolve));
  }
});

test("live results, Search button, Enter, and navigation highlighting work in the browser", async () => {
  const page = await browser.newPage();
  const errors = [];
  const requests = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => requests.push(request.url()));
  try {
    await page.goto(origin);
    assert.ok(!requests.some((url) => url.endsWith("/search-index.json") || url.endsWith("/assets/search.js")));
    await page.locator("#search-trigger").focus();
    await page.keyboard.press("Enter");
    const input = page.locator("#search-query");
    await input.waitFor({ state: "visible" });
    await page.waitForFunction(() => !document.getElementById("search-query").disabled);

    for (const query of ["===", ":::", "@hub", "->", "TW3009", "manipulater"]) {
      await input.fill(query);
      const links = page.locator(".search-result-link");
      assert.ok(await links.count() > 0, `Expected results for ${query}`);
      assert.ok(await page.locator("#search-results mark.search-match").count() > 0);
    }

    await input.fill(":::");
    const firstResult = page.locator(".search-result-link").first();
    await page.locator("#search-submit").click();
    assert.equal(await firstResult.evaluate((element) => element === document.activeElement), true);
    await input.focus();
    await page.keyboard.press("Enter");
    assert.equal(await firstResult.evaluate((element) => element === document.activeElement), true);
    await page.keyboard.press("Enter");
    await page.waitForURL((url) => url.searchParams.get("search") === ":::" && url.hash.length > 1);
    await page.waitForFunction(() => document.querySelector("#main mark.search-match"));
    const headingId = decodeURIComponent(new URL(page.url()).hash.slice(1));
    assert.ok(await page.locator(`[id="${headingId}"]`).count() > 0);
    assert.ok((await page.locator("#main mark.search-match").allTextContents()).includes(":::"));
    assert.equal(await page.locator("nav mark.search-match, .docs-source mark.search-match").count(), 0);

    await page.reload();
    await page.waitForFunction(() => document.querySelector("#main mark.search-match"));
    await page.locator("#search-trigger").click();
    await page.waitForFunction(() => !document.getElementById("search-query").disabled);
    await page.locator("#search-query").fill("TW3009");
    await page.keyboard.press("Escape");
    assert.equal(await page.locator("#site-search").evaluate((dialog) => dialog.open), false);
    assert.equal(await page.locator("#search-trigger").evaluate((element) => element === document.activeElement), true);
    await page.locator("#search-trigger").click();
    await page.waitForFunction(() => document.getElementById("search-status").textContent !== "Loading search…");
    assert.ok(await page.locator(".search-result-link").count() > 0);
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});

test("highlighting uses text nodes and does not interpret query text as HTML", async () => {
  const page = await browser.newPage();
  try {
    await page.goto(origin);
    await page.locator("#search-trigger").click();
    await page.waitForFunction(() => !document.getElementById("search-query").disabled);
    await page.locator("#search-query").fill("<img src=x onerror=alert(1)> @hub");
    assert.equal(await page.locator("#search-results img").count(), 0);
    assert.ok(await page.locator("#search-results mark.search-match").count() > 0);
  } finally {
    await page.close();
  }
});

test("syntax, diagnostics, and typo matches remain highlighted after result navigation", async () => {
  const page = await browser.newPage();
  try {
    for (const [query, expectedText] of [
      ["===", "==="],
      ["@hub", "@hub"],
      ["TW3009", "TW3009"],
      ["manipulater", "manipulator"],
    ]) {
      await page.goto(origin);
      await page.locator("#search-trigger").click();
      await page.waitForFunction(() => !document.getElementById("search-query").disabled);
      await page.locator("#search-query").fill(query);
      await page.locator(".search-result-link").first().click();
      await page.waitForURL((url) => url.searchParams.get("search") === query);
      await page.waitForFunction(() => document.querySelector("#main mark.search-match"));
      assert.ok(
        (await page.locator("#main mark.search-match").allTextContents())
          .some((text) => text.toLowerCase() === expectedText.toLowerCase()),
        `Expected highlighted ${expectedText} after navigating from ${query}`,
      );
    }
  } finally {
    await page.close();
  }
});

test("failed search loading reports an error and can be retried", async () => {
  const page = await browser.newPage();
  try {
    await page.route("**/search-index.json", (route) => route.abort());
    await page.goto(origin);
    await page.locator("#search-trigger").click();
    await page.waitForFunction(() => document.getElementById("search-status").textContent.includes("could not be loaded"));
    assert.equal(await page.locator("#search-submit").isDisabled(), true);
    await page.keyboard.press("Escape");
    await page.unroute("**/search-index.json");
    await page.locator("#search-trigger").click();
    await page.waitForFunction(() => !document.getElementById("search-query").disabled);
    await page.locator("#search-query").fill("===");
    assert.ok(await page.locator(".search-result-link").count() > 0);
  } finally {
    await page.close();
  }
});
