"""
Router Node
===========

Classifica a query do usuário e extrai entidades usando IA.
Determina quais nós devem ser executados.

100% IA - sem regras hardcoded.
"""

import json
import re

from app.llm import get_fast_llm
from app.graph.state import AuditState


def router_node(state: AuditState) -> dict:
    """
    Classifica a query e extrai entidades usando LLM.
    
    A IA analisa a query e decide:
    - Qual tipo de consulta (policy, email, transaction, fraud, general)
    - Quais entidades foram mencionadas (pessoas, valores, datas)
    
    Args:
        state: Estado atual do grafo
        
    Returns:
        Atualizações para o estado (query_type, entities)
    """
    query = state["query"]
    
    try:
        result = _classify_with_llm(query)
        
        return {
            "query_type": result.get("query_type", "general"),
            "entities": result.get("entities", []),
            "nodes_visited": ["router"],
            "router_method": "llm"
        }
        
    except Exception as e:
        # Se LLM falhar completamente, usar tipo genérico
        return {
            "query_type": "general",
            "entities": [],
            "nodes_visited": ["router"],
            "router_method": "error",
            "error": f"Router LLM error: {str(e)}"
        }


def _classify_with_llm(query: str) -> dict:
    """
    Usa LLM para classificar a query e extrair entidades.
    
    Args:
        query: Query do usuário
        
    Returns:
        Dicionário com query_type e entities
    """
    prompt = f"""Você é um classificador de consultas para um sistema de auditoria corporativa.

Analise a consulta abaixo e classifique-a em UMA das categorias:

CATEGORIAS:
- "fraud": Investigação de fraudes, irregularidades, smurfing, conflito de interesse, desvios, esquemas, cruzamento de dados para detectar problemas
- "transaction": Consultas sobre transações financeiras, gastos, despesas, compras, pagamentos, reembolsos, valores
- "email": Consultas sobre comunicações, emails, mensagens, correspondências
- "policy": Consultas sobre regras, políticas, limites, compliance, normas, procedimentos, o que é permitido/proibido
- "general": Outras consultas que não se encaixam nas anteriores

INSTRUÇÕES:
1. Se a consulta mencionar investigação, fraude, irregularidade, ou pedir para cruzar informações -> "fraud"
2. Se perguntar sobre uma pessoa específica E gastos/transações -> "transaction" 
3. Se perguntar sobre uma pessoa E quiser investigar -> "fraud"
4. Se mencionar apenas emails ou comunicações -> "email"
5. Se perguntar sobre regras ou políticas da empresa -> "policy"

EXTRAÇÃO DE ENTIDADES:
- Extraia nomes de pessoas mencionadas
- Extraia valores monetários (ex: $500, 1000 dólares)
- Extraia datas se mencionadas

CONSULTA: {query}

Responda APENAS com JSON válido no formato:
{{"query_type": "categoria", "entities": ["lista", "de", "entidades"]}}
"""

    llm = get_fast_llm()
    response = llm.invoke(prompt)
    
    return _parse_router_response(response.content)


def _parse_router_response(response_text: str) -> dict:
    """
    Extrai o JSON da resposta do LLM.
    
    Args:
        response_text: Resposta raw do LLM
        
    Returns:
        Dicionário com query_type e entities
    """
    # Limpar resposta
    response_text = response_text.strip()
    
    # Tentar extrair JSON diretamente
    try:
        # Procurar por bloco JSON na resposta
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            # Validar query_type
            valid_types = ["fraud", "transaction", "email", "policy", "general"]
            if result.get("query_type") not in valid_types:
                result["query_type"] = "general"
            return result
    except json.JSONDecodeError:
        pass
    
    # Fallback: tentar parsear como JSON direto
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Retornar default se nada funcionar
    return {"query_type": "general", "entities": []}


def get_next_nodes(query_type: str) -> list[str]:
    """
    Determina quais nós devem ser executados baseado no tipo de query.
    
    Args:
        query_type: Tipo de query classificado
        
    Returns:
        Lista de nomes dos próximos nós
    """
    routing_map = {
        "policy": ["rag"],
        "email": ["rag", "email"],
        "transaction": ["rag", "transaction"],
        "fraud": ["rag", "email", "transaction", "fraud"],
        "general": ["rag"]
    }
    
    return routing_map.get(query_type, ["rag"])
