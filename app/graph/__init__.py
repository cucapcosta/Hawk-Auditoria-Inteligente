"""
Graph Module - LangGraph Workflow
=================================

Define o grafo de estados e workflow do sistema de auditoria.
"""

from .state import AuditState, create_initial_state

# Lazy import para evitar circular imports
def get_workflow():
    from .workflow import create_audit_graph, run_audit, run_audit_stream
    return create_audit_graph, run_audit, run_audit_stream

__all__ = ["AuditState", "create_initial_state", "get_workflow"]
