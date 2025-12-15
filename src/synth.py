"""
Synthesizer Module - Usa LLM para sintetizar e formatar respostas
Centraliza toda geracao de texto para garantir consistencia
"""

from typing import Generator
import ollama

LLM_MODEL = "llama3.2"

# Prompt para compliance (RAG)
COMPLIANCE_PROMPT = """Voce e um assistente de compliance da Dunder Mifflin.
Responda APENAS com base no contexto fornecido da politica de compliance.
Se a informacao nao estiver no contexto, diga que nao encontrou na politica.
Seja direto e cite as secoes relevantes quando possivel.
NAO use markdown. Use apenas texto simples.
Responda em portugues."""

# Prompt para formatacao final de qualquer output
FORMAT_PROMPT = """Voce e um redator tecnico da Dunder Mifflin.
Sua tarefa e formatar e redigir o texto de forma clara e profissional.

REGRAS:
- NAO use markdown (sem asteriscos, sem hashtags, sem bullets com -)
- Use MAIUSCULAS para titulos e secoes
- Use quebras de linha para separar secoes
- Mantenha o conteudo original, apenas melhore a formatacao
- Seja conciso e direto
- Responda em portugues

Se o texto ja estiver bem formatado, retorne-o com minimas alteracoes."""


def synthesize(question: str, context_chunks: list[str]) -> Generator[str, None, str]:
    """
    Sintetiza uma resposta usando LLM baseado nos chunks de contexto.
    Yields status updates, returns final answer.
    """
    
    if not context_chunks:
        yield "SEM CONTEXTO PARA SINTETIZAR"
        return "Nao encontrei informacoes relevantes na politica de compliance."
    
    yield "SINTETIZANDO RESPOSTA..."
    
    context = "\n\n---\n\n".join(context_chunks)
    
    user_prompt = f"""CONTEXTO DA POLITICA:
{context}

PERGUNTA: {question}

RESPOSTA:"""

    yield "CONSULTANDO LLM..."
    
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": COMPLIANCE_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    answer = response["message"]["content"]
    
    yield "RESPOSTA PRONTA"
    return answer


def format_output(text: str, skip_if_short: bool = True) -> Generator[str, None, str]:
    """
    Formata qualquer texto de output para garantir consistencia.
    Passa o texto pela LLM para padronizar formatacao.
    
    Args:
        text: Texto a ser formatado
        skip_if_short: Se True, nao formata textos curtos (< 100 chars)
    
    Yields status updates, returns formatted text.
    """
    
    if not text:
        return ""
    
    # Textos curtos nao precisam de formatacao
    if skip_if_short and len(text) < 100:
        return text
    
    yield "FORMATANDO RESPOSTA..."
    
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": FORMAT_PROMPT},
            {"role": "user", "content": text}
        ]
    )
    
    formatted = response["message"]["content"]
    
    yield "FORMATACAO CONCLUIDA"
    return formatted
