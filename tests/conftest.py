"""Pytest fixtures for open-research-tagging tests."""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from codebook_fixtures import REAL_CODEBOOK_PATH

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "site"
RAW_FIXTURE = SITE / "data" / "raw_comments.fixture.json"


@pytest.fixture
def real_codebook_path() -> Path:
    return REAL_CODEBOOK_PATH


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _fill_temp_site_with_fixture_json(site_root: Path) -> None:
    """Process offline fixture into site_root/data (does not touch repo site/)."""
    py = sys.executable
    comments_out = site_root / "data" / "comments.json"
    projects_out = site_root / "data" / "projects.json"
    subprocess.run(
        [
            py,
            "-m",
            "open_research_tagging.process_comments",
            "--in",
            str(RAW_FIXTURE),
            "--out",
            str(comments_out),
            "--repo-root",
            str(REPO_ROOT),
        ],
        check=True,
        cwd=REPO_ROOT,
    )
    subprocess.run(
        [
            py,
            "-m",
            "open_research_tagging.process_projects",
            "--comments",
            str(comments_out),
            "--out",
            str(projects_out),
            "--repo-root",
            str(REPO_ROOT),
        ],
        check=True,
        cwd=REPO_ROOT,
    )


@pytest.fixture(scope="module")
def site_under_test(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copy of site/ with fixture-shaped comments/projects JSON (Playwright only).

    Isolates offline demo data from committed live comments.json on main.
    """
    dest = tmp_path_factory.mktemp("ort-site")
    shutil.copytree(SITE, dest, dirs_exist_ok=True)
    _fill_temp_site_with_fixture_json(dest)
    return dest


@pytest.fixture(scope="module")
def site_base_url(site_under_test: Path):
    """Serve the temp fixture site on a local ephemeral port."""
    port = _free_port()
    proc = subprocess.Popen(
        ["python3", "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=site_under_test,
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
    try:
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
