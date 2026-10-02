#!/usr/bin/env python3
"""Extract CV metadata (name + contact links) from a Markdown source.

Emits either HTML <meta> tags (promoted to PDF info metadata by
``weasyprint --custom-metadata``) or an XMP/RDF block (appended with
``weasyprint --xmp-metadata``).

Usage:
    cvmeta.py SOURCE.md --format meta
    cvmeta.py SOURCE.md --format xmp
    cvmeta.py SOURCE.md --format slug
    cvmeta.py SOURCE.md --format name
"""

import argparse
import re
import unicodedata

XMP_NS = "urn:cv-builder:1.0"

# Labels that should map to a fixed metadata key regardless of their URL.
LABELS = {
    "linkedin": "linkedin",
    "github": "github",
    "gitlab": "gitlab",
    "twitter": "twitter",
    "x": "x",
    "open source": "opensource",
    "website": "website",
}
TLDS = ("com", "org", "net", "dev", "io", "app", "co", "me", "xyz", "site")


def header_block(text):
    """Everything before the first "###" heading (the contact block)."""

    lines = []
    for line in text.splitlines():
        if line.startswith("###"):
            break
        lines.append(line)
    return lines


def meta_name(label, url):
    """Return the metadata key for a header-block link."""

    if url.startswith("mailto:"):
        return "email"
    if url.startswith("tel:"):
        return "phone"
    key = LABELS.get(label.strip().lower())
    if key:
        return key
    value = re.sub(r"\.(" + "|".join(TLDS) + r")$", "", label.strip().lower())
    return re.sub(r"[^a-z0-9]+", "", value) or "link"


def collect(text):
    """Return (name, [(key, url), ...])."""

    lines = header_block(text)

    name = None
    for line in lines:
        match = re.match(r"^#{1,2}\s+(.+?)\s*$", line)
        if match:
            name = match.group(1)
            break

    links = []
    seen = set()
    for label, url in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", "\n".join(lines)):
        key = meta_name(label, url)
        if key in seen:
            continue
        seen.add(key)
        links.append((key, url))
    return name, links


def as_meta(links):
    """Render links as HTML <meta> tags."""

    return "\n".join(f'<meta name="{key}" content="{url}" />' for key, url in links)


def slugify(value):
    """Turn a name into a filename slug (e.g. "Jane Doe" -> "Jane-Doe")."""

    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")


def xml_escape(value):
    """Escape a string for XML text content."""

    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def as_xmp(name, links):
    """Render the name and links as an XMP/RDF block."""

    fields = []
    if name:
        fields.append(f"    <cv:name>{xml_escape(name)}</cv:name>")
    for key, url in links:
        fields.append(f"    <cv:{key}>{xml_escape(url)}</cv:{key}>")
    body = "\n".join(fields)
    return (
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        f'  <rdf:Description rdf:about="" xmlns:cv="{XMP_NS}">\n'
        f"{body}\n"
        "  </rdf:Description>\n"
        "</rdf:RDF>"
    )


def main():
    """CLI entry point: print the requested representation to stdout."""

    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--format", choices=("meta", "xmp", "slug", "name"), default="meta")
    args = parser.parse_args()

    with open(args.source, encoding="utf-8") as handle:
        name, links = collect(handle.read())

    if args.format == "meta":
        print(as_meta(links))
    elif args.format == "slug":
        print(slugify(name))
    elif args.format == "name":
        print(name or "")
    else:
        print(as_xmp(name, links))


if __name__ == "__main__":
    main()
