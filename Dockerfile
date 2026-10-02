# syntax=docker/dockerfile:1

# cv-builder: build CV PDFs from Markdown with pandoc + WeasyPrint.
#
# Used as a GitHub Docker container action (see action.yml) and directly:
#   docker build -t cv-builder .
#   docker run --rm -v "$PWD:/github/workspace" -w /github/workspace \
#     -e INPUT_FILES="cv.md" cv-builder
#   # -> ./build/<name>-CV.pdf

FROM debian:bookworm-slim

# Matches the pandoc that Ubuntu 24.04 (GitHub's runner) ships.
ARG PANDOC_VERSION=3.1.3
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        curl \
        ca-certificates \
        fontconfig \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz-subset0 \
        fonts-dejavu-core \
        fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

# Official static pandoc: a single binary, rather than apt's package which
# pulls in a large Haskell dependency tree.
RUN curl -sSL \
      "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-amd64.tar.gz" \
      | tar -xz -C /usr/local --strip-components=1 \
    && pandoc --version | head -1

# fonts-noto-core ships Noto Sans Regular/Bold, but weight 500 (Medium) only
# lives in the bulky fonts-noto-extra package; fetch just that face instead.
RUN font_url=$(curl -sS -A '' \
        "https://fonts.googleapis.com/css2?family=Noto+Sans:wght@500" \
        | grep -oE 'https://[^)]+\.ttf' | head -1) \
    && test -n "$font_url" \
    && mkdir -p /usr/share/fonts/truetype/noto \
    && curl -sSL -o /usr/share/fonts/truetype/noto/NotoSans-Medium.ttf "$font_url" \
    && fc-cache -f

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip weasyprint
ENV PATH="/opt/venv/bin:$PATH"

# Install the package from pyproject.toml (gives us the `cv-builder` entry point
# and the built-in template/stylesheet as package data).
COPY . /opt/cv
RUN /opt/venv/bin/pip install --no-cache-dir /opt/cv \
    && rm -rf /opt/cv

WORKDIR /github/workspace
ENTRYPOINT ["cv-builder"]
