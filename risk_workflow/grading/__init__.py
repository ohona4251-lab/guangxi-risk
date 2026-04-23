"""Rule-based risk grading utilities.

This package reads existing rule/KG artifacts and writes node5 grading results.
It does not run or modify the KG construction pipeline.
"""

from .engine import run_batch_grading

__all__ = ["run_batch_grading"]
