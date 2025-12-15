"""
Router Module - Decide qual fluxo executar e extrai entidades
Usa LLM com temperatura 0 para consistencia
"""

import json
from typing import Generator
import ollama

LLM_MODEL = "llama3.2"

SYSTEM_PROMPT = """Classifique a pergunta e extraia pessoas mencionadas.

CATEGORIAS:
- compliance: Perguntas sobre REGRAS, politicas, limites. Nao menciona pessoa especifica.
- emails: Quer saber o que alguem DISSE, escreveu, conversou, conspirou.
- transacoes: Quer VER gastos/transacoes de alguem.
- auditoria: Menciona FRAUDE, investigar alguem, desvio, irregularidade.

REGRA: Se menciona "fraude" ou "investigar" + nome de pessoa = auditoria

EXEMPLOS:
"Qual o limite de gastos?" -> {"rota": "compliance", "pessoas": [], "periodo": null}
"Ryan esta cometendo fraude?" -> {"rota": "auditoria", "pessoas": ["Ryan"], "periodo": null}
"Investigue o Ryan" -> {"rota": "auditoria", "pessoas": ["Ryan"], "periodo": null}
"O que o Dwight disse?" -> {"rota": "emails", "pessoas": ["Dwight"], "periodo": null}
"Ryan e Toby estao conspirando?" -> {"rota": "emails", "pessoas": ["Ryan", "Toby"], "periodo": null}
"Transacoes da Angela" -> {"rota": "transacoes", "pessoas": ["Angela"], "periodo": null}

Responda APENAS JSON:"""


def route(question: str) -> Generator[str, None, dict]:
    """
    Determina qual rota seguir e extrai entidades.
    Yields status, returns dict com rota e entidades.
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
            "num_predict": 100,
        }
    )
    
    answer = response["message"]["content"].strip()
    
    # Tenta parsear JSON
    try:
        # Limpa resposta se tiver texto extra
        if "{" in answer:
            json_str = answer[answer.find("{"):answer.rfind("}")+1]
            result = json.loads(json_str)
        else:
            result = {"rota": "compliance", "pessoas": [], "periodo": None}
    except json.JSONDecodeError:
        # Fallback: tenta extrair rota do texto
        result = {"rota": "compliance", "pessoas": [], "periodo": None}
        for rota in ["auditoria", "emails", "transacoes", "compliance"]:
            if rota in answer.lower():
                result["rota"] = rota
                break
    
    # Normaliza rota
    valid_routes = ["compliance", "emails", "transacoes", "auditoria"]
    if result.get("rota") not in valid_routes:
        result["rota"] = "compliance"
    
    # Normaliza pessoas (garante que seja lista)
    pessoas = result.get("pessoas") or result.get("pessoa")
    if pessoas is None:
        pessoas = []
    elif isinstance(pessoas, str):
        pessoas = [pessoas]
    result["pessoas"] = pessoas
    
    # Log
    rota = result["rota"].upper()
    periodo = result.get("periodo")
    
    info_parts = [f"ROTA: {rota}"]
    if pessoas:
        info_parts.append(f"PESSOAS: {', '.join(pessoas)}")
    if periodo:
        info_parts.append(f"PERIODO: {periodo}")
    
    yield " | ".join(info_parts)
    
    return result
