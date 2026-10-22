"""Smoke: the installable package must be importable under its public name."""

import importlib

import pytest

import open_research_tagging


def test_package_is_importable():
    assert open_research_tagging.__name__ == "open_research_tagging"


def test_package_exposes_version_string():
    version = open_research_tagging.__version__
    assert isinstance(version, str)
    assert version != ""


def test_version_matches_pep440_ish_simple_form():
    """Boundary: version is a non-empty dotted numeric string for now (0.1.0)."""
    parts = open_research_tagging.__version__.split(".")
    assert len(parts) >= 2
    for part in parts:
        assert part.isdigit(), f"unexpected version segment: {part!r}"


def test_importlib_can_load_package_by_name():
    """Failure path adjacent: wrong name must not resolve to this package."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("open_research_tagging_does_not_exist")
