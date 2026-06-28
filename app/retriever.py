"""FAISS-backed semantic chunk retriever using bag-of-words vectors.

Provides :class:`FaissRetriever` which:

1. Builds a shared vocabulary from all ingested chunks.
2. Represents each chunk as a L2-normalised bag-of-words vector.
3. Uses FAISS ``IndexFlatIP`` (inner product = cosine on unit vectors) to
   find the most similar chunks to any query string.

A pure-Python keyword-overlap fallback is used automatically when the
``faiss`` package is not installed, so the agent remains functional without
native dependencies.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import faiss  # type: ignore[import-untyped]

    _FAISS_AVAILABLE = True
except ImportError:
    _FAISS_AVAILABLE = False

__all__ = ["FaissRetriever"]

_TOKEN_RE = re.compile(r"\w+")


def _tokenize(text: str) -> List[str]:
    """Return a list of lowercase word tokens extracted from *text*.

    Parameters
    ----------
    text :
        Input string to tokenise.

    Returns
    -------
    list of str
        Lowercase alphanumeric tokens.
    """
    return _TOKEN_RE.findall(text.lower())


def _build_vocab(
    chunks: List[dict],
    min_df: int,
) -> Dict[str, int]:
    """Build a term-to-index vocabulary from *chunks*.

    Terms appearing in fewer than *min_df* distinct chunks are excluded.

    Parameters
    ----------
    chunks :
        Sequence of document chunk dicts with a ``page_content`` key.
    min_df :
        Minimum document frequency threshold.

    Returns
    -------
    dict
        Mapping of term string → integer column index (sorted for
        determinism).
    """
    doc_freq: Dict[str, int] = {}
    for chunk in chunks:
        seen = set(_tokenize(chunk.get("page_content", "")))
        for token in seen:
            doc_freq[token] = doc_freq.get(token, 0) + 1

    return {
        term: idx
        for idx, term in enumerate(
            sorted(t for t, cnt in doc_freq.items() if cnt >= min_df)
        )
    }


class FaissRetriever:
    """Semantic chunk retriever backed by FAISS inner-product search.

    Parameters
    ----------
    chunks :
        Non-empty list of document chunk dicts.
    min_df :
        Minimum document frequency for vocabulary terms.  Default 1 includes
        all terms, which is appropriate for small corpora.

    Raises
    ------
    ValueError
        When *chunks* is empty or *min_df* < 1.
    """

    def __init__(self, chunks: List[dict], min_df: int = 1) -> None:
        if not chunks:
            raise ValueError("chunks must not be empty")
        if min_df < 1:
            raise ValueError(f"min_df must be >= 1, got {min_df}")

        self._chunks: List[dict] = chunks
        self._vocab: Dict[str, int] = _build_vocab(chunks, min_df)
        self._index: Optional[object] = None  # faiss index or None

        if _FAISS_AVAILABLE and self._vocab:
            self._index = self._build_faiss_index()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _vectorise(self, text: str) -> np.ndarray:
        """Convert text to a L2-normalised bag-of-words vector.

        Parameters
        ----------
        text :
            Input text string.

        Returns
        -------
        numpy.ndarray
            Shape ``(vocab_size,)`` float32 array.  The zero vector is
            returned (without normalisation) when no vocabulary tokens are
            present.
        """
        vec = np.zeros(len(self._vocab), dtype=np.float32)
        for token in _tokenize(text):
            if token in self._vocab:
                vec[self._vocab[token]] += 1.0
        norm = float(np.linalg.norm(vec))
        if norm > 0.0:
            vec /= norm
        return vec

    def _build_faiss_index(self) -> "faiss.IndexFlatIP":
        """Build and populate a FAISS ``IndexFlatIP`` from all chunks.

        Returns
        -------
        faiss.IndexFlatIP
            Index populated with one vector per chunk.
        """
        dim = len(self._vocab)
        index = faiss.IndexFlatIP(dim)  # type: ignore[attr-defined]
        matrix = np.stack(
            [self._vectorise(c.get("page_content", "")) for c in self._chunks]
        )
        index.add(matrix)
        return index

    def _fallback_query(
        self,
        query_tokens: set,
        k: int,
    ) -> List[Tuple[int, dict]]:
        """Keyword-overlap ranking used when FAISS is unavailable.

        Parameters
        ----------
        query_tokens :
            Set of lowercase tokens from the query string.
        k :
            Number of top results.

        Returns
        -------
        list of tuple
            Up to *k* ``(overlap_count, chunk)`` pairs sorted descending.
        """
        scored = [
            (len(query_tokens & set(_tokenize(c.get("page_content", "")))), c)
            for c in self._chunks
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:k]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query(self, query_text: str, k: int = 5) -> List[dict]:
        """Retrieve the *k* most similar chunks to *query_text*.

        Uses FAISS inner-product search when available; falls back to
        keyword-overlap ranking otherwise.

        Parameters
        ----------
        query_text :
            Natural-language or keyword query string.
        k :
            Number of results to return.  Must be ≥ 1.

        Returns
        -------
        list of dict
            Up to *k* most similar chunks, highest-similarity first.

        Raises
        ------
        ValueError
            When *k* < 1.
        """
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")

        effective_k = min(k, len(self._chunks))

        if _FAISS_AVAILABLE and self._index is not None:
            q_vec = self._vectorise(query_text).reshape(1, -1)
            _, indices = self._index.search(q_vec, effective_k)  # type: ignore[union-attr]
            return [
                self._chunks[int(i)]
                for i in indices[0]
                if 0 <= int(i) < len(self._chunks)
            ]

        # Pure-Python fallback
        query_tokens = set(_tokenize(query_text))
        return [c for _, c in self._fallback_query(query_tokens, effective_k)]
