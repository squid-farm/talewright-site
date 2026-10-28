#!/usr/bin/env python3
"""Check a built site: required pages exist and every internal link and anchor resolves."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
import sys

SITE_ORIGIN = "https://www.trytalewright.com"
REQUIRED = ["index.html", "getting-started/index.html", "404.html", "docs/index.html",
            "docs/guide/index.html", "docs/guide/getting-started.html"]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.title, self.description, self._in_title = [], set(), "", None, False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
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
    for error in errors:
        print(error)
    print(f"Checked {len(pages)} pages and {checked} internal links: {len(errors)} problem(s).")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
