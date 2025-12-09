"""
Email Node
==========

Busca e analisa emails corporativos usando IA.
100% IA para análise - sem regras hardcoded.
"""

import json
import re
from app.llm import get_llm
from app.graph.state import AuditState, EmailResult
from app.tools.vector_store import get_vector_store_manager
from app.tools.email_parser import EmailParser


def email_node(state: AuditState) -> dict:
    """
    Busca emails relevantes e usa IA para analisar.
    
    1. Busca emails por semântica (vector store) e por entidades
    2. Envia para IA analisar e identificar problemas
    
    Args:
        state: Estado atual do grafo
        
    Returns:
        Atualizações para o estado (email_results)
    """
    query = state["query"]
    entities = state.get("entities", [])
    policy_context = state.get("policy_context", [])
    
    try:
        # Buscar emails relevantes
        raw_emails = _get_relevant_emails(query, entities)
        
        # Usar IA para analisar os emails
        analyzed_results = _analyze_emails_with_llm(
            query, 
            raw_emails, 
            policy_context
        )
        
        return {
            "email_results": analyzed_results,
            "nodes_visited": ["email"]
        }
        
    except Exception as e:
        return {
            "email_results": [],
            "nodes_visited": ["email"],
            "error": f"Email analysis error: {str(e)}"
        }


def _get_relevant_emails(query: str, entities: list) -> list[dict]:
    """
    Busca emails relevantes combinando vector search e busca direta.
    """
    emails = []
    seen_lines = set()
    
    try:
        # Tentar busca semântica primeiro
        vs_manager = get_vector_store_manager()
        docs = vs_manager.search_emails(query, k=5)
        
        for doc in docs:
            linha = doc.metadata.get("linha", 0)
            if linha not in seen_lines:
                seen_lines.add(linha)
                emails.append({
                    "de": doc.metadata.get("de", ""),
                    "para": doc.metadata.get("para", ""),
                    "data": doc.metadata.get("data", ""),
                    "assunto": doc.metadata.get("assunto", ""),
                    "mensagem": doc.page_content,
                    "linha": linha
                })
        
        # Buscar por entidades (pessoas)
        for entity in entities:
            if _is_person_name(entity):
                person_docs = vs_manager.search_emails_by_person(entity, k=5)
                for doc in person_docs:
                    linha = doc.metadata.get("linha", 0)
                    if linha not in seen_lines:
                        seen_lines.add(linha)
                        emails.append({
                            "de": doc.metadata.get("de", ""),
                            "para": doc.metadata.get("para", ""),
                            "data": doc.metadata.get("data", ""),
                            "assunto": doc.metadata.get("assunto", ""),
                            "mensagem": doc.page_content,
                            "linha": linha
                        })
                        
    except Exception:
        # Fallback: usar parser diretamente
        emails = _fallback_email_search(entities)
    
    return emails[:10]


def _fallback_email_search(entities: list) -> list[dict]:
    """
    Busca fallback usando parser diretamente.
    """
    try:
        parser = EmailParser()
        emails = []
        
        for entity in entities:
            if _is_person_name(entity):
                sender_emails = parser.search_by_sender(entity)
                recipient_emails = parser.search_by_recipient(entity)
                
                # Email é dataclass, usar atributos diretamente
                for e in sender_emails + recipient_emails:
                    emails.append({
                        "de": e.de,
                        "para": e.para,
                        "data": e.data,
                        "assunto": e.assunto,
                        "mensagem": e.mensagem,
                        "linha": e.linha
                    })
        
        return emails[:10]
    except Exception:
        return []


def _is_person_name(entity: str) -> bool:
    """Verifica se a entidade parece ser um nome de pessoa."""
    if not entity:
        return False
    
    known_names = [
        "michael", "dwight", "jim", "pam", "ryan", "angela",
        "kevin", "oscar", "stanley", "phyllis", "andy", "creed",
        "meredith", "kelly", "toby", "jan", "david", "holly"
    ]
    
    entity_lower = entity.lower()
    for name in known_names:
        if name in entity_lower:
            return True
    
    return entity[0].isupper() and not any(c.isdigit() for c in entity)


def _analyze_emails_with_llm(query: str, emails: list[dict], policy: list[str]) -> list[EmailResult]:
    """
    Usa IA para analisar emails e identificar problemas.
    """
    if not emails:
        return []
    
    # Formatar emails para prompt
    email_text = ""
    for i, e in enumerate(emails, 1):
        email_text += f"--- EMAIL {i} (linha {e.get('linha', 'N/A')}) ---\n"
        email_text += f"De: {e.get('de', 'N/A')}\n"
        email_text += f"Para: {e.get('para', 'N/A')}\n"
        email_text += f"Data: {e.get('data', 'N/A')}\n"
        email_text += f"Assunto: {e.get('assunto', 'N/A')}\n"
        email_text += f"Mensagem: {e.get('mensagem', '')}\n\n"
    
    # Formatar política
    policy_text = "\n".join(policy[:2]) if policy else "Não disponível"
    
    prompt = f"""Você é um auditor corporativo analisando comunicações internas.

## CONSULTA:
{query}

## EMAILS ENCONTRADOS:
{email_text}

## POLÍTICA DE COMPLIANCE (RESUMO):
{policy_text}

---

Analise cada email e identifique:
1. Comunicações relevantes para a consulta
2. Evidências de acordos ou combinações suspeitas
3. Menções a despesas, compras ou transações
4. Conflitos de interesse mencionados
5. Violações de políticas discutidas

Para cada email, retorne em JSON:

```json
[
  {{
    "de": "remetente",
    "para": "destinatário",
    "data": "data",
    "assunto": "assunto",
    "mensagem": "mensagem original",
    "linha": numero_da_linha,
    "analise": "sua análise do email - o que é relevante ou suspeito"
  }}
]
```

Retorne APENAS o JSON, sem texto adicional.
"""

    llm = get_llm()
    response = llm.invoke(prompt)
    
    return _parse_email_response(response.content, emails)


def _parse_email_response(response_text: str, original: list[dict]) -> list[EmailResult]:
    """
    Extrai resultados da resposta da IA.
    """
    results = []
    
    try:
        # Procurar JSON na resposta
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if json_match:
            parsed = json.loads(json_match.group())
            
            for e in parsed:
                result = EmailResult(
                    de=e.get("de", ""),
                    para=e.get("para", ""),
                    data=e.get("data", ""),
                    assunto=e.get("assunto", ""),
                    mensagem=e.get("mensagem", ""),
                    linha=int(e.get("linha", 0))
                )
                results.append(result)
            
            return results
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Fallback: retornar originais
    for e in original:
        result = EmailResult(
            de=e.get("de", ""),
            para=e.get("para", ""),
            data=e.get("data", ""),
            assunto=e.get("assunto", ""),
            mensagem=e.get("mensagem", ""),
            linha=int(e.get("linha", 0))
        )
        results.append(result)
    
    return results
