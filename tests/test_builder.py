import os
import subprocess

import pytest
from pypdf import PdfReader


def docker_run(workspace, image, output, extra_env=(), container_args=()):
    command = [
        "docker", "run", "--rm",
        "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp",
        "-v", f"{workspace}:/github/workspace", "-w", "/github/workspace",
        "-e", "INPUT_FILES=example.md", "-e", f"INPUT_OUTPUT={output}",
    ]
    for value in extra_env:
        command += ["-e", value]
    command += [image, *container_args]
    return command


@pytest.mark.integration
def test_builds_named_pdf(image, workspace):
    subprocess.run(
        docker_run(workspace, image, "out"),
        check=True, capture_output=True)

    pdf = workspace / "out" / "Jane-Doe-CV.pdf"
    assert pdf.read_bytes()[:5] == b"%PDF-"


@pytest.mark.integration
def test_pdf_info_metadata(image, workspace):
    subprocess.run(
        docker_run(workspace, image, "out"),
        check=True, capture_output=True)

    metadata = PdfReader(workspace / "out" / "Jane-Doe-CV.pdf").metadata
    assert metadata.get("/Title") == "Jane Doe — Curriculum Vitae"
    assert metadata.get("/Author") == "Jane Doe"
    assert metadata.get("/linkedin") == "https://linkedin.com/in/janedoe"
    assert metadata.get("/github") == "https://github.com/janedoe"


@pytest.mark.integration
def test_pdf_xmp_metadata(image, workspace):
    subprocess.run(
        docker_run(workspace, image, "out"),
        check=True, capture_output=True)

    reader = PdfReader(workspace / "out" / "Jane-Doe-CV.pdf")
    xmp = reader.trailer["/Root"]["/Metadata"].get_object().get_data().decode()
    assert "<cv:name>Jane Doe</cv:name>" in xmp
    assert "<cv:linkedin>https://linkedin.com/in/janedoe</cv:linkedin>" in xmp


@pytest.mark.integration
def test_custom_metadata_and_directory(image, workspace):
    (workspace / "cv").mkdir()
    (workspace / "cv" / "cv.md").write_text(
        "# Jane Doe\n\n[jane@example.com](mailto:jane@example.com)\n\n### About\n\nHi.\n")
    (workspace / "meta.yaml").write_text(
        "---\ntitle: Custom Title\nauthor: Jane Doe\ncreator: Jane Doe\n"
        "description-meta: Custom Subject\nkeywords: [one, two]\n---\n")

    subprocess.run(
        docker_run(
            workspace, image, "custom",
            extra_env=("INPUT_FILES=", "INPUT_DIRECTORY=cv", "INPUT_METADATA=meta.yaml"),
        ),
        check=True, capture_output=True)

    metadata = PdfReader(workspace / "custom" / "Jane-Doe-CV.pdf").metadata
    assert metadata.get("/Title") == "Custom Title"
    assert metadata.get("/Creator") == "Jane Doe"
    assert metadata.get("/Subject") == "Custom Subject"
    assert metadata.get("/Keywords") == "one, two"
