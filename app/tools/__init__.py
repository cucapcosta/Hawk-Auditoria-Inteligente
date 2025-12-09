"""
Tools Module
============

Ferramentas auxiliares para processamento de dados.
"""

# Lazy imports para evitar problemas de dependência
def get_vector_store_manager():
    from .vector_store import get_vector_store_manager as _get
    return _get()

def get_email_parser():
    from .email_parser import EmailParser
    return EmailParser()

def get_transaction_analyzer():
    from .transaction_rules import get_transaction_analyzer as _get
    return _get()

__all__ = ["get_vector_store_manager", "get_email_parser", "get_transaction_analyzer"]
