# HawkAI

Sistema de Auditoria com Agentes de IA para detectar fraudes e irregularidades na Dunder Mifflin.
Já que eu que fiz, tem que ter um pássaro e periquitos não são particularmente conhecidos por serem caçadores habilidosos com boa visão.

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
                     |                       |                       |
                     +-----------------------+-----------------------+
                                             |
                                             v
                                    +------------------+
                                    |   FORMAT_OUTPUT  |
                                    |   (synth.py)     |
                                    |                  |
                                    | Padroniza texto  |
                                    | Remove markdown  |
                                    +------------------+
                                             |
                                             v
                                    +------------------+
                                    |     RESPOSTA     |
                                    +------------------+

+-----------------------------------------------------------------------------------+
|                                  DATA LAYER                                       |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  data/                                                                            |
|  +-- politica_compliance.txt    (Regras da empresa)                               |
|  +-- emails.txt                 (117 emails)                                      |
|  +-- transacoes_bancarias.csv   (2000 transações)                                 |
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
| `rag.py` | RAG para politica de compliance (FAISS, suporte GPU) |
| `synth.py` | Sintetiza respostas e formata outputs (camada final) |
| `emails_analyzer.py` | Indexa e analisa emails (FAISS + LLM, suporte GPU) |
| `auditor.py` | Cruza dados para detectar fraudes |

## Fluxos

Todas as respostas passam pelo `format_output` (synth.py) para garantir consistencia.

### 1. Compliance
```
Pergunta -> Router -> RAG (busca regras) -> Synth (LLM) -> format_output -> Resposta
```

### 2. Emails
```
Pergunta -> Router -> EmailsAnalyzer (FAISS + LLM) -> format_output -> Resposta
```

### 3. Auditoria
```
Pergunta -> Router -> Auditor:
                        +-> RAG (regras)
                        +-> EmailsAnalyzer (emails)
                        +-> CSV (transações)
                        +-> LLM (veredito)
                      -> format_output -> Resposta
```

## Stack

- **Frontend**: Streamlit (tema terminal retro)
- **LLM**: llama3.2 via Ollama
- **Embeddings**: mxbai-embed-large via Ollama (limite ~512 tokens, truncado em 1500 chars)
- **Vector DB**: FAISS (CPU ou GPU NVIDIA)
- **Linguagem**: Python 3.11+

## Instalação

Nota: Garanta que o ollama está corretamente instalado e funcionando: [Download](https://ollama.com/download)

```bash
# Clone o repositorio
git clone <repo>
cd HawkAI

# Crie o ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Instale dependencias
pip install -r requirements.txt

# (Opcional) Para GPU NVIDIA, substitua faiss-cpu por faiss-gpu:
# pip uninstall faiss-cpu && pip install faiss-gpu

# Em um terminal separado, rode o Ollama
ollama serve

# Inicie o Ollama e baixe os modelos
ollama pull llama3.2
ollama pull mxbai-embed-large

# Execute
cd src
streamlit run app.py
```

## GPU

O sistema detecta automaticamente se ha GPU NVIDIA disponivel:

```
# Com faiss-cpu (padrão):
> MODO CPU (GPU NÃO DISPONÍVEL)
> CARREGADO: 10 SEÇÕES [CPU]

# Com faiss-gpu + NVIDIA:
> GPU DETECTADA: 1 DISPOSITIVO(S)
> CARREGADO: 10 SEÇÕES [GPU]
```

Para usar GPU:
```bash
pip uninstall faiss-cpu
pip install faiss-gpu
```

## Uso

Exemplos de perguntas:

| Pergunta | Rota |
|----------|------|
| "Qual o limite de gastos sem aprovação?" | Compliance |
| "Analise os emails do Dwight" | Emails |
| "O Ryan esta cometendo fraude?" | Auditoria |
## Dados

O sistema usa dados ficticios da Dunder Mifflin (The Office):
- **Política de Compliance**: Regras de gastos, reembolsos, conflito de interesses
- **Emails**: 117 emails de abril-maio/2008
- **Transações**: 2000 transações bancárias