"""
Synthesizer Node
================

Gera a resposta final usando IA para análise inteligente.
A IA interpreta os dados e gera uma resposta contextualizada.
"""

from app.llm import get_synthesis_llm
from app.graph.state import AuditState


def synthesizer_node(state: AuditState) -> dict:
    """
    Gera resposta final usando LLM para análise inteligente.
    
    A IA recebe os dados coletados e gera uma resposta interpretativa.
    """
    try:
        query = state["query"]
        query_type = state.get("query_type", "general")
        
        # Preparar contexto compacto para a IA
        context = _prepare_context(state)
        
        # Construir prompt para a IA analisar
        prompt = _build_analysis_prompt(query, query_type, context)
        
        # Usar LLM para análise
        llm = get_synthesis_llm()
        response = llm.invoke(prompt)
        
        return {
            "final_response": response.content,
            "evidence_summary": _generate_evidence_summary(state),
            "nodes_visited": ["synthesizer"]
        }
        
    except Exception as e:
        return _fallback_response(state, str(e))


def _prepare_context(state: AuditState) -> dict:
    """
    Prepara um contexto compacto com os dados coletados.
    Limita o tamanho para não sobrecarregar o LLM.
    """
    # Alertas de fraude (máximo 5, mais relevantes)
    fraud_alerts = state.get("fraud_alerts", [])
    fraud_summary = []
    for a in fraud_alerts[:5]:
        fraud_summary.append(
            f"- {a.get('tipo', '?')}: {a.get('funcionario', '?')} - "
            f"${a.get('valor_total', 0):.2f} - {a.get('descricao', '')[:100]}"
        )
    
    # Transações com violações (máximo 5)
    transactions = state.get("transaction_results", [])
    trans_with_violations = [t for t in transactions if t.get("violacoes")]
    trans_summary = []
    for t in trans_with_violations[:5]:
        trans_summary.append(
            f"- {t.get('id_transacao')}: {t.get('funcionario')} - ${t.get('valor', 0):.2f} - "
            f"{t.get('descricao', '')[:50]} [Violação: {t.get('violacoes', [''])[0][:50]}]"
        )
    
    # Emails (máximo 3)
    emails = state.get("email_results", [])
    email_summary = []
    for e in emails[:3]:
        email_summary.append(
            f"- De: {e.get('de', '?')} Para: {e.get('para', '?')} - "
            f"Assunto: {e.get('assunto', '')} - {e.get('mensagem', '')[:80]}..."
        )
    
    # Política (máximo 2 trechos curtos)
    policy = state.get("policy_context", [])
    policy_summary = []
    for p in policy[:2]:
        policy_summary.append(p[:250] + "...")
    
    return {
        "fraud_alerts": "\n".join(fraud_summary) if fraud_summary else "Nenhum alerta",
        "transactions": "\n".join(trans_summary) if trans_summary else "Nenhuma violação",
        "emails": "\n".join(email_summary) if email_summary else "Nenhum email relevante",
        "policy": "\n".join(policy_summary) if policy_summary else "Sem contexto de política",
        "stats": {
            "total_fraud": len(fraud_alerts),
            "total_transactions": len(transactions),
            "transactions_with_violations": len(trans_with_violations),
            "total_emails": len(emails)
        }
    }


def _build_analysis_prompt(query: str, query_type: str, context: dict) -> str:
    """
    Constrói o prompt para a IA analisar os dados.
    """
    stats = context["stats"]
    
    prompt = f"""Você é um auditor da Dunder Mifflin. Analise os dados e responda à pergunta.

PERGUNTA: {query}

DADOS COLETADOS:

## Alertas de Fraude ({stats['total_fraud']} encontrados):
{context['fraud_alerts']}

## Transações ({stats['transactions_with_violations']} com violações de {stats['total_transactions']} total):
{context['transactions']}

## Emails Relevantes ({stats['total_emails']} encontrados):
{context['emails']}

## Política de Compliance:
{context['policy']}

---
INSTRUÇÕES:
- Responda em português de forma clara e direta
- Foque na pergunta específica do usuário
- Cite evidências concretas (IDs, valores, nomes)
- Se perguntaram sobre uma pessoa específica, foque nela
- Se perguntaram sobre um tipo de fraude (ex: smurfing), foque nisso
- Dê uma conclusão objetiva
"""
    return prompt





def _generate_evidence_summary(state: AuditState) -> str:
    """
    Gera um resumo das evidências utilizadas.
    """
    parts = []
    
    # Nós visitados
    nodes = state.get("nodes_visited", [])
    parts.append(f"**Fontes consultadas:** {', '.join(nodes)}")
    
    # Estatísticas
    stats = []
    
    policy_ctx = state.get("policy_context", [])
    if policy_ctx:
        stats.append(f"{len(policy_ctx)} seções da política")
    
    emails = state.get("email_results", [])
    if emails:
        stats.append(f"{len(emails)} emails")
    
    transactions = state.get("transaction_results", [])
    if transactions:
        stats.append(f"{len(transactions)} transações")
    
    frauds = state.get("fraud_alerts", [])
    if frauds:
        stats.append(f"{len(frauds)} alertas de fraude")
    
    if stats:
        parts.append(f"**Evidências coletadas:** {', '.join(stats)}")
    
    # Erros (se houver)
    error = state.get("error")
    if error:
        parts.append(f"**Aviso:** {error}")
    
    return "\n".join(parts)


def _fallback_response(state: AuditState, error_msg: str) -> dict:
    """
    Gera resposta fallback quando o LLM falha.
    """
    query = state["query"]
    
    # Montar resposta básica
    response_parts = [
        f"## Resultado da Análise\n",
        f"**Consulta:** {query}\n",
    ]
    
    # Adicionar informações disponíveis
    fraud_alerts = state.get("fraud_alerts", [])
    if fraud_alerts:
        response_parts.append(f"\n### Alertas de Fraude ({len(fraud_alerts)})\n")
        for alert in fraud_alerts[:5]:
            response_parts.append(
                f"- **{alert.get('tipo', 'N/A')}** - {alert.get('funcionario', 'N/A')}: "
                f"{alert.get('descricao', 'N/A')} (${alert.get('valor_total', 0):.2f})\n"
            )
    
    transaction_results = state.get("transaction_results", [])
    with_violations = [t for t in transaction_results if t.get("violacoes")]
    if with_violations:
        response_parts.append(f"\n### Transações com Violações ({len(with_violations)})\n")
        for t in with_violations[:5]:
            response_parts.append(
                f"- **{t.get('id_transacao')}** - {t.get('funcionario')}: "
                f"${t.get('valor', 0):.2f} - {t.get('descricao')}\n"
            )
    
    response_parts.append(f"\n---\n*Nota: Resposta gerada em modo fallback devido a: {error_msg}*")
    
    return {
        "final_response": "".join(response_parts),
        "evidence_summary": _generate_evidence_summary(state),
        "nodes_visited": ["synthesizer"],
        "error": f"Synthesizer fallback: {error_msg}"
    }
