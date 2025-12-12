"""
Auditor Module - Cruza dados de emails e transacoes para detectar fraudes
Usa compliance como base para regras
"""

import os
import csv
from typing import Generator
import ollama

from rag import get_rag
from emails_analyzer import get_emails_analyzer

LLM_MODEL = "llama3.2"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "transacoes_bancarias.csv")


def load_transactions(pessoa: str | None = None, periodo: str | None = None) -> list[dict]:
    """Carrega transacoes do CSV, opcionalmente filtrando"""
    transactions = []
    
    with open(TRANSACTIONS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filtra por pessoa se especificado
            if pessoa:
                pessoa_lower = pessoa.lower()
                func_lower = row.get("funcionario", "").lower()
                if pessoa_lower not in func_lower:
                    continue
            
            # Filtra por periodo se especificado
            if periodo:
                data = row.get("data", "")
                if periodo not in data:
                    continue
            
            transactions.append(row)
    
    return transactions


def format_transactions(transactions: list[dict], limit: int = 20) -> str:
    """Formata transacoes para contexto da LLM"""
    if not transactions:
        return "Nenhuma transacao encontrada."
    
    lines = []
    total = 0.0
    
    for t in transactions[:limit]:
        valor = float(t.get("valor", 0))
        total += valor
        # Formato sem separador de milhar para clareza
        valor_str = f"{valor:.2f}".replace(",", "")
        lines.append(
            f"- {t['data']} | {t['funcionario']} | {t['descricao']} | ${valor_str} | {t['categoria']}"
        )
    
    if len(transactions) > limit:
        lines.append(f"... e mais {len(transactions) - limit} transacoes")
    
    total_str = f"{total:.2f}".replace(",", "")
    lines.append(f"\nTOTAL: ${total_str} em {len(transactions)} transacoes")
    
    return "\n".join(lines)


def format_emails(emails: list[dict], limit: int = 10) -> str:
    """Formata emails para contexto da LLM"""
    if not emails:
        return "Nenhum email encontrado."
    
    lines = []
    
    for e in emails[:limit]:
        lines.append(f"--- EMAIL ---")
        lines.append(f"De: {e['de']}")
        lines.append(f"Para: {e['para']}")
        lines.append(f"Data: {e['data']}")
        lines.append(f"Assunto: {e['assunto']}")
        lines.append(f"Mensagem: {e['mensagem'][:300]}...")
        lines.append("")
    
    if len(emails) > limit:
        lines.append(f"... e mais {len(emails) - limit} emails")
    
    return "\n".join(lines)


def audit(question: str, pessoa: str | None = None, periodo: str | None = None) -> Generator[str, None, str]:
    """
    Executa auditoria completa:
    1. Busca regras de compliance
    2. Busca emails relevantes
    3. Carrega transacoes
    4. Cruza dados e da veredito
    """
    
    yield "=" * 40
    yield "INICIANDO AUDITORIA"
    yield "=" * 40
    
    context_parts = []
    
    # 1. Busca regras de compliance
    yield "CONSULTANDO POLITICA DE COMPLIANCE..."
    
    rag = get_rag()
    if not rag._initialized:
        for status in rag.initialize():
            yield status
    
    compliance_query = question
    if pessoa:
        compliance_query = f"Regras sobre gastos, reembolsos e fraudes"
    
    compliance_chunks = []
    search_gen = rag.search(compliance_query, k=3)
    try:
        while True:
            status = next(search_gen)
            yield status
    except StopIteration as e:
        compliance_chunks = e.value or []
    
    if compliance_chunks:
        context_parts.append("=== REGRAS DE COMPLIANCE ===")
        context_parts.append("\n---\n".join(compliance_chunks[:2]))
    
    # 2. Busca emails
    yield "-" * 40
    yield "ANALISANDO EMAILS..."
    
    emails_analyzer = get_emails_analyzer()
    if not emails_analyzer._initialized:
        for status in emails_analyzer.initialize():
            yield status
    
    emails = []
    email_query = question if not pessoa else pessoa
    search_gen = emails_analyzer.search(email_query, pessoa=pessoa, k=15)
    try:
        while True:
            status = next(search_gen)
            yield status
    except StopIteration as e:
        emails = e.value or []
    
    if emails:
        context_parts.append("\n=== EMAILS ENCONTRADOS ===")
        context_parts.append(format_emails(emails, limit=10))
    
    # 3. Carrega transacoes
    yield "-" * 40
    yield "ANALISANDO TRANSACOES..."
    
    transactions = load_transactions(pessoa=pessoa, periodo=periodo)
    yield f"{len(transactions)} TRANSACOES ENCONTRADAS"
    
    if transactions:
        context_parts.append("\n=== TRANSACOES ===")
        context_parts.append(format_transactions(transactions, limit=25))
    
    # 4. Sintetiza veredito
    yield "-" * 40
    yield "CRUZANDO DADOS..."
    yield "GERANDO VEREDITO..."
    
    context = "\n\n".join(context_parts)
    
    system_prompt = """Voce e um auditor forense da Dunder Mifflin.

REGRAS DE COMPLIANCE:

SECAO 3.3 - CONFLITO DE INTERESSES:
- PROIBIDO usar dinheiro da empresa para projetos PESSOAIS
- PROIBIDO financiar startups ou redes sociais do funcionario
- Exemplo: WUPHF.com e projeto pessoal do Ryan, nao da empresa

SECAO 1 - LIMITES DE APROVACAO:
- Ate $50: funcionario tem autonomia
- $50 a $500: precisa aprovacao do Gerente Regional  
- Acima de $500: precisa Purchase Order assinado pelo CFO

COMO ANALISAR:
1. Leia os EMAILS para descobrir o PROPOSITO REAL das despesas
2. Se o dinheiro foi para projeto PESSOAL = CONFLITO DE INTERESSES
3. Se gastou acima de $500 sem PO do CFO = IRREGULARIDADE
4. Use APENAS dados fornecidos, nao invente

NAO use markdown. Texto simples.

FORMATO:

EMAILS SUSPEITOS
[quem enviou, data, o que revela sobre fraude]

TRANSACOES IRREGULARES
[data, valor, descricao, qual regra viola]

VIOLACAO PRINCIPAL
[secao 3.3 ou secao 1, explicar]

VEREDITO
[FRAUDE DETECTADA ou SEM EVIDENCIAS]"""

    pessoa_context = f" sobre {pessoa}" if pessoa else ""
    user_prompt = f"""PERGUNTA DO INVESTIGADOR: {question}

DADOS COLETADOS{pessoa_context}:

{context}

ANALISE:"""

    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    answer = response["message"]["content"]
    
    yield "AUDITORIA CONCLUIDA"
    yield "=" * 40
    
    return answer
