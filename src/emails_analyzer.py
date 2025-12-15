"""
Emails Analyzer - Indexa e analisa emails para detectar fraudes
Usa FAISS para busca semantica
Suporta GPU NVIDIA quando disponivel (faiss-gpu)
"""

import os
import json
import hashlib
import re
from typing import Generator, Any

import faiss  # type: ignore
import numpy as np
import ollama

# Configuracoes
EMBEDDING_MODEL = "mxbai-embed-large"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
EMAILS_FILE = os.path.join(DATA_DIR, "emails.txt")
CACHE_DIR = os.path.join(DATA_DIR, ".cache")
INDEX_FILE = os.path.join(CACHE_DIR, "emails.index")
CHUNKS_FILE = os.path.join(CACHE_DIR, "emails.json")
HASH_FILE = os.path.join(CACHE_DIR, "emails.hash")


# Detecta GPU
def _detect_gpu() -> tuple[bool, int]:
    """Detecta se GPU esta disponivel para FAISS"""
    try:
        num_gpus = faiss.get_num_gpus()  # type: ignore
        return num_gpus > 0, num_gpus
    except AttributeError:
        # faiss-cpu nao tem get_num_gpus
        return False, 0


HAS_GPU, NUM_GPUS = _detect_gpu()


def _index_to_gpu(index: Any) -> Any:
    """Move index para GPU se disponivel"""
    if HAS_GPU:
        try:
            res = faiss.StandardGpuResources()  # type: ignore
            return faiss.index_cpu_to_gpu(res, 0, index)  # type: ignore
        except Exception:
            return index
    return index


def _index_to_cpu(index: Any) -> Any:
    """Move index para CPU (para salvar em disco)"""
    if HAS_GPU:
        try:
            return faiss.index_gpu_to_cpu(index)  # type: ignore
        except Exception:
            return index
    return index


