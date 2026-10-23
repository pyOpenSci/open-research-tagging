"""Pytest fixtures for open-research-tagging tests."""

from __future__ import annotations

import socket
import subprocess
import time
from pathlib import Path

import pytest

from codebook_fixtures import REAL_CODEBOOK_PATH

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "site"


@pytest.fixture
def real_codebook_path() -> Path:
    return REAL_CODEBOOK_PATH


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def site_base_url():
    """Serve site/ on a local ephemeral port (Playwright integration tests)."""
    port = _free_port()
    proc = subprocess.Popen(
        ["python3", "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=SITE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 5
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError as err:
            last_err = err
            time.sleep(0.05)
    else:
        proc.kill()
        raise RuntimeError(f"site server did not start: {last_err}")
    yield base
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
