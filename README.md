# HawkAI

Sistema de Auditoria com Agentes de IA para detectar fraudes e irregularidades na Dunder Mifflin.

## Arquitetura

```
                                    +------------------+
                                    |     USUARIO      |
                                    |   (Streamlit)    |
                                    +--------+---------+
                                             |
                                             v
+-----------------------------------------------------------------------------------+
|                                      app.py                                       |
+-----------------------------------------------------------------------------------+
                                             |
                                             v
                                    +------------------+
                                    |     ROUTER       |
                                    |   (router.py)    |
                                    |                  |
                                    | - Classifica     |
                                    |   pergunta       |
                                    | - Extrai pessoa  |
                                    | - Extrai periodo |
                                    +--------+---------+
                                             |
                     +-----------------------+-----------------------+
                     |                       |                       |
                     v                       v                       v
            +----------------+      +----------------+      +------------------+
            |   COMPLIANCE   |      |    EMAILS      |      |    AUDITORIA     |
            |   (rag.py +    |      | (emails_       |      |   (auditor.py)   |
            |   synth.py)    |      |  analyzer.py)  |      |                  |
            +----------------+      +----------------+      +------------------+
                     |                       |                       |
                     v                       v                       v
            +----------------+      +----------------+      +------------------+
            |  FAISS Index   |      |  FAISS Index   |      |  Cruza dados:    |
            |  (politica)    |      |  (emails)      |      |  - Compliance    |
            +----------------+      +----------------+      |  - Emails        |
                     |                       |              |  - Transacoes    |
                     v                       v              +------------------+
            +----------------+      +----------------+               |
            |    LLM         |      |    LLM         |               v
            | (sintetiza     |      | (analisa       |      +------------------+
            |  resposta)     |      |  conteudo)     |      |      LLM         |
            +----------------+      +----------------+      | (gera veredito)  |
                                                            +------------------+

+-----------------------------------------------------------------------------------+
|                                  DATA LAYER                                       |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  data/                                                                            |
|  +-- politica_compliance.txt    (Regras da empresa)                               |
|  +-- emails.txt                 (117 emails)                                      |
|  +-- transacoes_bancarias.csv   (2000 transacoes)                                 |
|  +-- .cache/                                                                      |
|      +-- faiss.index            (Embeddings politica)                             |
|      +-- emails.index           (Embeddings emails)                               |
|      +-- *.json, *.hash         (Metadados cache)                                 |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

## Modulos

| Modulo | Descricao |
|--------|-----------|
| `app.py` | Interface Streamlit (tema terminal Fallout) |
| `router.py` | Classifica perguntas e extrai entidades |
| `rag.py` | RAG para politica de compliance (FAISS) |
| `synth.py` | Sintetiza respostas de compliance |
| `emails_analyzer.py` | Indexa e analisa emails (FAISS + LLM) |
| `auditor.py` | Cruza dados para detectar fraudes |

## Fluxos

### 1. Compliance
```
Pergunta -> Router -> RAG (busca regras) -> Synth (LLM) -> Resposta
```

### 2. Emails
```
Pergunta -> Router -> EmailsAnalyzer (FAISS) -> LLM (analisa) -> Resposta
```

### 3. Auditoria
```
Pergunta -> Router -> Auditor:
                        +-> RAG (regras)
                        +-> EmailsAnalyzer (emails)
                        +-> CSV (transacoes)
                        +-> LLM (veredito)
                      -> Resposta
```

## Stack

- **Frontend**: Streamlit (tema terminal retro)
- **LLM**: llama3.2 via Ollama
- **Embeddings**: mxbai-embed-large via Ollama
- **Vector DB**: FAISS
- **Linguagem**: Python 3.11+

## Instalacao

```bash
# Clone o repositorio
git clone <repo>
cd HawkAI

# Crie o ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Instale dependencias
pip install -r requirements.txt

# Inicie o Ollama e baixe os modelos
ollama pull llama3.2
ollama pull mxbai-embed-large

# Execute
cd src
streamlit run app.py
```

## Uso

Exemplos de perguntas:

| Pergunta | Rota |
|----------|------|
| "Qual o limite de gastos sem aprovacao?" | Compliance |
| "Analise os emails do Dwight" | Emails |
| "O Ryan esta cometendo fraude?" | Auditoria |
| "Veja as transacoes da Angela" | Transacoes |

## Dados

O sistema usa dados ficticios da Dunder Mifflin (The Office):
- **Politica de Compliance**: Regras de gastos, reembolsos, conflito de interesses
- **Emails**: 117 emails de abril-maio/2008
- **Transacoes**: 2000 transacoes bancarias

## Licenca

MIT
