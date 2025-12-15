"""
RAG Module - Retrieval Augmented Generation com FAISS
Apenas busca e retorna chunks relevantes (sem LLM)
Suporta GPU NVIDIA quando disponivel (faiss-gpu)
"""

import os
import json
import hashlib
from typing import Generator, Any

import faiss  # type: ignore
import numpy as np
import ollama

# Configuracoes
EMBEDDING_MODEL = "mxbai-embed-large"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
POLICY_FILE = os.path.join(DATA_DIR, "politica_compliance.txt")
CACHE_DIR = os.path.join(DATA_DIR, ".cache")
INDEX_FILE = os.path.join(CACHE_DIR, "faiss.index")
CHUNKS_FILE = os.path.join(CACHE_DIR, "chunks.json")
HASH_FILE = os.path.join(CACHE_DIR, "policy.hash")


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


class ComplianceRAG:
    """RAG para busca na politica de compliance"""
    
    def __init__(self):
        self.chunks: list[str] = []
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
        
        current_hash = self._get_file_hash(POLICY_FILE)
        return cached_hash == current_hash
    
    def _load_cache(self) -> bool:
        """Carrega index e chunks do cache"""
        try:
            cpu_index = faiss.read_index(INDEX_FILE)
            # Tenta mover para GPU
            self.index = _index_to_gpu(cpu_index)
            self._using_gpu = HAS_GPU
            with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
            return True
        except Exception:
            return False
    
    def _save_cache(self) -> None:
        """Salva index e chunks no cache"""
        os.makedirs(CACHE_DIR, exist_ok=True)
        # Precisa converter para CPU antes de salvar
        cpu_index = _index_to_cpu(self.index)
        faiss.write_index(cpu_index, INDEX_FILE)
        with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False)
        with open(HASH_FILE, "w") as f:
            f.write(self._get_file_hash(POLICY_FILE))
    
    def _get_embedding(self, text: str, max_chars: int = 2000) -> np.ndarray:
        """Gera embedding via Ollama. Trunca texto para evitar exceder contexto."""
        # mxbai-embed-large tem limite de ~512 tokens
        if len(text) > max_chars:
            text = text[:max_chars]
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
        return np.array(response["embedding"], dtype=np.float32)
    
    def _chunk_policy(self, text: str) -> list[str]:
        """Divide a politica em chunks por secao"""
        chunks = []
        current_chunk = []
        
        for line in text.split("\n"):
            if line.startswith("=" * 10):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk).strip()
                    if chunk_text and len(chunk_text) > 50:
                        chunks.append(chunk_text)
                    current_chunk = []
            else:
                current_chunk.append(line)
        
        if current_chunk:
            chunk_text = "\n".join(current_chunk).strip()
            if chunk_text and len(chunk_text) > 50:
                chunks.append(chunk_text)
        
        return chunks
    
    def initialize(self) -> Generator[str, None, None]:
        """Inicializa o RAG"""
        
        # Info sobre GPU
        if HAS_GPU:
            yield f"GPU DETECTADA: {NUM_GPUS} DISPOSITIVO(S)"
        else:
            yield "MODO CPU (GPU NAO DISPONIVEL)"
        
        yield "VERIFICANDO CACHE..."
        
        if self._cache_exists():
            yield "CACHE ENCONTRADO"
            if self._load_cache():
                gpu_status = " [GPU]" if self._using_gpu else " [CPU]"
                yield f"CARREGADO: {len(self.chunks)} SECOES{gpu_status}"
                self._initialized = True
                return
        
        yield "GERANDO EMBEDDINGS..."
        
        with open(POLICY_FILE, "r", encoding="utf-8") as f:
            policy_text = f.read()
        
        self.chunks = self._chunk_policy(policy_text)
        yield f"{len(self.chunks)} SECOES IDENTIFICADAS"
        
        embeddings = []
        for i, chunk in enumerate(self.chunks):
            emb = self._get_embedding(chunk)
            embeddings.append(emb)
            if i == 0:
                self.dimension = len(emb)
            yield f"EMBEDDING {i+1}/{len(self.chunks)}"
        
        embeddings_matrix = np.vstack(embeddings)
        cpu_index = faiss.IndexFlatL2(self.dimension)
        cpu_index.add(embeddings_matrix)
        
        # Tenta mover para GPU
        self.index = _index_to_gpu(cpu_index)
        self._using_gpu = HAS_GPU
        
        yield "SALVANDO CACHE..."
        self._save_cache()
        
        self._initialized = True
        gpu_status = " [GPU]" if self._using_gpu else " [CPU]"
        yield f"RAG PRONTO{gpu_status}"
    
    def search(self, query: str, k: int = 3) -> Generator[str, None, list[str]]:
        """Busca chunks relevantes"""
        
        if not self._initialized:
            yield "ERRO: RAG NAO INICIALIZADO"
            return []
        
        yield "BUSCANDO CONTEXTO..."
        
        query_emb = self._get_embedding(query)
        query_emb = query_emb.reshape(1, -1)
        
        distances, indices = self.index.search(query_emb, k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.chunks):
                results.append(self.chunks[idx])
        
        yield f"{len(results)} SECOES ENCONTRADAS"
        return results


# Singleton
_rag_instance: ComplianceRAG | None = None


def get_rag() -> ComplianceRAG:
    """Retorna instancia singleton do RAG"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = ComplianceRAG()
    return _rag_instance
