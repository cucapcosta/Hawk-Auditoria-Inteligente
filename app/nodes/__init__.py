"""
Nodes do Grafo de Auditoria
===========================

Cada nó é responsável por uma etapa específica do pipeline:
- router: Classifica a query do usuário
- rag: Busca na política de compliance
- email: Busca em emails corporativos
- transaction: Analisa transações bancárias
- fraud: Detecta fraudes cruzando dados
- synthesizer: Gera resposta final
"""

# Imports lazy para evitar circular imports
def get_router_node():
    from .router_node import router_node
    return router_node

def get_rag_node():
    from .rag_node import rag_node
    return rag_node

def get_email_node():
    from .email_node import email_node
    return email_node

def get_transaction_node():
    from .transaction_node import transaction_node
    return transaction_node

def get_fraud_node():
    from .fraud_node import fraud_node
    return fraud_node

def get_synthesizer_node():
    from .synthesizer_node import synthesizer_node
    return synthesizer_node

__all__ = [
    "get_router_node",
    "get_rag_node",
    "get_email_node",
    "get_transaction_node",
    "get_fraud_node",
    "get_synthesizer_node",
]
