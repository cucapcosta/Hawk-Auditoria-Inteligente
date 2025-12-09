"""
HawkAI - Flask API
==================

API REST para o chatbot de auditoria.
"""

import os
import sys

# Adicionar o diretório pai ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json

from app.config import validate_config, check_ollama
from app.graph.workflow import run_audit, run_audit_stream, run_quick_policy_query
from app.graph.state import create_initial_state


# Criar app Flask
app = Flask(__name__)
CORS(app)  # Permitir CORS para o Streamlit


@app.route("/", methods=["GET"])
def home():
    """Endpoint de health check."""
    return jsonify({
        "status": "online",
        "service": "HawkAI - Audit Chatbot",
        "version": "1.0.0",
        "endpoints": {
            "/audit": "POST - Executar consulta de auditoria",
            "/audit/stream": "POST - Executar consulta com streaming",
            "/audit/quick": "POST - Consulta rápida apenas na política",
            "/health": "GET - Status do serviço"
        }
    })


@app.route("/health", methods=["GET"])
def health():
    """Verifica saúde do serviço (Ollama local)."""
    try:
        # Verificar se Ollama está rodando
        ollama_ok, ollama_msg = check_ollama()
        
        return jsonify({
            "status": "healthy" if ollama_ok else "degraded",
            "ollama_status": ollama_ok,
            "message": ollama_msg
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@app.route("/audit", methods=["POST"])
def audit():
    """
    Executa uma consulta de auditoria completa.
    
    Request Body:
        {
            "query": "Pergunta do usuário"
        }
    
    Response:
        {
            "success": true,
            "query": "...",
            "query_type": "...",
            "response": "...",
            "evidence_summary": "...",
            "fraud_alerts": [...],
            "nodes_visited": [...]
        }
    """
    try:
        data = request.get_json()
        
        if not data or "query" not in data:
            return jsonify({
                "success": False,
                "error": "Campo 'query' é obrigatório"
            }), 400
        
        query = data["query"].strip()
        
        if not query:
            return jsonify({
                "success": False,
                "error": "Query não pode ser vazia"
            }), 400
        
        # Executar auditoria
        result = run_audit(query)
        
        # Formatar resposta
        response = {
            "success": True,
            "query": query,
            "query_type": result.get("query_type", "unknown"),
            "response": result.get("final_response", ""),
            "evidence_summary": result.get("evidence_summary", ""),
            "fraud_alerts": _serialize_fraud_alerts(result.get("fraud_alerts", [])),
            "transaction_count": len(result.get("transaction_results", [])),
            "email_count": len(result.get("email_results", [])),
            "nodes_visited": result.get("nodes_visited", []),
            "error": result.get("error")
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/audit/stream", methods=["POST"])
def audit_stream():
    """
    Executa consulta com streaming de resultados.
    
    Retorna Server-Sent Events (SSE) com atualizações em tempo real.
    Útil para mostrar progresso ao usuário durante processamento longo.
    """
    try:
        data = request.get_json()
        
        if not data or "query" not in data:
            return jsonify({
                "success": False,
                "error": "Campo 'query' é obrigatório"
            }), 400
        
        query = data["query"].strip()
        
        # Mapeamento de nomes de nós para mensagens amigáveis
        node_messages = {
            "router": "Classificando tipo de consulta...",
            "rag": "Buscando na política de compliance...",
            "email": "Analisando emails corporativos...",
            "transaction": "Verificando transações...",
            "fraud": "Detectando padrões de fraude...",
            "synthesizer": "IA gerando resposta (pode demorar)..."
        }
        
        def generate():
            try:
                for event in run_audit_stream(query):
                    for node_name, updates in event.items():
                        # Enviar mensagem de progresso amigável
                        progress_msg = node_messages.get(node_name, f"Processando {node_name}...")
                        yield f"data: {json.dumps({'node': node_name, 'message': progress_msg, 'updates': _serialize_state(updates)})}\n\n"
                
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Desabilita buffering no nginx
            }
        )
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/audit/quick", methods=["POST"])
def audit_quick():
    """
    Consulta rápida apenas na política de compliance.
    
    Mais rápido para perguntas simples sobre regras.
    """
    try:
        data = request.get_json()
        
        if not data or "query" not in data:
            return jsonify({
                "success": False,
                "error": "Campo 'query' é obrigatório"
            }), 400
        
        query = data["query"].strip()
        
        # Executar consulta rápida
        result = run_quick_policy_query(query)
        
        return jsonify({
            "success": True,
            "query": query,
            "query_type": "policy",
            "response": result.get("final_response", ""),
            "policy_sections": result.get("policy_sections", []),
            "nodes_visited": result.get("nodes_visited", [])
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/audit/examples", methods=["GET"])
def get_examples():
    """Retorna exemplos de queries para teste."""
    return jsonify({
        "examples": [
            {
                "category": "Política",
                "queries": [
                    "Qual é o limite de gastos para categoria B?",
                    "Quais restaurantes são aprovados para refeições?",
                    "O que é proibido comprar segundo a política?"
                ]
            },
            {
                "category": "Transações",
                "queries": [
                    "Quais transações do Ryan estão acima de $500?",
                    "Liste todas as transações suspeitas",
                    "Quem gastou mais na categoria Diversos?"
                ]
            },
            {
                "category": "Emails",
                "queries": [
                    "O que o Dwight enviou sobre equipamentos?",
                    "Há emails mencionando WUPHF?",
                    "Quais emails falam sobre compras pessoais?"
                ]
            },
            {
                "category": "Fraude",
                "queries": [
                    "Investigue o Ryan por fraude",
                    "Há evidências de smurfing nos dados?",
                    "Cruze emails e transações do Dwight",
                    "Quais fraudes foram detectadas?"
                ]
            }
        ]
    })


def _serialize_fraud_alerts(alerts: list) -> list:
    """Serializa alertas de fraude para JSON."""
    serialized = []
    for alert in alerts:
        serialized.append({
            "tipo": alert.get("tipo", ""),
            "severidade": alert.get("severidade", ""),
            "funcionario": alert.get("funcionario", ""),
            "descricao": alert.get("descricao", ""),
            "valor_total": alert.get("valor_total", 0),
            "regra_violada": alert.get("regra_violada", ""),
            "evidencias_transacao": alert.get("evidencias_transacao", []),
            "evidencias_email": alert.get("evidencias_email", [])
        })
    return serialized


def _serialize_state(state: dict) -> dict:
    """Serializa estado para JSON (remove objetos não serializáveis)."""
    serialized = {}
    for key, value in state.items():
        try:
            json.dumps(value)  # Testar se é serializável
            serialized[key] = value
        except (TypeError, ValueError):
            serialized[key] = str(value)
    return serialized


def create_app():
    """Factory function para criar a app."""
    return app


if __name__ == "__main__":
    print("=" * 60)
    print("  HawkAI - Audit Chatbot API")
    print("=" * 60)
    
    # Verificar configuração
    try:
        validate_config()
        print("✓ Configuração válida")
    except ValueError as e:
        print(f"⚠ Aviso: {e}")
        print("  A API iniciará, mas algumas funções podem não funcionar.")
    
    print("\nEndpoints disponíveis:")
    print("  POST /audit       - Consulta completa")
    print("  POST /audit/quick - Consulta rápida (só política)")
    print("  GET  /audit/examples - Exemplos de queries")
    print("  GET  /health      - Status do serviço")
    print("\n" + "=" * 60)
    
    # Iniciar servidor
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
