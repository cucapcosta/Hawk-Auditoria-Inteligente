"""
Synthesizer Module - Usa LLM para sintetizar respostas
"""

from typing import Generator
import ollama

LLM_MODEL = "llama3.2"

SYSTEM_PROMPT = """Voce e um assistente de compliance da Dunder Mifflin.
Responda APENAS com base no contexto fornecido da politica de compliance.
Se a informacao nao estiver no contexto, diga que nao encontrou na politica.
Seja direto e cite as secoes relevantes quando possivel.
NAO use markdown. Use apenas texto simples.
Responda em portugues."""


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
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    answer = response["message"]["content"]
    
    yield "RESPOSTA PRONTA"
    return answer
