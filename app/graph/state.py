"""
Estado do Grafo de Auditoria
============================

Define o TypedDict que representa o estado compartilhado
entre todos os nós do LangGraph.
"""

from typing import TypedDict, Annotated, Sequence, Optional
from operator import add


class EmailResult(TypedDict):
    """Resultado de busca em emails."""
    de: str
    para: str
    data: str
    assunto: str
    mensagem: str
    linha: int  # Linha no arquivo original para referência


class TransactionResult(TypedDict):
    """Resultado de análise de transação."""
    id_transacao: str
    data: str
    funcionario: str
    cargo: str
    descricao: str
    valor: float
    categoria: str
    departamento: str
    violacoes: list[str]  # Lista de violações detectadas


class FraudAlert(TypedDict):
    """Alerta de fraude detectado."""
    tipo: str  # Tipo de fraude (smurfing, conflito_interesse, etc.)
    severidade: str  # baixa, media, alta, critica
    funcionario: str
    descricao: str
    evidencias_email: list[int]  # Linhas dos emails como evidência
    evidencias_transacao: list[str]  # IDs das transações
    valor_total: float
    regra_violada: str  # Seção da política violada


class AuditState(TypedDict):
    """
    Estado compartilhado entre todos os nós do grafo.
    
    Este estado é passado de nó em nó, sendo atualizado
    conforme cada agente processa a informação.
    """
    
    # Input do usuário
    query: str
    
    # Classificação da query (definido pelo router)
    query_type: str  # policy, email, transaction, fraud, general
    entities: list[str]  # Entidades mencionadas (nomes, valores, etc.)
    
    # Resultados do RAG (política de compliance)
    policy_context: Annotated[list[str], add]  # Chunks relevantes
    policy_sections: list[str]  # Seções específicas citadas
    
    # Resultados de busca em emails
    email_results: Annotated[list[EmailResult], add]
    
    # Resultados de análise de transações
    transaction_results: Annotated[list[TransactionResult], add]
    transactions_analyzed: int  # Total de transações analisadas
    
    # Alertas de fraude
    fraud_alerts: Annotated[list[FraudAlert], add]
    
    # Resposta final
    final_response: str
    evidence_summary: str  # Resumo das evidências usadas
    
    # Metadados
    nodes_visited: Annotated[list[str], add]  # Para debug/rastreamento
    error: Optional[str]  # Mensagem de erro, se houver


def create_initial_state(query: str) -> AuditState:
    """
    Cria um estado inicial para uma nova consulta.
    
    Args:
        query: Pergunta do usuário
        
    Returns:
        Estado inicial do grafo
    """
    return AuditState(
        query=query,
        query_type="",
        entities=[],
        policy_context=[],
        policy_sections=[],
        email_results=[],
        transaction_results=[],
        transactions_analyzed=0,
        fraud_alerts=[],
        final_response="",
        evidence_summary="",
        nodes_visited=[],
        error=None
    )
