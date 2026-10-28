# Talewright website

Source for <https://www.trytalewright.com>: the marketing pages and the hosted documentation at
<https://www.trytalewright.com/docs/>. The web player is separate, at <https://play.trytalewright.com>,
and deploys from [squid-farm/talewright](https://github.com/squid-farm/talewright).

## Where the docs live

**The public docs are maintained in [squid-farm/talewright](https://github.com/squid-farm/talewright/tree/main/docs),
next to the code. Edit them there, not here.**

This repository has no copy of the docs. On every build, the workflow checks out `docs/` from
`squid-farm/talewright` `main` and [`scripts/sync_docs.py`](scripts/sync_docs.py) copies the public pages into
a generated, git-ignored `docs/` folder:

- Published: `docs/README.md`, `docs/guide/` and `docs/reference/`, plus `docs/images/`.
- Not published: `docs/developer/` and `docs/guide/debugger-test-plan.md`. Links to them, and to anything
  else outside `docs/`, point to GitHub.
- Each page gets its title and description from its first heading and paragraph, and links to its source file.

The site rebuilds on every push to `main`, daily at 06:23 UTC, and when you run the **Site** workflow
manually. Run it manually after merging a docs change in `squid-farm/talewright` to publish it straight away.

## What's here

| Path | Purpose |
|---|---|
| `index.html`, `getting-started.html`, `404.html` | Marketing pages (HTML with Jekyll front matter) |
| `_layouts/` | Shared page layout and the docs layout with its sidebar |
| `_data/doc_sections.yml` | Docs sidebar groups |
| `assets/site.css` | All styling |
| `scripts/sync_docs.py` | Copies and adapts the public docs |
| `scripts/check_site.py` | Checks required pages, titles, descriptions, internal links and anchors |
| `.github/workflows/site.yml` | Builds and checks on pull requests; deploys from `main` |

The site uses GitHub Pages' built-in Jekyll ([`actions/jekyll-build-pages`](https://github.com/actions/jekyll-build-pages)).
There is no JavaScript, package manager or theme dependency.

## Build locally

You need Python 3 and Docker (or Podman), plus a checkout of `squid-farm/talewright`.

```bash
python3 scripts/sync_docs.py ../talewright docs
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/site" -e GITHUB_WORKSPACE=/site \
  -e INPUT_SOURCE=./ -e INPUT_DESTINATION=./_site -e GITHUB_REPOSITORY=squid-farm/talewright-site \
  ghcr.io/actions/jekyll-build-pages:v1.0.13
python3 scripts/check_site.py _site
python3 -m http.server -d _site 8000
```

## Deployment

GitHub Pages for this repository must use **Source: GitHub Actions** and the custom domain
`www.trytalewright.com` with **Enforce HTTPS**. Pull requests only build and check; pushes to `main`,
scheduled runs and manual runs on `main` deploy. The workflow uses the default `GITHUB_TOKEN` with
read-only contents access. Only the deploy job gets `pages: write` and `id-token: write`.

## Content and licensing

Documentation text and screenshots come from `squid-farm/talewright`, licensed under the
[Mozilla Public License 2.0](https://github.com/squid-farm/talewright/blob/main/LICENSE).
Keep marketing claims in line with the product README and docs. Talewright is a pre-1.0 preview.
