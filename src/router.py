"""
Router Module - Decide qual fluxo executar baseado na pergunta
Usa LLM com temperatura 0 para consistencia
"""

from typing import Generator
import ollama

LLM_MODEL = "llama3.2"

SYSTEM_PROMPT = """Classifique a pergunta em UMA categoria:

- compliance: Perguntas sobre REGRAS, politicas, limites, procedimentos, aprovacoes. PADRAO.
- emails: Pedido para ANALISAR emails ou buscar fraudes EM emails.
- transacoes: Pedido para ANALISAR transacoes bancarias/financeiras.
- auditoria: Pedido de auditoria completa, CRUZAR dados, ou analisar emails E transacoes juntos.

Responda APENAS com: compliance, emails, transacoes ou auditoria"""


def route(question: str) -> Generator[str, None, str]:
    """
    Determina qual rota seguir baseado na pergunta.
    Yields status, returns route name.
    """
    
    yield "ANALISANDO PERGUNTA..."
    
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        options={
            "temperature": 0,
            "num_predict": 20,  # Limita tokens de saida
        }
    )
    
    answer = response["message"]["content"].strip().lower()
    
    # Rotas validas
    valid_routes = ["compliance", "emails", "transacoes", "auditoria"]
    
    # Normaliza resposta
    for route_name in valid_routes:
        if route_name in answer:
            yield f"ROTA: {route_name.upper()}"
            return route_name
    
    # Default
    yield "ROTA: COMPLIANCE"
    return "compliance"
