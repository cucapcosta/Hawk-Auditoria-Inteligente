"""
Fraud Detection Node
====================

Detecta fraudes usando IA para analisar emails e transações.
Sem regras hardcoded - a IA faz toda a análise.
"""

import json
import re
from app.llm import get_llm
from app.graph.state import AuditState, FraudAlert


def fraud_node(state: AuditState) -> dict:
    """
    Usa IA para detectar fraudes cruzando emails e transações.
    
    A IA analisa os dados e identifica padrões suspeitos.
    """
    query = state.get("query", "")
    email_results = state.get("email_results", [])
    transaction_results = state.get("transaction_results", [])
    policy_context = state.get("policy_context", [])
    
    try:
        # Preparar dados para análise
        data_summary = _prepare_data_for_analysis(
            email_results, 
            transaction_results, 
            policy_context
        )
        
        # Usar IA para detectar fraudes
        fraud_alerts = _detect_fraud_with_llm(query, data_summary)
        
        return {
            "fraud_alerts": fraud_alerts,
            "nodes_visited": ["fraud"]
        }
        
    except Exception as e:
        return {
            "fraud_alerts": [],
            "nodes_visited": ["fraud"],
            "error": f"Fraud detection error: {str(e)}"
        }


def _prepare_data_for_analysis(emails: list, transactions: list, policy: list) -> dict:
    """
    Prepara os dados em formato conciso para a IA analisar.
    """
    # Formatar emails
    email_text = ""
    for e in emails[:10]:
        email_text += f"- De: {e.get('de', '?')} Para: {e.get('para', '?')}\n"
        email_text += f"  Assunto: {e.get('assunto', '')}\n"
        email_text += f"  Mensagem: {e.get('mensagem', '')[:200]}\n\n"
    
    # Formatar transações
    trans_text = ""
    for t in transactions[:20]:
        trans_text += f"- ID: {t.get('id_transacao', '?')} | {t.get('funcionario', '?')} | "
        trans_text += f"${t.get('valor', 0):.2f} | {t.get('descricao', '')}\n"
    
    # Formatar política (resumo)
    policy_text = "\n".join(p[:300] for p in policy[:2]) if policy else "Não disponível"
    
    return {
        "emails": email_text if email_text else "Nenhum email encontrado",
        "transactions": trans_text if trans_text else "Nenhuma transação encontrada",
        "policy": policy_text
    }


def _detect_fraud_with_llm(query: str, data: dict) -> list[FraudAlert]:
    """
    Usa a IA para analisar os dados e detectar fraudes.
    """
    prompt = f"""Você é um auditor especializado em detecção de fraudes corporativas.

Analise os dados abaixo e identifique TODAS as possíveis fraudes ou irregularidades.

## PERGUNTA DO AUDITOR:
{query}

## EMAILS CORPORATIVOS:
{data['emails']}

## TRANSAÇÕES FINANCEIRAS:
{data['transactions']}

## POLÍTICA DE COMPLIANCE:
{data['policy']}

---

Para cada fraude ou irregularidade encontrada, responda em formato JSON:

```json
[
  {{
    "tipo": "tipo da fraude (ex: smurfing, conflito_interesse, desvio_verba, uso_pessoal, etc)",
    "severidade": "critica, alta, media ou baixa",
    "funcionario": "nome do funcionário envolvido",
    "descricao": "descrição detalhada do que foi encontrado",
    "valor_total": valor numérico envolvido,
    "evidencias": ["lista de IDs de transação ou referências a emails"],
    "regra_violada": "qual regra da política foi violada"
  }}
]
```

Se não encontrar nenhuma fraude, retorne: []

IMPORTANTE: Retorne APENAS o JSON, sem texto adicional.
"""

    llm = get_llm()
    response = llm.invoke(prompt)
    
    # Extrair JSON da resposta
    return _parse_fraud_response(response.content)


def _parse_fraud_response(response_text: str) -> list[FraudAlert]:
    """
    Extrai a lista de fraudes do JSON retornado pela IA.
    """
    # Tentar encontrar JSON na resposta
    try:
        # Procurar por bloco JSON
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if json_match:
            fraud_list = json.loads(json_match.group())
            
            # Converter para FraudAlert
            alerts = []
            for f in fraud_list:
                alert = FraudAlert(
                    tipo=f.get("tipo", "irregularidade"),
                    severidade=f.get("severidade", "media"),
                    funcionario=f.get("funcionario", "Desconhecido"),
                    descricao=f.get("descricao", ""),
                    evidencias_email=[],
                    evidencias_transacao=f.get("evidencias", []),
                    valor_total=float(f.get("valor_total", 0)),
                    regra_violada=f.get("regra_violada", "")
                )
                alerts.append(alert)
            
            return alerts
    except (json.JSONDecodeError, ValueError):
        pass
    
    return []