class EmailsAnalyzer:
    """Analisador de emails com busca semantica"""
    
    def __init__(self):
        self.emails: list[dict] = []  # Lista de emails parseados
        self.index: Any = None
        self.dimension: int = 1024
        self._initialized = False
        self._using_gpu = False
    
    def _get_file_hash(self, filepath: str) -> str:
        """Calcula hash MD5 do arquivo"""
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _cache_exists(self) -> bool:
        """Verifica se o cache existe e eh valido"""
        if not all(os.path.exists(f) for f in [INDEX_FILE, CHUNKS_FILE, HASH_FILE]):
            return False
        
        with open(HASH_FILE, "r") as f:
            cached_hash = f.read().strip()
        
        current_hash = self._get_file_hash(EMAILS_FILE)
        return cached_hash == current_hash
    
    def _load_cache(self) -> bool:
        """Carrega index e emails do cache"""
        try:
            cpu_index = faiss.read_index(INDEX_FILE)
            # Tenta mover para GPU
            self.index = _index_to_gpu(cpu_index)
            self._using_gpu = HAS_GPU
            with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
                self.emails = json.load(f)
            return True
        except Exception:
            return False
    
    def _save_cache(self) -> None:
        """Salva index e emails no cache"""
        os.makedirs(CACHE_DIR, exist_ok=True)
        # Precisa converter para CPU antes de salvar
        cpu_index = _index_to_cpu(self.index)
        faiss.write_index(cpu_index, INDEX_FILE)
        with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.emails, f, ensure_ascii=False)
        with open(HASH_FILE, "w") as f:
            f.write(self._get_file_hash(EMAILS_FILE))
    
    def _get_embedding(self, text: str, max_chars: int = 1500) -> np.ndarray:
        """Gera embedding via Ollama. Trunca texto para evitar exceder contexto."""
        # mxbai-embed-large tem limite de ~512 tokens (~1500-2000 chars)
        if len(text) > max_chars:
            text = text[:max_chars]
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
        return np.array(response["embedding"], dtype=np.float32)
    
    def _parse_emails(self, content: str) -> list[dict]:
        """Parseia arquivo de emails em lista estruturada"""
        emails = []
        
        # Divide por separador
        raw_emails = content.split("-" * 79)
        
        for raw in raw_emails:
            raw = raw.strip()
            if not raw or "De:" not in raw:
                continue
            
            email = {
                "de": "",
                "para": "",
                "data": "",
                "assunto": "",
                "mensagem": "",
                "texto_completo": raw
            }
            
            lines = raw.split("\n")
            in_message = False
            message_lines = []
            
            for line in lines:
                line = line.strip()
                
                if line.startswith("De:"):
                    # Extrai nome do email
                    match = re.search(r"De:\s*([^<]+)", line)
                    if match:
                        email["de"] = match.group(1).strip()
                elif line.startswith("Para:"):
                    match = re.search(r"Para:\s*([^<]+)", line)
                    if match:
                        email["para"] = match.group(1).strip()
                elif line.startswith("Data:"):
                    email["data"] = line.replace("Data:", "").strip()
                elif line.startswith("Assunto:"):
                    email["assunto"] = line.replace("Assunto:", "").strip()
                elif line.startswith("Mensagem:"):
                    in_message = True
                elif in_message and line:
                    message_lines.append(line)
            
            email["mensagem"] = " ".join(message_lines)
            
            if email["de"] and email["mensagem"]:
                emails.append(email)
        
        return emails
    
    def initialize(self) -> Generator[str, None, None]:
        """Inicializa o analisador de emails"""
        
        # Info sobre GPU
        if HAS_GPU:
            yield f"GPU DETECTADA: {NUM_GPUS} DISPOSITIVO(S)"
        else:
            yield "MODO CPU (GPU NAO DISPONIVEL)"
        
        yield "VERIFICANDO CACHE DE EMAILS..."
        
        if self._cache_exists():
            yield "CACHE DE EMAILS ENCONTRADO"
            if self._load_cache():
                gpu_status = " [GPU]" if self._using_gpu else " [CPU]"
                yield f"CARREGADO: {len(self.emails)} EMAILS{gpu_status}"
                self._initialized = True
                return
        
        yield "INDEXANDO EMAILS..."
        
        with open(EMAILS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        self.emails = self._parse_emails(content)
        yield f"{len(self.emails)} EMAILS PARSEADOS"
        
        yield "GERANDO EMBEDDINGS DE EMAILS..."
        embeddings = []
        for i, email in enumerate(self.emails):
            # Texto para embedding: combina campos relevantes
            text = f"De: {email['de']} Para: {email['para']} Assunto: {email['assunto']} {email['mensagem']}"
            emb = self._get_embedding(text)
            embeddings.append(emb)
            if i == 0:
                self.dimension = len(emb)
            if (i + 1) % 20 == 0:
                yield f"EMBEDDING {i+1}/{len(self.emails)}"
        
        yield f"EMBEDDING {len(self.emails)}/{len(self.emails)}"
        
        embeddings_matrix = np.vstack(embeddings)
        cpu_index = faiss.IndexFlatL2(self.dimension)
        cpu_index.add(embeddings_matrix)
        
        # Tenta mover para GPU
        self.index = _index_to_gpu(cpu_index)
        self._using_gpu = HAS_GPU
        
        yield "SALVANDO CACHE DE EMAILS..."
        self._save_cache()
        
        self._initialized = True
        gpu_status = " [GPU]" if self._using_gpu else " [CPU]"
        yield f"EMAILS INDEXADOS{gpu_status}"
    
    def search(self, query: str, pessoa: str | None = None, k: int = 10) -> Generator[str, None, list[dict]]:
        """Busca emails relevantes"""
        
        if not self._initialized:
            yield "ERRO: EMAILS NAO INDEXADOS"
            return []
        
        yield f"BUSCANDO EMAILS..."
        
        # Se tiver pessoa, filtra primeiro
        if pessoa:
            yield f"FILTRANDO POR: {pessoa}"
            pessoa_lower = pessoa.lower()
            filtered_indices = []
            for i, email in enumerate(self.emails):
                if (pessoa_lower in email["de"].lower() or 
                    pessoa_lower in email["para"].lower() or
                    pessoa_lower in email["mensagem"].lower()):
                    filtered_indices.append(i)
            
            if not filtered_indices:
                yield f"NENHUM EMAIL ENCONTRADO PARA {pessoa}"
                return []
            
            yield f"{len(filtered_indices)} EMAILS DE/PARA {pessoa}"
            
            # Retorna todos os emails da pessoa (sem busca semantica)
            results = [self.emails[i] for i in filtered_indices[:k]]
        else:
            # Busca semantica
            query_emb = self._get_embedding(query)
            query_emb = query_emb.reshape(1, -1)
            
            distances, indices = self.index.search(query_emb, k)
            
            results = []
            for idx in indices[0]:
                if idx < len(self.emails):
                    results.append(self.emails[idx])
        
        yield f"{len(results)} EMAILS ENCONTRADOS"
        return results


    def analyze(self, query: str, pessoas: list[str] | None = None) -> Generator[str, None, str]:
        """
        Analisa emails buscando conteudo especifico.
        Usa LLM para sintetizar os achados.
        Aceita lista de pessoas para filtrar.
        """
        
        yield "BUSCANDO EMAILS RELEVANTES..."
        
        # Busca emails de todas as pessoas mencionadas
        emails = []
        if pessoas:
            for pessoa in pessoas:
                search_gen = self.search(query, pessoa=pessoa, k=10)
                try:
                    while True:
                        status = next(search_gen)
                        yield status
                except StopIteration as e:
                    found = e.value or []
                    # Evita duplicatas
                    for email in found:
                        if email not in emails:
                            emails.append(email)
        else:
            # Busca semantica sem filtro de pessoa
            search_gen = self.search(query, k=15)
            try:
                while True:
                    status = next(search_gen)
                    yield status
            except StopIteration as e:
                emails = e.value or []
        
        if not emails:
            yield "NENHUM EMAIL ENCONTRADO"
            return "Nao encontrei emails relevantes para sua busca."
        
        yield "ANALISANDO CONTEUDO..."
        
        # Formata emails para contexto
        emails_text = []
        for e in emails[:10]:
            emails_text.append(f"De: {e['de']}")
            emails_text.append(f"Para: {e['para']}")
            emails_text.append(f"Data: {e['data']}")
            emails_text.append(f"Assunto: {e['assunto']}")
            emails_text.append(f"Mensagem: {e['mensagem']}")
            emails_text.append("---")
        
        context = "\n".join(emails_text)
        
        system_prompt = """Voce e um analista de emails corporativos.
Analise os emails fornecidos e responda a pergunta do usuario.
Seja especifico: cite remetentes, datas e trechos relevantes.
NAO use markdown. Texto simples apenas."""

        user_prompt = f"""EMAILS:
{context}

PERGUNTA: {query}

ANALISE:"""

        yield "CONSULTANDO LLM..."
        
        response = ollama.chat(
            model="llama3.2",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        answer = response["message"]["content"]
        
        yield "ANALISE CONCLUIDA"
        return answer


# Singleton
_analyzer_instance: EmailsAnalyzer | None = None


def get_emails_analyzer() -> EmailsAnalyzer:
    """Retorna instancia singleton"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = EmailsAnalyzer()
    return _analyzer_instance
