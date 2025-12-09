"""
Prompts Module
==============

Templates de prompts para os agentes.
"""

from .templates import (
    ROUTER_PROMPT,
    RAG_PROMPT,
    EMAIL_ANALYSIS_PROMPT,
    TRANSACTION_ANALYSIS_PROMPT,
    FRAUD_DETECTION_PROMPT,
    SYNTHESIZER_PROMPT
)

__all__ = [
    "ROUTER_PROMPT",
    "RAG_PROMPT",
    "EMAIL_ANALYSIS_PROMPT",
    "TRANSACTION_ANALYSIS_PROMPT",
    "FRAUD_DETECTION_PROMPT",
    "SYNTHESIZER_PROMPT"
]
