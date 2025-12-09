"""
Vector Store Manager
====================

Gerencia o ChromaDB para armazenamento e busca de embeddings.
Usa embeddings padrão do Chroma (onnx runtime, leve e local).
"""

from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings

from app.config import (
    CHROMA_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    RETRIEVER_K,
    POLICY_FILE,
    EMAILS_FILE
)


class DocumentResult:
    """Resultado de busca simplificado."""
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata


class VectorStoreManager:
    """
    Gerencia vector stores para política e emails.
    
    Usa ChromaDB nativo com embeddings padrão (all-MiniLM-L6-v2 via onnx).
    Não requer API externa nem PyTorch.
    """
    
    def __init__(self):
        # Cliente ChromaDB persistente
        self._client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self._policy_collection = None
        self._email_collection = None
    
    @property
    def policy_collection(self):
        """Lazy loading da coleção de política."""
        if self._policy_collection is None:
            self._policy_collection = self._load_or_create_policy_collection()
        return self._policy_collection
    
    @property
    def email_collection(self):
        """Lazy loading da coleção de emails."""
        if self._email_collection is None:
            self._email_collection = self._load_or_create_email_collection()
        return self._email_collection
    
    def _load_or_create_policy_collection(self):
        """Carrega ou cria a coleção de política."""
        collection = self._client.get_or_create_collection(
            name="policy",
            metadata={"description": "Política de compliance da Dunder Mifflin"}
        )
        
        # Se vazia, popular com dados
        if collection.count() == 0:
            self._populate_policy_collection(collection)
        
        return collection
    
    def _populate_policy_collection(self, collection):
        """Popula a coleção com dados da política."""
        with open(POLICY_FILE, "r", encoding="utf-8") as f:
            policy_text = f.read()
        
        # Dividir em seções usando os separadores visuais
        sections = policy_text.split("=" * 78)
        
        documents = []
        metadatas = []
        ids = []
        
        for i, section in enumerate(sections):
            section = section.strip()
            if section and len(section) > 50:  # Ignorar seções muito pequenas
                lines = section.split("\n")
                title = lines[0].strip() if lines else f"Seção {i}"
                
                # Dividir seções grandes em chunks
                chunks = self._split_text(section, CHUNK_SIZE, CHUNK_OVERLAP)
                
                for j, chunk in enumerate(chunks):
                    documents.append(chunk)
                    metadatas.append({
                        "source": "politica_compliance.txt",
                        "section_index": i,
                        "chunk_index": j,
                        "section_title": title[:100]
                    })
                    ids.append(f"policy_{i}_{j}")
        
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
    
    def _load_or_create_email_collection(self):
        """Carrega ou cria a coleção de emails."""
        collection = self._client.get_or_create_collection(
            name="emails",
            metadata={"description": "Emails corporativos"}
        )
        
        if collection.count() == 0:
            self._populate_email_collection(collection)
        
        return collection
    
    def _populate_email_collection(self, collection):
        """Popula a coleção com dados de emails."""
        from app.tools.email_parser import EmailParser
        
        parser = EmailParser()
        emails = parser.parse_all()
        
        documents = []
        metadatas = []
        ids = []
        
        for i, email in enumerate(emails):
            content = f"""De: {email['de']}
Para: {email['para']}
Data: {email['data']}
Assunto: {email['assunto']}

{email['mensagem']}"""
            
            documents.append(content)
            metadatas.append({
                "source": "emails.txt",
                "linha": email["linha"],
                "de": email["de"],
                "para": email["para"],
                "data": email["data"],
                "assunto": email["assunto"]
            })
            ids.append(f"email_{i}")
        
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
    
    def _split_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """Divide texto em chunks com overlap."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Tentar quebrar em ponto natural (nova linha ou ponto)
            if end < len(text):
                # Procurar último \n ou . antes do limite
                break_point = text.rfind('\n', start, end)
                if break_point == -1 or break_point <= start:
                    break_point = text.rfind('. ', start, end)
                if break_point > start:
                    end = break_point + 1
            
            chunks.append(text[start:end].strip())
            start = end - overlap
            
            if start >= len(text):
                break
        
        return [c for c in chunks if c]  # Filtrar vazios
    
    def search_policy(self, query: str, k: int = RETRIEVER_K) -> list[DocumentResult]:
        """
        Busca híbrida na política de compliance.
        Prioriza busca por keywords (melhor para português) e complementa com semântica.
        
        Args:
            query: Texto de busca
            k: Número de resultados
            
        Returns:
            Lista de DocumentResult
        """
        # 1. Busca por keyword primeiro (mais confiável para português)
        keyword_results = self._keyword_search_policy(query, k)
        
        # Se encontrou resultados bons por keyword, usar eles
        if keyword_results:
            return keyword_results[:k]
        
        # 2. Fallback: busca semântica se keyword não encontrou nada
        semantic_results = self.policy_collection.query(
            query_texts=[query],
            n_results=k
        )
        
        return self._format_results(semantic_results)
    
    def _keyword_search_policy(self, query: str, k: int) -> list[DocumentResult]:
        """Busca por keywords nos documentos da política."""
        # Obter todos os documentos
        all_docs = self.policy_collection.get()
        
        documents = all_docs.get('documents', [])
        metadatas = all_docs.get('metadatas', [])
        
        # Extrair termos de busca (ignorar palavras muito curtas e stopwords)
        stopwords = {'qual', 'como', 'onde', 'quando', 'quem', 'que', 'para', 'com', 'por', 'uma', 'um', 'os', 'as', 'de', 'da', 'do', 'em', 'no', 'na', 'é', 'são'}
        terms = [t.lower() for t in query.split() if len(t) > 2 and t.lower() not in stopwords]
        
        # Termos compostos importantes (ex: "categoria B", "categoria A")
        query_lower = query.lower()
        composite_terms = []
        if 'categoria a' in query_lower:
            composite_terms.append('categoria a')
        if 'categoria b' in query_lower:
            composite_terms.append('categoria b')
        if 'categoria c' in query_lower:
            composite_terms.append('categoria c')
        
        # Pontuar documentos por número de matches
        scored = []
        for doc, meta in zip(documents, metadatas):
            doc_lower = doc.lower()
            
            # Score base por termos individuais
            score = sum(1 for term in terms if term in doc_lower)
            
            # Bonus para termos compostos (muito mais importante)
            for comp in composite_terms:
                if comp in doc_lower:
                    score += 10  # Grande bonus
            
            if score > 0:
                scored.append((score, doc, meta))
        
        # Ordenar por score (mais matches primeiro)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [
            DocumentResult(page_content=doc, metadata=meta)
            for _, doc, meta in scored[:k]
        ]
    
    def search_emails(self, query: str, k: int = RETRIEVER_K) -> list[DocumentResult]:
        """
        Busca semântica em emails.
        
        Args:
            query: Texto de busca
            k: Número de resultados
            
        Returns:
            Lista de DocumentResult
        """
        results = self.email_collection.query(
            query_texts=[query],
            n_results=k
        )
        
        return self._format_results(results)
    
    def search_emails_by_person(self, person: str, k: int = 10) -> list[DocumentResult]:
        """Busca emails de/para uma pessoa específica."""
        # Busca semântica + filtro por metadados
        results = self.email_collection.query(
            query_texts=[f"email {person}"],
            n_results=k * 2  # Buscar mais para filtrar
        )
        
        # Filtrar resultados que mencionam a pessoa
        filtered = []
        person_lower = person.lower()
        
        docs = results.get('documents', [[]])[0]
        metas = results.get('metadatas', [[]])[0]
        
        for doc, meta in zip(docs, metas):
            de = meta.get('de', '').lower()
            para = meta.get('para', '').lower()
            
            if person_lower in de or person_lower in para or person_lower in doc.lower():
                filtered.append(DocumentResult(page_content=doc, metadata=meta))
                if len(filtered) >= k:
                    break
        
        return filtered
    
    def _format_results(self, results: dict) -> list[DocumentResult]:
        """Converte resultados do Chroma para DocumentResult."""
        documents = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        
        return [
            DocumentResult(page_content=doc, metadata=meta)
            for doc, meta in zip(documents, metadatas)
        ]
    
    def rebuild_stores(self):
        """Reconstrói todas as coleções do zero."""
        # Deletar coleções existentes
        try:
            self._client.delete_collection("policy")
        except Exception:
            pass
        
        try:
            self._client.delete_collection("emails")
        except Exception:
            pass
        
        # Resetar cache
        self._policy_collection = None
        self._email_collection = None
        
        # Recriar (lazy loading)
        _ = self.policy_collection
        _ = self.email_collection
    
    def get_policy_stats(self) -> dict:
        """Retorna estatísticas da coleção de política."""
        return {
            "count": self.policy_collection.count(),
            "name": "policy"
        }
    
    def get_email_stats(self) -> dict:
        """Retorna estatísticas da coleção de emails."""
        return {
            "count": self.email_collection.count(),
            "name": "emails"
        }


# Singleton para reutilização
_manager: Optional[VectorStoreManager] = None


def get_vector_store_manager() -> VectorStoreManager:
    """Retorna a instância singleton do VectorStoreManager."""
    global _manager
    if _manager is None:
        _manager = VectorStoreManager()
    return _manager
