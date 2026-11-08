#!/usr/bin/env python3
"""Generate a section-level search index from the built site."""

from html.parser import HTMLParser
import json
from pathlib import Path
import sys

IGNORED_TAGS = {"footer", "nav", "script", "style", "noscript"}
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class Element:
    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or ())
        self.children = []


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("#document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        self.stack[-1].children.append(element)
        if tag not in VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Element(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def walk_elements(element):
    for child in element.children:
        if isinstance(child, Element):
            yield child
            yield from walk_elements(child)


def is_ignored(element):
    classes = element.attrs.get("class", "").split()
    return element.tag in IGNORED_TAGS or "docs-source" in classes


def text_content(element):
    parts = []

    def collect(current):
        if isinstance(current, str):
            parts.append(current)
        elif not is_ignored(current):
            for child in current.children:
                collect(child)

    collect(element)
    return " ".join(" ".join(parts).split())


def visible_events(element):
    for child in element.children:
        if isinstance(child, str):
            yield ("text", child)
        elif not is_ignored(child):
            if child.tag in {f"h{level}" for level in range(1, 7)}:
                yield ("heading", child)
            else:
                yield from visible_events(child)


def route_for(relative_path):
    if relative_path == "index.html":
        return "/"
    if relative_path.endswith("/index.html"):
        return "/" + relative_path[: -len("index.html")]
    return "/" + relative_path


def is_noindex(root):
    return any(
        element.tag == "meta"
        and element.attrs.get("name", "").lower() == "robots"
        and "noindex" in element.attrs.get("content", "").lower()
        for element in walk_elements(root)
    )


def collect_records(site):
    records = []
    for page in sorted(site.rglob("*.html")):
        parser = DocumentParser()
        parser.feed(page.read_text(encoding="utf-8"))
        if is_noindex(parser.root):
            continue

        main = next(
            (element for element in walk_elements(parser.root)
             if element.tag == "main" and element.attrs.get("id") == "main"),
            None,
        )
        if main is None:
            continue

        relative_path = page.relative_to(site).as_posix()
        route = route_for(relative_path)
        page_title = None
        record = None
        page_anchors = set()
        for event_type, value in visible_events(main):
            if event_type == "heading":
                if record is not None:
                    record["body"] = " ".join(record.pop("_body_parts")).strip()
                    records.append(record)

                heading = text_content(value)
                anchor = value.attrs.get("id", "").strip()
                if not anchor:
                    raise ValueError(f"{relative_path}: heading {heading!r} has no id.")
                if anchor in page_anchors:
                    raise ValueError(f"{relative_path}: duplicate heading id {anchor!r}.")
                page_anchors.add(anchor)
                if page_title is None:
                    page_title = heading
                record = {
                    "id": f"{route}#{anchor}",
                    "pageTitle": page_title,
                    "heading": heading,
                    "body": "",
                    "url": f"{route}#{anchor}",
                    "_body_parts": [],
                }
            elif record is not None:
                record["_body_parts"].append(value)

        if record is not None:
            record["body"] = " ".join(" ".join(record.pop("_body_parts")).split())
            records.append(record)

    if not records:
        raise ValueError(f"No searchable heading sections found in {site}.")
    return records


def main():
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    if not site.is_dir():
        sys.exit(f"Built site directory does not exist: {site}")
    try:
        records = collect_records(site)
    except (OSError, ValueError) as error:
        sys.exit(str(error))

    index = {"version": 1, "records": records}
    output = site / "search-index.json"
    output.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Generated {len(records)} search sections in {output}")


if __name__ == "__main__":
    main()
