"""
Transaction Node
================

Busca e analisa transações financeiras usando IA.
100% IA para análise - sem regras hardcoded.
"""

import json
import re
from app.llm import get_llm
from app.graph.state import AuditState, TransactionResult
from app.tools.transaction_rules import get_transaction_analyzer


def transaction_node(state: AuditState) -> dict:
    """
    Busca transações relevantes e usa IA para analisar.
    
    1. Busca transações baseado na query/entidades
    2. Envia para IA analisar e identificar problemas
    
    Args:
        state: Estado atual do grafo
        
    Returns:
        Atualizações para o estado (transaction_results, transactions_analyzed)
    """
    query = state["query"]
    entities = state.get("entities", [])
    query_type = state.get("query_type", "general")
    policy_context = state.get("policy_context", [])
    
    try:
        # Buscar transações relevantes
        analyzer = get_transaction_analyzer()
        raw_transactions = _get_relevant_transactions(analyzer, query_type, entities)
        
        # Usar IA para analisar as transações
        analyzed_results = _analyze_with_llm(
            query, 
            raw_transactions, 
            policy_context
        )
        
        return {
            "transaction_results": analyzed_results,
            "transactions_analyzed": len(analyzer.df),
            "nodes_visited": ["transaction"]
        }
        
    except Exception as e:
        return {
            "transaction_results": [],
            "transactions_analyzed": 0,
            "nodes_visited": ["transaction"],
            "error": f"Transaction analysis error: {str(e)}"
        }


def _get_relevant_transactions(analyzer, query_type: str, entities: list) -> list[dict]:
    """
    Busca transações relevantes para análise.
    
    Retorna dados raw para a IA analisar.
    """
    transactions = []
    
    # Buscar por funcionários mencionados
    for entity in entities:
        if _is_person_name(entity):
            emp_trans = analyzer.search_by_employee(entity)
            for t in emp_trans:
                transactions.append(_to_dict(t))
    
    # Para fraude, buscar transações de alto valor também
    if query_type == "fraud" and len(transactions) < 20:
        high_value = analyzer.get_high_value_transactions(threshold=200)
        for t in high_value[:20]:
            d = _to_dict(t)
            if d not in transactions:
                transactions.append(d)
    
    # Se não encontrou nada, buscar todas
    if not transactions:
        all_trans = analyzer.analyze_all()[:30]
        transactions = [_to_dict(t) for t in all_trans]
    
    # Limitar
    return transactions[:30]


def _to_dict(t) -> dict:
    """Converte TransactionAnalysis para dict."""
    return {
        "id_transacao": t.id_transacao,
        "data": t.data,
        "funcionario": t.funcionario,
        "cargo": t.cargo,
        "descricao": t.descricao,
        "valor": t.valor,
        "categoria": t.categoria,
        "departamento": t.departamento
    }


def _is_person_name(entity: str) -> bool:
    """Verifica se a entidade parece ser um nome de pessoa."""
    if not entity:
        return False
    
    known_names = [
        "michael", "dwight", "jim", "pam", "ryan", "angela",
        "kevin", "oscar", "stanley", "phyllis", "andy", "creed",
        "meredith", "kelly", "toby", "jan"
    ]
    
    entity_lower = entity.lower()
    for name in known_names:
        if name in entity_lower:
            return True
    
    return entity[0].isupper() and not any(c.isdigit() for c in entity)


def _analyze_with_llm(query: str, transactions: list[dict], policy: list[str]) -> list[TransactionResult]:
    """
    Usa IA para analisar transações e identificar problemas.
    """
    if not transactions:
        return []
    
    # Formatar transações para prompt
    trans_text = ""
    for t in transactions:
        trans_text += f"- {t['id_transacao']} | {t['data']} | {t['funcionario']} ({t['cargo']})\n"
        trans_text += f"  Descrição: {t['descricao']}\n"
        trans_text += f"  Valor: ${t['valor']:.2f} | Categoria: {t['categoria']} | Dept: {t['departamento']}\n\n"
    
    # Formatar política
    policy_text = "\n".join(policy[:3]) if policy else "Não disponível"
    
    prompt = f"""Você é um auditor financeiro analisando transações corporativas.

## CONSULTA:
{query}

## TRANSAÇÕES A ANALISAR:
{trans_text}

## POLÍTICA DE COMPLIANCE (RESUMO):
{policy_text}

---

Analise cada transação e identifique:
1. Violações de limites de valor
2. Despesas em itens proibidos ou suspeitos
3. Possíveis fraudes ou irregularidades
4. Uso indevido de categoria
5. Padrões suspeitos (como smurfing - divisão de compras)

Para cada transação, retorne em JSON:

```json
[
  {{
    "id_transacao": "ID",
    "data": "data",
    "funcionario": "nome",
    "cargo": "cargo",
    "descricao": "descrição original",
    "valor": valor_numerico,
    "categoria": "categoria",
    "departamento": "dept",
    "violacoes": ["lista de problemas identificados ou vazio se OK"]
  }}
]
```

Se uma transação estiver OK, coloque violacoes como lista vazia [].
Retorne APENAS o JSON, sem texto adicional.
"""

    llm = get_llm()
    response = llm.invoke(prompt)
    
    return _parse_transaction_response(response.content, transactions)


def _parse_transaction_response(response_text: str, original: list[dict]) -> list[TransactionResult]:
    """
    Extrai resultados da resposta da IA.
    """
    results = []
    
    try:
        # Procurar JSON na resposta
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if json_match:
            parsed = json.loads(json_match.group())
            
            for t in parsed:
                result = TransactionResult(
                    id_transacao=t.get("id_transacao", "?"),
                    data=t.get("data", ""),
                    funcionario=t.get("funcionario", ""),
                    cargo=t.get("cargo", ""),
                    descricao=t.get("descricao", ""),
                    valor=float(t.get("valor", 0)),
                    categoria=t.get("categoria", ""),
                    departamento=t.get("departamento", ""),
                    violacoes=t.get("violacoes", [])
                )
                results.append(result)
            
            return results
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Fallback: retornar originais sem violações
    for t in original:
        result = TransactionResult(
            id_transacao=t.get("id_transacao", "?"),
            data=t.get("data", ""),
            funcionario=t.get("funcionario", ""),
            cargo=t.get("cargo", ""),
            descricao=t.get("descricao", ""),
            valor=float(t.get("valor", 0)),
            categoria=t.get("categoria", ""),
            departamento=t.get("departamento", ""),
            violacoes=[]
        )
        results.append(result)
    
    return results
