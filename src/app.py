"""
HawkAI - Sistema de Auditoria com Agentes de IA
Interface estilo Terminal Retro (Fallout/Pip-Boy)
"""

import streamlit as st
from datetime import datetime
from rag import get_rag
from synth import synthesize
from router import route

# Configuracao da pagina
st.set_page_config(
    page_title="HawkAI Terminal",
    page_icon="terminal",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS - Estilo Terminal Retro Fallout
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');
    
    /* Base */
    .stApp {
        background: #0a0a0a;
        font-family: 'VT323', monospace;
    }
    
    /* Esconder elementos padrao */
    #MainMenu, footer, header,
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    .stDeployButton,
    .stChatInput,
    [data-testid="stChatInput"],
    [data-testid="stBottom"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Terminal frame aplicado ao block-container */
    .block-container {
        background: linear-gradient(180deg, #001a00 0%, #000d00 100%);
        border: 3px solid #00ff00;
        border-radius: 5px;
        padding: 1.5rem !important;
        margin: 1rem auto !important;
        max-width: 750px !important;
        box-shadow: 
            0 0 20px rgba(0, 255, 0, 0.3),
            inset 0 0 50px rgba(0, 255, 0, 0.03);
        position: relative;
    }
    
    /* Scanlines */
    .block-container::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: repeating-linear-gradient(
            0deg,
            rgba(0, 0, 0, 0.1),
            rgba(0, 0, 0, 0.1) 1px,
            transparent 1px,
            transparent 2px
        );
        pointer-events: none;
        z-index: 1;
    }
    
    .block-container > * {
        position: relative;
        z-index: 2;
    }
    
    /* Header */
    .term-header {
        text-align: center;
        border-bottom: 2px solid #00aa00;
        padding-bottom: 1rem;
        margin-bottom: 1rem;
    }
    
    .term-title {
        color: #00ff00;
        font-size: 3rem;
        margin: 0;
        text-shadow: 0 0 10px #00ff00;
        letter-spacing: 8px;
    }
    
    .term-subtitle {
        color: #00aa00;
        font-size: 1.1rem;
        margin: 0.3rem 0 0 0;
        letter-spacing: 3px;
    }
    
    .term-status {
        display: flex;
        justify-content: space-between;
        color: #00bb00;
        font-size: 0.85rem;
        margin-top: 0.8rem;
        padding-top: 0.5rem;
        border-top: 1px solid #003300;
    }
    
    /* Output box */
    .output-box {
        background: rgba(0, 20, 0, 0.5);
        border: 1px solid #004400;
        padding: 1rem;
        margin: 0.8rem 0;
        color: #00ff00;
        font-size: 1.1rem;
        line-height: 1.5;
    }
    
    .output-box.user {
        color: #ffff00;
        border-left: 3px solid #ffff00;
    }
    
    .output-box.system {
        border-left: 3px solid #00ff00;
    }
    
    .output-box.step {
        border-left: 3px solid #00aaaa;
        color: #00cccc;
        font-size: 0.95rem;
        padding: 0.5rem 1rem;
        margin: 0.3rem 0;
    }
    
    .output-box.answer {
        border-left: 3px solid #00ff00;
        border: 2px solid #00aa00;
        background: rgba(0, 40, 0, 0.5);
    }
    
    .prefix-user::before {
        content: "> ";
        color: #ffff00;
    }
    
    .prefix-sys::before {
        content: "[HAWKAI] ";
        color: #008800;
    }
    
    .prefix-step::before {
        content: ">> ";
        color: #008888;
    }
    
    /* Cursor */
    .blink {
        animation: blink 1s infinite;
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
    
    /* Prompt */
    .prompt-line {
        color: #00dd00;
        font-size: 1rem;
        margin-top: 1rem;
    }
    
    /* Divider */
    .term-divider {
        border: none;
        border-top: 1px solid #003300;
        margin: 1rem 0;
    }
    
    /* Buttons */
    .stButton > button {
        background: transparent !important;
        border: 1px solid #00aa00 !important;
        border-radius: 0 !important;
        color: #00ff00 !important;
        font-family: 'VT323', monospace !important;
        font-size: 1.1rem !important;
        letter-spacing: 1px;
    }
    
    .stButton > button:hover {
        background: rgba(0, 255, 0, 0.1) !important;
        border-color: #00ff00 !important;
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.3) !important;
    }
    
    /* Text input estilizado */
    .stTextInput > div > div > input {
        background: rgba(0, 20, 0, 0.9) !important;
        border: 2px solid #00aa00 !important;
        border-radius: 0 !important;
        color: #00ff00 !important;
        font-family: 'VT323', monospace !important;
        font-size: 1.1rem !important;
        padding: 0.8rem 1rem !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #00ff00 !important;
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.3) !important;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #006600 !important;
    }
    
    .stTextInput > label {
        display: none !important;
    }
    
    /* Esconder botao submit do form */
    .stForm [data-testid="stFormSubmitButton"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)


def check_ollama_status() -> bool:
    """Verifica se o Ollama esta rodando"""
    try:
        import ollama
        ollama.list()
        return True
    except Exception:
        return False


# Estado
if "messages" not in st.session_state:
    st.session_state.messages = []

if "rag_ready" not in st.session_state:
    st.session_state.rag_ready = False

if "rag_instance" not in st.session_state:
    st.session_state.rag_instance = None

# Dados
ollama_online = check_ollama_status()
status_text = "ONLINE" if ollama_online else "OFFLINE"
current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

# === HEADER ===
st.markdown(f"""
<div class="term-header">
    <h1 class="term-title">HAWKAI</h1>
    <p class="term-subtitle">SISTEMA DE AUDITORIA v1.0</p>
    <div class="term-status">
        <span>{current_time}</span>
        <span>OLLAMA: {status_text}</span>
        <span>DUNDER MIFFLIN</span>
    </div>
</div>
""", unsafe_allow_html=True)

# === INICIALIZACAO DO RAG (tela de loading) ===
if not st.session_state.rag_ready:
    st.markdown("""
    <div class="output-box system">
        <span class="prefix-sys"></span>INICIALIZANDO SISTEMA...
    </div>
    """, unsafe_allow_html=True)
    
    # Container para mostrar progresso
    progress_container = st.empty()
    
    try:
        rag = get_rag()
        st.session_state.rag_instance = rag
        
        # Inicializa e mostra progresso
        status_lines = []
        for status in rag.initialize():
            status_lines.append(f">> {status}")
            progress_html = "<br>".join(status_lines[-10:])  # Mostra ultimas 10 linhas
            progress_container.markdown(
                f'<div class="output-box step">{progress_html}</div>',
                unsafe_allow_html=True
            )
        
        st.session_state.rag_ready = True
        st.rerun()
        
    except Exception as e:
        st.markdown(f"""
        <div class="output-box answer">
            <span class="prefix-sys"></span>ERRO NA INICIALIZACAO: {str(e)}
        </div>
        """, unsafe_allow_html=True)
        st.stop()

# === INTERFACE PRINCIPAL (so aparece depois do RAG pronto) ===

# Mostrar historico de mensagens
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="output-box user"><span class="prefix-user"></span>{msg["content"]}</div>', unsafe_allow_html=True)
    elif msg["role"] == "step":
        st.markdown(f'<div class="output-box step"><span class="prefix-step"></span>{msg["content"]}</div>', unsafe_allow_html=True)
    elif msg["role"] == "answer":
        content = msg["content"].replace("\n", "<br>")
        st.markdown(f'<div class="output-box answer"><span class="prefix-sys"></span>{content}</div>', unsafe_allow_html=True)
    else:
        content = msg["content"].replace("\n", "<br>")
        st.markdown(f'<div class="output-box system"><span class="prefix-sys"></span>{content}</div>', unsafe_allow_html=True)

# Mensagem inicial se nao tem historico
if not st.session_state.messages:
    st.markdown("""
    <div class="output-box system">
        <span class="prefix-sys"></span>SISTEMA PRONTO.<br>
        DIGITE SUA PERGUNTA SOBRE A POLITICA DE COMPLIANCE.
    </div>
    <p class="prompt-line"><span class="blink">_</span> AGUARDANDO COMANDO...</p>
    """, unsafe_allow_html=True)

# Botao limpar
if st.session_state.messages:
    st.markdown('<hr class="term-divider">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("[LIMPAR]", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# Container para logs em tempo real (aparece durante processamento)
live_logs = st.empty()

# Input
if "processing" not in st.session_state:
    st.session_state.processing = False

with st.form(key="input_form", clear_on_submit=True):
    prompt = st.text_input("Input", placeholder="DIGITE SUA PERGUNTA...", label_visibility="collapsed")
    submitted = st.form_submit_button("ENVIAR", use_container_width=True)

# Helper para atualizar logs em tempo real
def update_logs(logs: list[str], container):
    logs_html = "<br>".join([f">> {log}" for log in logs])
    container.markdown(f'<div class="output-box step">{logs_html}</div>', unsafe_allow_html=True)

def run_generator(gen, logs: list[str], container):
    """Executa generator atualizando logs em tempo real"""
    try:
        while True:
            status = next(gen)
            logs.append(status)
            st.session_state.messages.append({"role": "step", "content": status})
            update_logs(logs, container)
    except StopIteration as e:
        return e.value
    return None

# Processa fora do form para permitir atualizacao em tempo real
if submitted and prompt and not st.session_state.processing:
    st.session_state.processing = True
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Mostra pergunta imediatamente
    st.markdown(f'<div class="output-box user"><span class="prefix-user"></span>{prompt}</div>', unsafe_allow_html=True)
    
    try:
        logs = []
        
        # 0. Router - decide qual fluxo seguir
        route_name = run_generator(route(prompt), logs, live_logs)
        
        if route_name == "compliance":
            # Fluxo de compliance: RAG + Synth
            rag = st.session_state.rag_instance
            if rag is None:
                raise Exception("RAG nao inicializado")
            
            # 1. Busca contexto com RAG
            context_chunks = run_generator(rag.search(prompt), logs, live_logs) or []
            
            # 2. Sintetiza resposta com LLM
            answer = run_generator(synthesize(prompt, context_chunks), logs, live_logs)
            answer = answer or "Erro ao sintetizar resposta."
        
        elif route_name == "emails":
            # TODO: Implementar analise de emails
            answer = "ANALISE DE EMAILS: Funcionalidade em desenvolvimento."
        
        elif route_name == "transacoes":
            # TODO: Implementar analise de transacoes
            answer = "ANALISE DE TRANSACOES: Funcionalidade em desenvolvimento."
        
        elif route_name == "auditoria":
            # TODO: Implementar auditoria completa
            answer = "AUDITORIA COMPLETA: Funcionalidade em desenvolvimento."
        
        else:
            answer = "Rota desconhecida."
        
        st.session_state.messages.append({"role": "answer", "content": answer})
    
    except Exception as e:
        st.session_state.messages.append({"role": "answer", "content": f"ERRO: {str(e)}"})
    
    st.session_state.processing = False
    st.rerun()
