"""
Configurações do HawkAI
=======================

Carrega variáveis de ambiente e define configurações globais.
Sistema 100% local usando Ollama.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

# Diretórios
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"

# =============================================================================
# CONFIGURAÇÃO DE LLM - OLLAMA (100% LOCAL)
# =============================================================================
# Modelo Ollama - roda localmente, sem custo, sem API key
# Alternativas: llama3.2, mistral, phi3, gemma2, qwen2.5
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Temperatura baixa para maior precisão em auditoria
TEMPERATURE = 0.1

# =============================================================================
# CONFIGURAÇÕES DE PERFORMANCE - OLLAMA
# =============================================================================
# Contexto máximo (reduzir para respostas mais rápidas)
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))

# Número máximo de tokens na resposta (limitar para mais velocidade)
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))

# Keep alive - mantém modelo na memória (evita reload entre chamadas)
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")

# Configurações do RAG
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
RETRIEVER_K = 5  # Número de documentos a recuperar

# Arquivos de dados
POLICY_FILE = DATA_DIR / "politica_compliance.txt"
EMAILS_FILE = DATA_DIR / "emails.txt"
TRANSACTIONS_FILE = DATA_DIR / "transacoes_bancarias.csv"

# Validação
def validate_config():
    """Valida se as configurações essenciais estão presentes."""
    errors = []
    
    if not POLICY_FILE.exists():
        errors.append(f"Arquivo de política não encontrado: {POLICY_FILE}")
    
    if not EMAILS_FILE.exists():
        errors.append(f"Arquivo de emails não encontrado: {EMAILS_FILE}")
    
    if not TRANSACTIONS_FILE.exists():
        errors.append(f"Arquivo de transações não encontrado: {TRANSACTIONS_FILE}")
    
    if errors:
        raise ValueError("Erros de configuração:\n" + "\n".join(f"  - {e}" for e in errors))
    
    return True


def check_ollama():
    """Verifica se o Ollama está rodando e o modelo está disponível."""
    import requests
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = [m["name"] for m in response.json().get("models", [])]
            if any(OLLAMA_MODEL in m for m in models):
                return True, f"Ollama OK - modelo {OLLAMA_MODEL} disponível"
            else:
                return False, f"Modelo {OLLAMA_MODEL} não encontrado. Execute: ollama pull {OLLAMA_MODEL}"
        return False, "Ollama não respondeu corretamente"
    except requests.exceptions.ConnectionError:
        return False, "Ollama não está rodando. Execute: ollama serve"
    except Exception as e:
        return False, f"Erro ao verificar Ollama: {e}"


# Criar diretórios se não existirem
CHROMA_DIR.mkdir(exist_ok=True)
