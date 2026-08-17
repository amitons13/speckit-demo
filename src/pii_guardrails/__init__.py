"""PII Guardrails MVP: Detection API and Redaction API.

Exactly two primary APIs, sharing one reusable PII detection component that is
isolated behind a swappable detector interface (OpenAI-backed in this MVP).
"""

__all__ = ["__version__"]
__version__ = "0.1.0"
