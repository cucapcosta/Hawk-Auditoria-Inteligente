"""
Router Module - Decide qual fluxo executar e extrai entidades
Usa LLM com temperatura 0 para consistencia
"""

import json
from typing import Generator
import ollama

LLM_MODEL = "llama3.2"

SYSTEM_PROMPT = """Classifique a pergunta em uma categoria e extraia entidades.

CATEGORIAS:
- compliance: Perguntas sobre REGRAS da empresa, politicas, limites de gastos, o que pode/nao pode.
- emails: Quando pedir para VER ou ANALISAR emails de alguem.
- transacoes: Quando pedir para VER ou ANALISAR transacoes/gastos de alguem.
- auditoria: Quando mencionar FRAUDE, INVESTIGAR, SUSPEITO, IRREGULARIDADE, ou pedir analise completa de alguem.

EXTRAIA entidades mencionadas:
- pessoa: Nome proprio mencionado (Ryan, Michael, Dwight, etc)
- periodo: Data ou mes mencionado

EXEMPLOS:
"Qual o limite de gastos?" -> {"rota": "compliance", "pessoa": null, "periodo": null}
"O Ryan esta cometendo fraude?" -> {"rota": "auditoria", "pessoa": "Ryan", "periodo": null}
"Analise os emails do Dwight" -> {"rota": "emails", "pessoa": "Dwight", "periodo": null}
"Investigue Michael Scott" -> {"rota": "auditoria", "pessoa": "Michael Scott", "periodo": null}

Responda APENAS o JSON:"""


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
            result = {"rota": "compliance", "pessoa": None, "periodo": None}
    except json.JSONDecodeError:
        # Fallback: tenta extrair rota do texto
        result = {"rota": "compliance", "pessoa": None, "periodo": None}
        for rota in ["auditoria", "emails", "transacoes", "compliance"]:
            if rota in answer.lower():
                result["rota"] = rota
                break
    
    # Normaliza rota
    valid_routes = ["compliance", "emails", "transacoes", "auditoria"]
    if result.get("rota") not in valid_routes:
        result["rota"] = "compliance"
    
    # Log
    rota = result["rota"].upper()
    pessoa = result.get("pessoa")
    periodo = result.get("periodo")
    
    info_parts = [f"ROTA: {rota}"]
    if pessoa:
        info_parts.append(f"PESSOA: {pessoa}")
    if periodo:
        info_parts.append(f"PERIODO: {periodo}")
    
    yield " | ".join(info_parts)
    
    return result
