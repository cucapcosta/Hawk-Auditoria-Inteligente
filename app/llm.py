"""
LLM Helper - Configuração otimizada do Ollama
=============================================

Centraliza a criação do LLM com configurações de performance.
"""

from functools import lru_cache
from langchain_ollama import ChatOllama

from app.config import (
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    TEMPERATURE,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
    OLLAMA_KEEP_ALIVE,
)


def get_llm(
    num_predict: int | None = None,
    num_ctx: int | None = None,
    temperature: float | None = None
) -> ChatOllama:
    """
    Retorna uma instância do ChatOllama com configurações otimizadas.
    
    Args:
        num_predict: Máximo de tokens na resposta (None = usar default)
        num_ctx: Tamanho do contexto (None = usar default)
        temperature: Temperatura do modelo (None = usar default)
        
    Returns:
        Instância configurada do ChatOllama
    """
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=temperature if temperature is not None else TEMPERATURE,
        num_ctx=num_ctx if num_ctx is not None else OLLAMA_NUM_CTX,
        num_predict=num_predict if num_predict is not None else OLLAMA_NUM_PREDICT,
        keep_alive=OLLAMA_KEEP_ALIVE,
    )


def get_fast_llm() -> ChatOllama:
    """
    LLM otimizado para respostas rápidas (router, classificação).
    Contexto menor, resposta curta.
    """
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,  # Determinístico para classificação
        num_ctx=2048,     # Contexto pequeno
        num_predict=256,  # Resposta curta
        keep_alive=OLLAMA_KEEP_ALIVE,
    )


def get_synthesis_llm() -> ChatOllama:
    """
    LLM para síntese final - OTIMIZADO para velocidade.
    """
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=TEMPERATURE,
        num_ctx=2048,      # Reduzido para velocidade
        num_predict=512,   # Resposta moderada
        keep_alive=OLLAMA_KEEP_ALIVE,
    )


# Cache para manter modelo "quente" na memória
@lru_cache(maxsize=1)
def warmup_model() -> bool:
    """
    Faz uma chamada inicial para carregar o modelo na memória.
    Chamar no startup da aplicação.
    """
    try:
        llm = get_fast_llm()
        llm.invoke("Olá")
        return True
    except Exception:
        return False
