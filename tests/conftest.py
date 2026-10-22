"""Pytest fixtures for open-research-tagging tests."""

from pathlib import Path

import pytest

from codebook_fixtures import REAL_CODEBOOK_PATH


@pytest.fixture
def real_codebook_path() -> Path:
    return REAL_CODEBOOK_PATH
