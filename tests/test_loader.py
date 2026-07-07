"""Tests for app.loader — Markdown filing loader."""

from __future__ import annotations

import tempfile
import textwrap
from pathlib import Path

import pytest

from app.loader import load_markdown_as_documents


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_filing(tmp_path: Path) -> Path:
    """Create a minimal synthetic filing and return its path."""
    content = textwrap.dedent("""\
        # TEST-2024 Annual Filing (Synthetic)

        ## Business
        TEST provides cloud analytics services.

        ## Results
        Revenue grew 18% with gross margin 80%.

        ## Risk Factors
        - Cybersecurity incidents could result in penalties.
        - Regulatory changes may increase costs.

        ## Liquidity
        Cash: $500M.

        ## Outlook
        Management expects cautious macro conditions.
    """)
    path = tmp_path / "TEST-2024.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_load_returns_list_of_dicts(sample_filing: Path) -> None:
    """Loader returns a non-empty list of document dicts."""
    docs = load_markdown_as_documents(str(sample_filing))
    assert isinstance(docs, list)
    assert len(docs) > 0
    for doc in docs:
        assert "page_content" in doc
        assert "metadata" in doc


def test_load_extracts_all_sections(sample_filing: Path) -> None:
    """Loader extracts one document per ## heading."""
    docs = load_markdown_as_documents(str(sample_filing))
    sections = [d["metadata"]["section"] for d in docs]
    assert "Business" in sections
    assert "Results" in sections
    assert "Risk Factors" in sections
    assert "Liquidity" in sections
    assert "Outlook" in sections


def test_load_preserves_title(sample_filing: Path) -> None:
    """Each document carries the H1 title in metadata."""
    docs = load_markdown_as_documents(str(sample_filing))
    for doc in docs:
        assert "TEST-2024 Annual Filing (Synthetic)" in doc["metadata"]["title"]


def test_load_file_not_found() -> None:
    """FileNotFoundError for a non-existent path."""
    with pytest.raises(FileNotFoundError):
        load_markdown_as_documents("/nonexistent/path.md")


def test_load_empty_file(tmp_path: Path) -> None:
    """ValueError for an empty file."""
    empty = tmp_path / "empty.md"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_markdown_as_documents(str(empty))
