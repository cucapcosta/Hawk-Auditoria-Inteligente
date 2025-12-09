"""
RAG Node
========

Busca informações relevantes na política de compliance usando RAG.
Sistema 100% local com Ollama.
"""

from app.llm import get_llm
from app.graph.state import AuditState
from app.tools.vector_store import get_vector_store_manager
from app.prompts.templates import RAG_PROMPT


def rag_node(state: AuditState) -> dict:
    """
    Busca na política de compliance usando RAG.
    
    Args:
        state: Estado atual do grafo
        
    Returns:
        Atualizações para o estado (policy_context, policy_sections)
    """
    query = state["query"]
    entities = state.get("entities", [])
    
    try:
        # Obter vector store manager
        vs_manager = get_vector_store_manager()
        
        # Buscar documentos relevantes
        docs = vs_manager.search_policy(query)
        
        # Se houver entidades, fazer busca adicional
        if entities:
            for entity in entities[:3]:  # Limitar a 3 entidades
                entity_docs = vs_manager.search_policy(str(entity), k=2)
                docs.extend(entity_docs)
        
        # Remover duplicatas mantendo ordem
        seen_contents = set()
        unique_docs = []
        for doc in docs:
            content_hash = hash(doc.page_content[:100])
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_docs.append(doc)
        
        # Extrair contexto e seções
        policy_context = [doc.page_content for doc in unique_docs]
        policy_sections = list(set(
            doc.metadata.get("section_title", "Seção não identificada")
            for doc in unique_docs
        ))
        
        return {
            "policy_context": policy_context,
            "policy_sections": policy_sections,
            "nodes_visited": ["rag"]
        }
        
    except Exception as e:
        return {
            "policy_context": [],
            "policy_sections": [],
            "nodes_visited": ["rag"],
            "error": f"RAG error: {str(e)}"
        }


def generate_policy_response(state: AuditState) -> str:
    """
    Gera uma resposta baseada na política usando o contexto recuperado.
    
    Args:
        state: Estado com policy_context preenchido
        
    Returns:
        Resposta gerada pelo LLM
    """
    query = state["query"]
    context = "\n\n---\n\n".join(state.get("policy_context", []))
    
    if not context:
        return "Não encontrei informações relevantes na política de compliance."
    
    # Inicializar LLM otimizado
    llm = get_llm()
    
    # Formatar prompt
    prompt = RAG_PROMPT.format(context=context, question=query)
    
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"Erro ao gerar resposta: {str(e)}"
