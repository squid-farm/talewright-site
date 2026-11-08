#!/usr/bin/env python3
"""Check a built site: required pages exist and every internal link and anchor resolves."""

from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
import sys

SITE_ORIGIN = "https://www.trytalewright.com"
REQUIRED = ["index.html", "getting-started/index.html", "features/index.html", "404.html", "docs/index.html",
            "docs/guide/index.html", "docs/guide/getting-started.html"]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.title, self.description, self._in_title = [], set(), "", None, False
        self.search_index_url = None
        self.module_scripts = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.search_index_url = attrs.get("data-search-index-url")
        if tag == "script" and attrs.get("type") == "module" and attrs.get("src"):
            self.module_scripts.add(attrs["src"])
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a" and "name" in attrs:
            self.ids.add(attrs["name"])
        for key in ("href", "src"):
            if attrs.get(key) and not (tag == "link" and attrs.get("rel") in ("canonical", "preconnect")):
                self.links.append(attrs[key])
        if tag == "meta" and attrs.get("name") == "description":
            self.description = attrs.get("content")
        self._in_title = tag == "title"

    def handle_endtag(self, tag):
        self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def target_file(site, path):
    file = site / unquote(path).lstrip("/")
    if path.endswith("/") or file.is_dir():
        file = file / "index.html"
    return file


def check_search_index(site, pages):
    errors = []
    index_file = site / "search-index.json"
    if not index_file.is_file():
        return ["missing generated search index search-index.json"]
    try:
        index = json.loads(index_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"invalid generated search index: {error}"]

    if not isinstance(index, dict):
        return ["generated search index is not an object"]
    records = index.get("records")
    if index.get("version") != 1:
        errors.append("search index has an unsupported version")
    if not isinstance(records, list) or not records:
        errors.append("search index is empty or has no records")
        return errors

    seen = set()
    for number, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append(f"search index record {number} is not an object")
            continue
        required = ("id", "pageTitle", "heading", "body", "url")
        if any(not isinstance(record.get(key), str) for key in required):
            errors.append(f"search index record {number} is missing string fields")
            continue
        if not record["pageTitle"].strip() or not record["heading"].strip():
            errors.append(f"search index record {number} has an empty title or heading")
        if record["id"] in seen:
            errors.append(f"duplicate search index record id {record['id']}")
        seen.add(record["id"])

        url = urlparse(urljoin(SITE_ORIGIN + "/", record["url"]))
        if url.scheme != "https" or url.netloc != urlparse(SITE_ORIGIN).netloc:
            errors.append(f"search index record {number} points outside the site")
            continue
        target = target_file(site, url.path)
        if not target.is_file():
            errors.append(f"search index record {number} points to a missing page: {record['url']}")
            continue
        if target.suffix != ".html" or target not in pages:
            errors.append(f"search index record {number} does not point to a built HTML page: {record['url']}")
            continue
        if not url.fragment or unquote(url.fragment) not in pages[target].ids:
            errors.append(f"search index record {number} points to a missing heading: {record['url']}")
        if record["id"] != f"{url.path}#{unquote(url.fragment)}":
            errors.append(f"search index record {number} id does not match its heading URL")

    return errors


def main():
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    errors = [f"missing required page {r}" for r in REQUIRED if not (site / r).is_file()]
    pages = {}
    for file in site.rglob("*.html"):
        page = Page()
        page.feed(file.read_text(encoding="utf-8"))
        pages[file] = page
        rel = file.relative_to(site).as_posix()
        if not page.title.strip():
            errors.append(f"{rel}: missing <title>")
        if not page.description:
            errors.append(f"{rel}: missing meta description")
        if page.search_index_url != "/search-index.json":
            errors.append(f"{rel}: missing search index URL")
        if "/assets/search-loader.js" not in page.module_scripts:
            errors.append(f"{rel}: search loader is not loaded as a module")
    checked = 0
    for file, page in pages.items():
        rel = file.relative_to(site).as_posix()
        base = SITE_ORIGIN + "/" + rel
        for link in page.links:
            url = urlparse(urljoin(base, link))
            if url.scheme in ("mailto", "data") or (url.scheme.startswith("http") and
                                                    url.netloc != urlparse(SITE_ORIGIN).netloc):
                continue
            checked += 1
            if url.path.endswith(".md"):
                errors.append(f"{rel}: unconverted Markdown link {link}")
                continue
            target = target_file(site, url.path)
            if not target.is_file():
                errors.append(f"{rel}: broken link {link}")
            elif url.fragment and target.suffix == ".html":
                ids = pages[target].ids if target in pages else set()
                if unquote(url.fragment) not in ids:
                    errors.append(f"{rel}: missing anchor {link}")
    errors.extend(check_search_index(site, pages))
    for required_asset in (
        "assets/search-loader.js",
        "assets/search.js",
        "assets/minisearch.LICENSE.txt",
    ):
        asset = site / required_asset
        if not asset.is_file() or asset.stat().st_size == 0:
            errors.append(f"missing or empty search asset {required_asset}")
    for error in errors:
        print(error)
    print(f"Checked {len(pages)} pages and {checked} internal links: {len(errors)} problem(s).")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
