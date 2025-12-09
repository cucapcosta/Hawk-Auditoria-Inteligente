"""
HawkAI - Interface Streamlit
============================

Interface web para o chatbot de auditoria.
"""

import os
import sys

# Adicionar o diretório pai ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import requests
import json

# Configuração da página
st.set_page_config(
    page_title="HawkAI - Audit Chatbot",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URL da API (pode ser configurada via env)
API_URL = os.getenv("HAWKAI_API_URL", "http://localhost:5000")


def init_session_state():
    """Inicializa o estado da sessão."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "api_available" not in st.session_state:
        st.session_state.api_available = check_api_health()


def check_api_health() -> bool:
    """Verifica se a API está disponível."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def send_query(query: str, quick_mode: bool = False, progress_callback=None) -> dict:
    """
    Envia query para a API.
    
    Args:
        query: Pergunta do usuário
        quick_mode: Se True, usa endpoint rápido (só política)
        progress_callback: Função para atualizar progresso (opcional)
        
    Returns:
        Resposta da API
    """
    endpoint = "/audit/quick" if quick_mode else "/audit"
    
    try:
        response = requests.post(
            f"{API_URL}{endpoint}",
            json={"query": query},
            timeout=None  # Sem timeout - deixa a IA trabalhar
        )
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_query_stream(query: str, progress_callback) -> dict:
    """
    Envia query com streaming para mostrar progresso em tempo real.
    
    Args:
        query: Pergunta do usuário
        progress_callback: Função para atualizar progresso
        
    Returns:
        Resposta final
    """
    try:
        response = requests.post(
            f"{API_URL}/audit/stream",
            json={"query": query},
            stream=True,
            timeout=None
        )
        
        final_result = {}
        
        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                if line_text.startswith('data: '):
                    data = json.loads(line_text[6:])
                    
                    if data.get('done'):
                        break
                    elif data.get('error'):
                        return {"success": False, "error": data['error']}
                    elif data.get('message'):
                        progress_callback(data['message'])
                        # Guardar updates do último nó
                        if data.get('updates'):
                            final_result.update(data['updates'])
        
        return {"success": True, **final_result}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_examples() -> list:
    """Obtém exemplos de queries da API."""
    try:
        response = requests.get(f"{API_URL}/audit/examples", timeout=5)
        if response.status_code == 200:
            return response.json().get("examples", [])
    except Exception:
        pass
    
    # Fallback local
    return [
        {
            "category": "Política",
            "queries": [
                "Qual é o limite de gastos para categoria B?",
                "Quais restaurantes são aprovados?",
                "O que é proibido comprar?"
            ]
        },
        {
            "category": "Fraude",
            "queries": [
                "Investigue o Ryan por fraude",
                "Há evidências de smurfing?",
                "Quais fraudes foram detectadas?"
            ]
        }
    ]


def render_sidebar():
    """Renderiza a barra lateral."""
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/hawk.png", width=80)
        st.title("HawkAI")
        st.caption("Assistente de Auditoria - Dunder Mifflin")
        
        st.divider()
        
        # Status da API
        if st.session_state.api_available:
            st.success("🟢 API Online")
        else:
            st.error("🔴 API Offline")
            st.info("Execute: `python app/main.py`")
            if st.button("Tentar Reconectar"):
                st.session_state.api_available = check_api_health()
                st.rerun()
        
        st.divider()
        
        # Modo de consulta
        st.subheader("Configurações")
        quick_mode = st.toggle(
            "Modo Rápido",
            help="Consulta apenas a política (mais rápido)"
        )
        st.session_state.quick_mode = quick_mode
        
        st.divider()
        
        # Exemplos de queries
        st.subheader("Exemplos")
        examples = get_examples()
        
        for category in examples:
            with st.expander(category["category"]):
                for query in category["queries"]:
                    if st.button(query, key=f"ex_{hash(query)}", use_container_width=True):
                        st.session_state.pending_query = query
                        st.rerun()
        
        st.divider()
        
        # Limpar histórico
        if st.button("🗑️ Limpar Histórico", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        # Info
        st.divider()
        st.caption("Desenvolvido para auditoria da Dunder Mifflin Paper Company")


def render_chat():
    """Renderiza a interface de chat."""
    st.title("🦅 HawkAI - Assistente de Auditoria")
    
    # Container para mensagens
    chat_container = st.container()
    
    with chat_container:
        # Exibir histórico de mensagens
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    render_assistant_message(message)
                else:
                    st.markdown(message["content"])
    
    # Input do usuário
    if prompt := st.chat_input("Digite sua pergunta sobre auditoria..."):
        process_query(prompt)
    
    # Processar query pendente (dos exemplos)
    if "pending_query" in st.session_state:
        query = st.session_state.pending_query
        del st.session_state.pending_query
        process_query(query)


def process_query(query: str):
    """Processa uma query do usuário."""
    # Adicionar mensagem do usuário
    st.session_state.messages.append({
        "role": "user",
        "content": query
    })
    
    # Exibir mensagem do usuário
    with st.chat_message("user"):
        st.markdown(query)
    
    # Processar com a API
    with st.chat_message("assistant"):
        # Container para mostrar progresso
        progress_container = st.empty()
        status_text = st.empty()
        
        if st.session_state.api_available:
            quick_mode = st.session_state.get("quick_mode", False)
            use_streaming = st.session_state.get("use_streaming", True)
            
            # Mostrar aviso inicial
            with progress_container:
                st.info("""
                **Processando consulta...**
                
                A IA está analisando os dados. Consultas complexas podem levar 
                de 30 segundos a alguns minutos dependendo do hardware.
                """)
            
            if use_streaming and not quick_mode:
                # Usar streaming para mostrar progresso em tempo real
                def update_progress(message):
                    status_text.text(f"Status: {message}")
                
                response = send_query_stream(query, update_progress)
            else:
                # Modo simples sem streaming
                response = send_query(query, quick_mode)
            
            # Limpar indicadores de progresso
            progress_container.empty()
            status_text.empty()
            
            if response.get("success"):
                message_data = {
                    "role": "assistant",
                    "content": response.get("response", response.get("final_response", "")),
                    "query_type": response.get("query_type", ""),
                    "fraud_alerts": response.get("fraud_alerts", []),
                    "evidence_summary": response.get("evidence_summary", ""),
                    "nodes_visited": response.get("nodes_visited", [])
                }
            else:
                message_data = {
                    "role": "assistant",
                    "content": f"Erro: {response.get('error', 'Erro desconhecido')}",
                    "is_error": True
                }
        else:
            progress_container.empty()
            message_data = {
                "role": "assistant",
                "content": "API não disponível. Execute `python app/main.py` primeiro.",
                "is_error": True
            }
        
        # Salvar e renderizar
        st.session_state.messages.append(message_data)
        render_assistant_message(message_data)
    
    st.rerun()


def render_assistant_message(message: dict):
    """Renderiza uma mensagem do assistente com formatação especial."""
    content = message.get("content", "")
    
    # Se for erro, mostrar apenas o conteúdo
    if message.get("is_error"):
        st.error(content)
        return
    
    # Mostrar resposta principal
    st.markdown(content)
    
    # Mostrar alertas de fraude se houver
    fraud_alerts = message.get("fraud_alerts", [])
    if fraud_alerts:
        st.divider()
        st.subheader("🚨 Alertas de Fraude")
        
        for alert in fraud_alerts:
            severity = alert.get("severidade", "media")
            severity_colors = {
                "critica": "red",
                "alta": "orange",
                "media": "yellow",
                "baixa": "blue"
            }
            color = severity_colors.get(severity, "gray")
            
            with st.expander(f"⚠️ {alert.get('tipo', 'N/A').replace('_', ' ').title()} - {alert.get('funcionario', 'N/A')}"):
                cols = st.columns(2)
                with cols[0]:
                    st.metric("Severidade", severity.upper())
                    st.metric("Valor", f"${alert.get('valor_total', 0):,.2f}")
                with cols[1]:
                    st.write("**Regra Violada:**")
                    st.write(alert.get("regra_violada", "N/A"))
                
                st.write("**Descrição:**")
                st.write(alert.get("descricao", "N/A"))
                
                trans = alert.get("evidencias_transacao", [])
                if trans:
                    st.write("**Transações:**", ", ".join(trans))
    
    # Mostrar metadados em expander
    query_type = message.get("query_type", "")
    evidence = message.get("evidence_summary", "")
    nodes = message.get("nodes_visited", [])
    
    if query_type or evidence or nodes:
        with st.expander("📊 Detalhes da Análise"):
            if query_type:
                st.write(f"**Tipo de Query:** {query_type}")
            if nodes:
                st.write(f"**Nós Executados:** {' → '.join(nodes)}")
            if evidence:
                st.write("**Resumo de Evidências:**")
                st.markdown(evidence)


def main():
    """Função principal."""
    init_session_state()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
