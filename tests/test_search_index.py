import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_search_index import collect_records
from check_site import Page, check_search_index


class SearchIndexTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.site = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write_page(self, relative_path, content):
        page = self.site / relative_path
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(content, encoding="utf-8")
        return page

    def test_collects_heading_sections_and_excludes_repeated_site_content(self):
        self.write_page(
            "docs/example.html",
            """<html><body>
              <nav><h2 id="nav">Navigation boilerplate</h2></nav>
              <main id="main"><article>
                <h1 id="guide">Example guide</h1>
                <p>Introductory text.</p>
                <h2 id="syntax">Talemark syntax</h2>
                <p>Use <code>@hub</code> to select scenes.</p>
                <p class="docs-source">Repeated source notice.</p>
              </article></main>
              <footer>Repeated footer text.</footer>
            </body></html>""",
        )

        records = collect_records(self.site)

        self.assertEqual([record["heading"] for record in records], ["Example guide", "Talemark syntax"])
        self.assertEqual(records[0]["body"], "Introductory text.")
        self.assertEqual(records[1]["url"], "/docs/example.html#syntax")
        self.assertIn("@hub", records[1]["body"])
        self.assertNotIn("Navigation boilerplate", str(records))
        self.assertNotIn("Repeated footer text", str(records))
        self.assertNotIn("Repeated source notice", str(records))

    def test_rejects_searchable_heading_without_anchor(self):
        self.write_page(
            "index.html",
            "<main id='main'><h1>Unanchored page</h1></main>",
        )

        with self.assertRaisesRegex(ValueError, "has no id"):
            collect_records(self.site)

    def test_check_requires_nonempty_index_and_valid_heading_links(self):
        page = self.write_page(
            "docs/guide/index.html",
            "<main id='main'><h1 id='guide'>Guide</h1><h2 id='syntax'>Syntax</h2></main>",
        )
        parsed_page = Page()
        parsed_page.feed(page.read_text(encoding="utf-8"))
        pages = {page: parsed_page}
        index_file = self.site / "search-index.json"

        self.assertIn("missing generated search index search-index.json", check_search_index(self.site, pages))

        index_file.write_text(json.dumps({"version": 1, "records": []}), encoding="utf-8")
        self.assertIn("search index is empty or has no records", check_search_index(self.site, pages))

        index_file.write_text(
            json.dumps({
                "version": 1,
                "records": [{
                    "id": "/docs/guide/#missing",
                    "pageTitle": "Guide",
                    "heading": "Missing",
                    "body": "",
                    "url": "/docs/guide/#missing",
                }],
            }),
            encoding="utf-8",
        )
        self.assertTrue(any("missing heading" in error for error in check_search_index(self.site, pages)))


if __name__ == "__main__":
    unittest.main()
