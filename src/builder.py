#!/usr/bin/env python3
"""Build CV PDFs from Markdown.

The cv-builder Docker action entrypoint: reads INPUT_* env vars, builds every
requested Markdown file to a PDF (in parallel), and writes the `pdf` / `pdfs`
outputs when running under GitHub Actions.
"""
import concurrent.futures
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

CV_HOME = Path(__file__).resolve().parent.parent
SRC_HOME = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_HOME))
import cvmeta

EXCLUDE = (
    "readme", "changelog", "contributing", "license",
    "code_of_conduct", "security", "authors", "notice", "example",
)


def resolve(value, fallback):
    """Resolve an input path against the workspace, or return the fallback."""
    if value:
        path = Path(value)
        return path if path.is_absolute() else WORKSPACE / path
    return fallback


def find_weasyprint():
    """Locate weasyprint: env override, local venv, then PATH."""
    if os.environ.get("WEASYPRINT"):
        return os.environ["WEASYPRINT"]
    venv = CV_HOME / ".venv" / "bin" / "weasyprint"
    if venv.is_file():
        return str(venv)
    found = shutil.which("weasyprint")
    if not found:
        sys.exit("weasyprint not found")
    return found


def collect_sources():
    """Return the Markdown files to build (INPUT_FILES, else scan INPUT_DIRECTORY)."""

    files_input = os.environ.get("INPUT_FILES", "").strip()
    if files_input:
        return files_input.split()

    directory = os.environ.get("INPUT_DIRECTORY", ".")
    sources = []
    for pattern in sorted(glob.glob(str(WORKSPACE / directory / "*.md"))):
        base = os.path.basename(pattern).lower()
        if any(base.startswith(prefix) for prefix in EXCLUDE):
            continue
        sources.append(os.path.relpath(pattern, WORKSPACE))
    if not sources:
        sys.exit(f"no markdown files found in {directory}")
    return sources


def build_one(info, template, stylesheet, metadata, output_dir, date, weasyprint):
    """Build one source (src, name, slug, count) to a PDF and return the path."""

    src, name, slug, count = info
    if count > 1:
        out = Path(output_dir) / f"{slug}-{Path(src).stem}-CV.pdf"
    else:
        out = Path(output_dir) / f"{slug}-CV.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    html = out.with_suffix(".html")

    work = Path(tempfile.mkdtemp())
    try:
        _, links = cvmeta.collect((WORKSPACE / src).read_text(encoding="utf-8"))
        # Trailing newline mirrors `cvmeta.py`'s print() output.
        (work / "meta.html").write_text(cvmeta.as_meta(links) + "\n", encoding="utf-8")
        (work / "xmp.rdf").write_text(cvmeta.as_xmp(name, links) + "\n", encoding="utf-8")

        pandoc = [
            "pandoc", src, "--standalone", "--wrap=none",
            f"--template={template}",
        ]
        if metadata:
            pandoc.append(f"--metadata-file={metadata}")
        elif name:
            pandoc += [
                "--metadata", f"title={name} — Curriculum Vitae",
                "--metadata", f"author={name}",
                "--metadata", f"creator={name}",
            ]
        pandoc += [
            "--metadata", f"date={date}",
            f"--include-in-header={work / 'meta.html'}",
            "-o", str(html),
        ]
        subprocess.run(pandoc, check=True)

        css_args = ["--stylesheet", str(SRC_HOME / "cv" / "print.css")]
        if stylesheet:
            css_args += ["--stylesheet", str(stylesheet)]
        subprocess.run([
            weasyprint,
            "--custom-metadata",
            "--pdf-variant=pdf/a-3b",
            "--xmp-metadata", str(work / "xmp.rdf"),
            *css_args,
            str(html),
            str(out),
        ], check=True)

        with open(out, "rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise RuntimeError(f"output is not a PDF: {out}")

        print(f"Built {out}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return str(out)


def main():
    """Entry point. collects sources, builds them in parallel and writes outputs."""

    os.chdir(WORKSPACE)

    template = resolve(os.environ.get("INPUT_TEMPLATE"), SRC_HOME / "cv" / "template.html")
    stylesheet = resolve(os.environ.get("INPUT_STYLESHEET"), None)
    metadata = resolve(os.environ.get("INPUT_METADATA"), None)
    output_dir = os.environ.get("INPUT_OUTPUT", "build")
    date = os.environ.get("CV_DATE") or time.strftime("%Y-%m-%d", time.gmtime())
    weasyprint = find_weasyprint()

    if not shutil.which("pandoc"):
        sys.exit("pandoc not found")

    infos = []
    for src in collect_sources():
        name, _ = cvmeta.collect((WORKSPACE / src).read_text(encoding="utf-8"))
        infos.append((src, name, cvmeta.slugify(name) or "cv"))
    counts = Counter(slug for _, _, slug in infos)
    infos = [(src, name, slug, counts[slug]) for src, name, slug in infos]

    status = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(infos)) as pool:
        for future in [pool.submit(
                build_one, info, template, stylesheet, metadata,
                output_dir, date, weasyprint) for info in infos]:
            try:
                future.result()
            except Exception as error:  # noqa: BLE001
                print(error, file=sys.stderr)
                status = 1

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output and status == 0:
        pdfs = sorted(glob.glob(str(Path(output_dir) / "*.pdf")))
        if pdfs:
            with open(github_output, "a", encoding="utf-8") as handle:
                handle.write(f"pdf={pdfs[0]}\n")
                handle.write(f"pdfs={' '.join(pdfs)}\n")

    return status


# Repository to build (GitHub mounts it at /github/workspace).
WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()

if __name__ == "__main__":
    sys.exit(main())
