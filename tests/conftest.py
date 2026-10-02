import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

IMAGE = os.environ.get("IMAGE", "cv-builder:test")


@pytest.fixture(scope="session")
def image():
    if shutil.which("docker") is None:
        pytest.skip("docker not available")
    subprocess.run(
        ["docker", "build", "-q", "-t", IMAGE, str(ROOT)],
        check=True, capture_output=True)
    return IMAGE


@pytest.fixture
def workspace():
    work = Path(tempfile.mkdtemp())
    shutil.copy(ROOT / "examples" / "example.md", work / "example.md")
    yield work
    shutil.rmtree(work, ignore_errors=True)
