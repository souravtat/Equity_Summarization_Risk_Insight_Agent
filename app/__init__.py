"""Equity Summarisation & Risk Insight Agent — application package.

Exposes the top-level :func:`summarize_filing` callable so external code and
evaluation scripts can import it without touching internal module paths.
"""

from .summarize import summarize_filing

__all__ = ["summarize_filing"]
