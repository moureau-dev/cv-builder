# cv-builder

A GitHub Action (and Docker image) that turns Markdown CVs into polished PDFs
with [pandoc](https://pandoc.org) and [WeasyPrint](https://weasyprint.org).

It mirrors the look of [`github-markdown-css`](https://github.com/sindresorhus/github-markdown-css),
embeds PDF metadata (title, author, subject,
keywords, creator, dates), writes the contact links into both the PDF info
dictionary and the XMP block, and names each file after the person
(e.g. `Jane-Doe-CV.pdf`).

The action **only produces the PDFs**. Publishing them (e.g. to a GitHub
Release) is up to you — see the examples below.

## Usage in a workflow

Minimal:

```yaml
name: Build CV

on:
  push:
    paths: ["cv.md"]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: moureau-dev/cv-builder@v1
        with:
          files: cv.md
```

Build every Markdown file in a folder:

```yaml
      - uses: moureau-dev/cv-builder@v1
        with:
          directory: cv
          metadata: cv/metadata.yaml
```

Attach the result to a release:

```yaml
name: Build CV

on:
  push:
    paths: ["cv.md"]

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: moureau-dev/cv-builder@v1
        id: cv
        with:
          files: cv.md
          metadata: cv/metadata.yaml   # optional, your custom data

      - name: Publish to a release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release view cv-latest >/dev/null 2>&1 || \
            gh release create cv-latest --target "$GITHUB_SHA" --title "Latest CV"
          gh release upload cv-latest ${{ steps.cv.outputs.pdfs }} --clobber
```

## Usage locally with Docker

Using the published image. `--user` keeps the generated files owned by you and
`HOME` gives the container a writable cache directory:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD:/github/workspace" -w /github/workspace \
  -e INPUT_FILES=cv.md \
  -e INPUT_OUTPUT=out \
  ghcr.io/moureau-dev/cv-builder:v1
# -> out/Jane-Doe-CV.pdf
```

Or build the image yourself:

```bash
docker build -t cv-builder .
docker run --rm \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD:/github/workspace" -w /github/workspace \
  -e INPUT_FILES=cv.md \
  -e INPUT_OUTPUT=out \
  cv-builder
```

Multiple files (built in parallel):

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD:/github/workspace" -w /github/workspace \
  -e INPUT_FILES="cv.md cv-short.md" \
  cv-builder
```

## Inputs

| Input        | Default | Description |
|--------------|---------|-------------|
| `files`      | all `*.md` except README/CHANGELOG/license/example files | Space-separated Markdown files. Overrides `directory`. |
| `directory`  | `.` | Directory scanned for `*.md` when `files` is not set. |
| `metadata`   | derived | Path to a pandoc metadata YAML. When omitted, title/author/creator come from the first heading. |
| `template`   | built-in | Path to a pandoc HTML template. |
| `stylesheet` | — | Extra CSS applied **after** the built-in stylesheet (layers on top). |
| `output`     | `build` | Output directory. |

## Outputs

| Output | Description |
|--------|-------------|
| `pdf`  | Path of the first generated PDF. |
| `pdfs` | Space-separated paths of all generated PDFs. |

## How it works

1. `src/cvmeta.py` reads the header block (everything before the first `###`)
   and extracts the person's name and contact links. It emits HTML `<meta>` tags
   and an XMP/RDF block.
2. `pandoc` renders the Markdown to HTML using the template, injecting the
   metadata and link tags.
3. `weasyprint` lays the HTML out to A4 PDF, applying the built-in stylesheet
   and the XMP metadata, and `--custom-metadata` promotes the link tags into the
   PDF info dictionary.

Each output is named `<Name>-CV.pdf` where `<Name>` is the slugified first
heading. If several sources share a name, the source filename is added:
`<Name>-<source>-CV.pdf`.

## Custom data

- **Metadata** — pass your own pandoc metadata file (title, author,
  `description-meta`, `keywords`, `creator`, `lang`, ...). See
  [`examples/example-metadata.yaml`](examples/example-metadata.yaml) for a starting point.
- **Styling** — override `template` and/or `stylesheet` with paths in your repo.
- **Links** — any `[label](url)` in the header block becomes metadata. Known
  labels (LinkedIn, GitHub, ...) get stable keys; others use a slug of the label
  (e.g. `Moureau.dev` → `cv:moureau`).

## Notes

- The GHCR package must be **public** (or your workflow must authenticate) so
  other repositories can pull the image. Set it under the package's settings.
- Markdown files named `README*`, `CHANGELOG*`, `CONTRIBUTING*`, `LICENSE*`,
  `CODE_OF_CONDUCT*`, `SECURITY*`, `AUTHORS*`, `NOTICE*` and `example*` are
  skipped when `files` is not set. `examples/example.md` is only built when
  named explicitly (as the tests do).

## Development

```bash
pip install -e ".[dev]"
pytest                       # unit + integration tests
pytest -m "not integration"  # skip the Docker-based tests
```

`tests/test_cvmeta.py` covers the parsing/metadata helpers; the
`tests/test_builder.py` integration tests build the image and check the
PDFs and their metadata.

## License

[MIT](LICENSE)
