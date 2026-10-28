#!/usr/bin/env python3
"""Copy the public Talewright docs from a squid-farm/talewright checkout into this site.

The docs are maintained in squid-farm/talewright under docs/. This script only
transforms a copy for publishing; never edit the generated docs/ folder here.
"""

import argparse
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import sys

REPO_URL = "https://github.com/squid-farm/talewright"
BRANCH = "main"

# Developer/technical material stays on GitHub, outside the public flow.
EXCLUDED = ("developer/", "guide/debugger-test-plan.md")
SECTION_INDEXES = ("guide/README.md", "README.md")

LINK = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\))")
FENCE = re.compile(r"^\s*(```|~~~)")


def is_public(rel):
    return rel.endswith(".md") and not any(rel == e or rel.startswith(e) for e in EXCLUDED)


def output_name(rel):
    """docs/guide/README.md becomes docs/guide/index.md so it serves at /docs/guide/."""
    path = PurePosixPath(rel)
    return str(path.with_name("index.md")) if path.name == "README.md" else rel


def page_url(rel):
    """URL path relative to /docs/: '' for the docs home, 'guide/' for an index page."""
    out = output_name(rel)
    return out[: -len("index.md")] if out.endswith("index.md") else out[:-3] + ".html"


def rewrite_target(target, rel, public, assets):
    if re.match(r"^[a-z][a-z0-9+.-]*:|^#|^/", target, re.I):
        return target
    path, _, anchor = target.partition("#")
    anchor = "#" + anchor if anchor else ""
    source_dir = posixpath.dirname(rel) or "."
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(rel), path))
    if resolved.startswith("../"):
        return f"{REPO_URL}/blob/{BRANCH}/{resolved[3:]}{anchor}"
    if resolved in public:
        url = page_url(resolved)
        link = posixpath.relpath(url or ".", source_dir)
        if url == "" or url.endswith("/"):
            link = link.rstrip("/") + "/" if link != "." else "./"
        return link + anchor
    if resolved in assets:
        return path + anchor
    return f"{REPO_URL}/blob/{BRANCH}/docs/{resolved}{anchor}"


def rewrite_links(text, rel, public, assets):
    lines, in_fence = [], False
    for line in text.splitlines(keepends=True):
        if FENCE.match(line):
            in_fence = not in_fence
        if in_fence or FENCE.match(line):
            lines.append(line)
            continue
        # Leave inline code spans untouched; only odd-indexed parts are code.
        parts = re.split(r"(`+[^`]*`+)", line)
        for i in range(0, len(parts), 2):
            parts[i] = LINK.sub(
                lambda m: m.group(1) + rewrite_target(m.group(2), rel, public, assets) + m.group(3),
                parts[i])
        lines.append("".join(parts))
    return "".join(lines)


def plain(text):
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return re.sub(r"\s+", " ", re.sub(r"[*_`>#]", "", text)).strip()


def title_and_description(text, rel):
    title = next((plain(l[2:]) for l in text.splitlines() if l.startswith("# ")), None)
    if not title:
        sys.exit(f"{rel}: public docs need a level-one heading for the page title.")
    paragraph, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        skip = in_fence or line.startswith("#") or line.lstrip().startswith(("|", "!", "<", "- ", "1."))
        if skip or not line.strip():
            if paragraph:
                break
            continue
        paragraph.append(line.strip())
    description = plain(" ".join(paragraph)) or f"Talewright documentation: {title}."
    if len(description) > 160:
        description = description[:157].rsplit(" ", 1)[0] + "..."
    return title, description


def nav_order(source, public):
    """Order pages the way the docs' own index pages list them."""
    order = []
    for index in SECTION_INDEXES:
        for _, target, _ in LINK.findall((source / index).read_text(encoding="utf-8")):
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(index), target.split("#")[0]))
            if resolved in public and resolved not in order:
                order.append(resolved)
    return {rel: i + 1 for i, rel in enumerate(order)}


def yaml_string(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("talewright", type=Path, help="Path to a squid-farm/talewright checkout")
    parser.add_argument("output", type=Path, help="Output folder, normally docs")
    parser.add_argument("--commit", default="", help="Source commit recorded on each page")
    args = parser.parse_args()

    source = args.talewright / "docs"
    if not (source / "README.md").is_file():
        sys.exit(f"No docs/README.md found under {args.talewright}")
    files = sorted(p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file())
    public = {f for f in files if is_public(f)}
    assets = {f for f in files if f.startswith("images/")}
    order = nav_order(source, public)

    if args.output.exists():
        shutil.rmtree(args.output)
    for rel in sorted(public):
        text = (source / rel).read_text(encoding="utf-8")
        if text.startswith("---"):
            sys.exit(f"{rel}: front matter in source docs is not supported.")
        title, description = title_and_description(text, rel)
        section = rel.split("/")[0] if "/" in rel else "home"
        front = [
            "---",
            "layout: doc",
            f"title: {yaml_string(title)}",
            f"description: {yaml_string(description)}",
            f"section: {section}",
            f"nav_order: {order.get(rel, 999)}",
            f"source_path: {yaml_string('docs/' + rel)}",
            f"source_commit: {yaml_string(args.commit)}",
            "---",
            # Talemark examples use braces; never let Liquid interpret doc content.
            "{% raw %}",
        ]
        body = rewrite_links(text, rel, public, assets)
        target = args.output / output_name(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(front) + "\n" + body.rstrip("\n") + "\n{% endraw %}\n", encoding="utf-8")
    for rel in sorted(assets):
        target = args.output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, target)
    print(f"Published {len(public)} docs pages and {len(assets)} images to {args.output}")


if __name__ == "__main__":
    main()
