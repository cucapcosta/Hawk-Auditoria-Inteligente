"""
Workflow do Grafo de Auditoria
==============================

Define o grafo LangGraph que orquestra todos os nós de auditoria.
"""

from typing import Literal
from langgraph.graph import StateGraph, END

from app.graph.state import AuditState, create_initial_state

# Import nodes diretamente (evitar circular import via __init__)
from app.nodes.router_node import router_node, get_next_nodes
from app.nodes.rag_node import rag_node
from app.nodes.email_node import email_node
from app.nodes.transaction_node import transaction_node
from app.nodes.fraud_node import fraud_node
from app.nodes.synthesizer_node import synthesizer_node


def create_audit_graph() -> StateGraph:
    """
    Cria o grafo de auditoria.
    
    Fluxo:
    1. Router classifica a query
    2. Baseado no tipo, executa nós relevantes em paralelo
    3. Synthesizer consolida resultados
    
    Returns:
        Grafo compilado pronto para execução
    """
    # Criar grafo com o estado tipado
    workflow = StateGraph(AuditState)
    
    # Adicionar nós
    workflow.add_node("router", router_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("email", email_node)
    workflow.add_node("transaction", transaction_node)
    workflow.add_node("fraud", fraud_node)
    workflow.add_node("synthesizer", synthesizer_node)
    
    # Definir ponto de entrada
    workflow.set_entry_point("router")
    
    # Definir roteamento condicional após o router
    workflow.add_conditional_edges(
        "router",
        route_by_query_type,
        {
            "policy": "rag",
            "email": "rag",  # Email também consulta política primeiro
            "transaction": "rag",  # Transaction também consulta política
            "fraud": "rag",  # Fraud começa pela política
            "general": "rag"
        }
    )
    
    # Após RAG, decidir próximo passo baseado no query_type
    workflow.add_conditional_edges(
        "rag",
        route_after_rag,
        {
            "email": "email",
            "transaction": "transaction",
            "fraud": "email",  # Fraud precisa de email e transaction
            "synthesizer": "synthesizer"
        }
    )
    
    # Após email, decidir se vai para transaction ou synthesizer
    workflow.add_conditional_edges(
        "email",
        route_after_email,
        {
            "transaction": "transaction",
            "fraud": "transaction",  # Fraud precisa de transaction após email
            "synthesizer": "synthesizer"
        }
    )
    
    # Após transaction, decidir se vai para fraud ou synthesizer
    workflow.add_conditional_edges(
        "transaction",
        route_after_transaction,
        {
            "fraud": "fraud",
            "synthesizer": "synthesizer"
        }
    )
    
    # Fraud sempre vai para synthesizer
    workflow.add_edge("fraud", "synthesizer")
    
    # Synthesizer é o fim
    workflow.add_edge("synthesizer", END)
    
    return workflow.compile()


def route_by_query_type(state: AuditState) -> str:
    """
    Roteia baseado no tipo de query classificado.
    Todos os caminhos começam pelo RAG para ter contexto da política.
    """
    query_type = state.get("query_type", "general")
    
    # Todos começam pelo RAG
    return query_type if query_type in ["policy", "email", "transaction", "fraud", "general"] else "general"


def route_after_rag(state: AuditState) -> str:
    """
    Decide o próximo passo após consultar a política.
    """
    query_type = state.get("query_type", "general")
    
    if query_type == "policy" or query_type == "general":
        return "synthesizer"
    elif query_type == "email":
        return "email"
    elif query_type == "transaction":
        return "transaction"
    elif query_type == "fraud":
        return "email"  # Fraud: primeiro busca emails
    
    return "synthesizer"


def route_after_email(state: AuditState) -> str:
    """
    Decide o próximo passo após buscar emails.
    """
    query_type = state.get("query_type", "general")
    
    if query_type == "fraud":
        return "fraud"  # Precisa analisar transações também
    
    return "synthesizer"


def route_after_transaction(state: AuditState) -> str:
    """
    Decide o próximo passo após analisar transações.
    """
    query_type = state.get("query_type", "general")
    
    if query_type == "fraud":
        return "fraud"
    
    return "synthesizer"


# Instância singleton do grafo compilado
_compiled_graph = None


def get_audit_graph():
    """
    Retorna a instância singleton do grafo compilado.
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = create_audit_graph()
    return _compiled_graph


def run_audit(query: str) -> dict:
    """
    Executa uma consulta de auditoria completa.
    
    Args:
        query: Pergunta do usuário
        
    Returns:
        Estado final com todos os resultados
    """
    graph = get_audit_graph()
    initial_state = create_initial_state(query)
    
    # Executar o grafo
    final_state = graph.invoke(initial_state)
    
    return final_state


def run_audit_stream(query: str):
    """
    Executa uma consulta de auditoria com streaming.
    
    Args:
        query: Pergunta do usuário
        
    Yields:
        Atualizações de estado conforme cada nó é executado
    """
    graph = get_audit_graph()
    initial_state = create_initial_state(query)
    
    # Stream de execução
    for event in graph.stream(initial_state):
        yield event


# Grafo simplificado para queries rápidas (apenas policy)
def create_quick_policy_graph() -> StateGraph:
    """
    Cria um grafo simplificado apenas para consultas de política.
    Mais rápido para perguntas simples sobre regras.
    """
    workflow = StateGraph(AuditState)
    
    workflow.add_node("router", router_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("synthesizer", synthesizer_node)
    
    workflow.set_entry_point("router")
    workflow.add_edge("router", "rag")
    workflow.add_edge("rag", "synthesizer")
    workflow.add_edge("synthesizer", END)
    
    return workflow.compile()


def run_quick_policy_query(query: str) -> dict:
    """
    Executa uma consulta rápida apenas na política.
    """
    graph = create_quick_policy_graph()
    initial_state = create_initial_state(query)
    initial_state["query_type"] = "policy"  # Forçar tipo
    
    return graph.invoke(initial_state)
