"""
Transaction Analyzer
====================

Analisa transações aplicando regras de compliance.
"""

import pandas as pd
from typing import Optional
from dataclasses import dataclass, field

from app.config import TRANSACTIONS_FILE


@dataclass
class ComplianceViolation:
    """Representa uma violação de compliance."""
    tipo: str
    regra: str
    descricao: str
    severidade: str  # baixa, media, alta, critica


@dataclass
class TransactionAnalysis:
    """Resultado da análise de uma transação."""
    id_transacao: str
    data: str
    funcionario: str
    cargo: str
    descricao: str
    valor: float
    categoria: str
    departamento: str
    violacoes: list[ComplianceViolation] = field(default_factory=list)
    
    @property
    def has_violations(self) -> bool:
        return len(self.violacoes) > 0
    
    def to_dict(self) -> dict:
        return {
            "id_transacao": self.id_transacao,
            "data": self.data,
            "funcionario": self.funcionario,
            "cargo": self.cargo,
            "descricao": self.descricao,
            "valor": self.valor,
            "categoria": self.categoria,
            "departamento": self.departamento,
            "violacoes": [
                {
                    "tipo": v.tipo,
                    "regra": v.regra,
                    "descricao": v.descricao,
                    "severidade": v.severidade
                }
                for v in self.violacoes
            ]
        }


class TransactionAnalyzer:
    """
    Analisa transações aplicando regras da política de compliance.
    
    Regras implementadas (baseadas no documento):
    - Limites de alçada (Categoria A/B/C)
    - Itens proibidos (Lista Negra - Seção 3)
    - Locais restritos para refeições
    - Detecção de smurfing (divisão de transações)
    """
    
    # Limites de alçada (Seção 1)
    LIMITE_CATEGORIA_C = 50.00  # Autonomia do funcionário
    LIMITE_CATEGORIA_B = 500.00  # Requer aprovação do gerente
    # Acima de 500: Categoria A - Requer PO e aprovação do CFO
    
    # Locais permitidos para refeições (Seção 2.1)
    LOCAIS_APROVADOS = [
        "chili's", "cugino's", "cooper's seafood", "poor richard's"
    ]
    
    # Local banido
    LOCAIS_BANIDOS = ["hooters"]
    
    # Palavras-chave de itens proibidos (Seção 3)
    ITENS_PROIBIDOS = {
        "mágica": ("Seção 3.1", "Kit de mágica/entretenimento proibido"),
        "magica": ("Seção 3.1", "Kit de mágica/entretenimento proibido"),
        "algemas": ("Seção 3.1", "Equipamento de entretenimento proibido"),
        "houdini": ("Seção 3.1", "Equipamento de entretenimento proibido"),
        "karaokê": ("Seção 3.1", "Equipamento de entretenimento proibido"),
        "karaoke": ("Seção 3.1", "Equipamento de entretenimento proibido"),
        "arma": ("Seção 3.2", "Armamento proibido"),
        "airsoft": ("Seção 3.2", "Armamento proibido"),
        "ninja": ("Seção 3.2", "Armamento proibido"),
        "nunchaku": ("Seção 3.2", "Armamento proibido"),
        "armadilha": ("Seção 3.2", "Armadilhas proibidas"),
        "wuphf": ("Seção 3.3", "Investimento em negócio paralelo"),
        "startup": ("Seção 3.3", "Investimento em startup pessoal"),
        "vela": ("Seção 3.3", "Produto de cônjuge/parente - Conflito de interesse"),
        "serenity": ("Seção 3.3", "Produto de cônjuge - Serenity by Jan"),
        "beterraba": ("Seção 3.3", "Agroturismo/produtos agrícolas proibidos"),
        "vigilância": ("Seção 3.2", "Equipamento de vigilância não autorizado"),
        "binóculo": ("Seção 3.2", "Equipamento de vigilância"),
        "visão noturna": ("Seção 3.2", "Equipamento tático proibido"),
        "helicóptero": ("Seção 3.1", "Brinquedo não é despesa válida"),
        "brinquedo": ("Seção 3.1", "Brinquedos não são despesa válida"),
    }
    
    # Fornecedores suspeitos
    FORNECEDORES_SUSPEITOS = {
        "wcs supplies": "Fornecedor sem registro - possível fraude",
        "tech solutions": "Possível fachada para despesa pessoal",
        "a. sparkles": "Despesa veterinária pessoal",
        "sprinkles": "Despesa veterinária pessoal",
    }
    
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or str(TRANSACTIONS_FILE)
        self._df: Optional[pd.DataFrame] = None
    
    @property
    def df(self) -> pd.DataFrame:
        """Lazy loading do DataFrame."""
        if self._df is None:
            self._df = pd.read_csv(self.file_path)
        return self._df
    
    def analyze_transaction(self, row: pd.Series) -> TransactionAnalysis:
        """Analisa uma única transação."""
        analysis = TransactionAnalysis(
            id_transacao=str(row["id_transacao"]),
            data=str(row["data"]),
            funcionario=str(row["funcionario"]),
            cargo=str(row["cargo"]),
            descricao=str(row["descricao"]),
            valor=float(row["valor"]),
            categoria=str(row["categoria"]),
            departamento=str(row["departamento"])
        )
        
        # Aplicar regras
        self._check_valor_limite(analysis)
        self._check_itens_proibidos(analysis)
        self._check_locais_restritos(analysis)
        self._check_fornecedores_suspeitos(analysis)
        self._check_categoria_diversos(analysis)
        
        return analysis
    
    def _check_valor_limite(self, analysis: TransactionAnalysis):
        """Verifica se o valor excede limites de alçada."""
        valor = analysis.valor
        cargo = analysis.cargo.lower()
        
        # Gerente Regional tem mais autonomia
        is_manager = "gerente" in cargo
        
        if valor > self.LIMITE_CATEGORIA_B:
            # Categoria A - precisa de PO
            if not is_manager:
                analysis.violacoes.append(ComplianceViolation(
                    tipo="limite_excedido",
                    regra="Seção 1.3",
                    descricao=f"Valor ${valor:.2f} excede limite de ${self.LIMITE_CATEGORIA_B:.2f}. "
                              f"Requer Pedido de Compra aprovado pelo CFO.",
                    severidade="alta"
                ))
        elif valor > self.LIMITE_CATEGORIA_C:
            # Categoria B - precisa aprovação do gerente
            # Não podemos verificar aprovação, mas marcamos para revisão
            if cargo.lower() not in ["gerente regional", "contadora", "contador"]:
                # Para fins de demo, não marcamos como violação
                # pois não temos como verificar se houve aprovação
                pass
    
    def _check_itens_proibidos(self, analysis: TransactionAnalysis):
        """Verifica se a descrição contém itens proibidos."""
        descricao_lower = analysis.descricao.lower()
        
        for keyword, (regra, motivo) in self.ITENS_PROIBIDOS.items():
            if keyword in descricao_lower:
                analysis.violacoes.append(ComplianceViolation(
                    tipo="item_proibido",
                    regra=regra,
                    descricao=f"{motivo}. Descrição: '{analysis.descricao}'",
                    severidade="alta" if "3.3" in regra else "media"
                ))
    
    def _check_locais_restritos(self, analysis: TransactionAnalysis):
        """Verifica se a refeição foi em local banido."""
        descricao_lower = analysis.descricao.lower()
        
        for local in self.LOCAIS_BANIDOS:
            if local in descricao_lower:
                analysis.violacoes.append(ComplianceViolation(
                    tipo="local_banido",
                    regra="Seção 2.1",
                    descricao=f"Restaurante '{local.title()}' está na lista de locais banidos.",
                    severidade="media"
                ))
    
    def _check_fornecedores_suspeitos(self, analysis: TransactionAnalysis):
        """Verifica fornecedores suspeitos."""
        descricao_lower = analysis.descricao.lower()
        
        for fornecedor, motivo in self.FORNECEDORES_SUSPEITOS.items():
            if fornecedor in descricao_lower:
                analysis.violacoes.append(ComplianceViolation(
                    tipo="fornecedor_suspeito",
                    regra="Seção 3.3",
                    descricao=f"{motivo}. Fornecedor: '{fornecedor}'",
                    severidade="alta"
                ))
    
    def _check_categoria_diversos(self, analysis: TransactionAnalysis):
        """Verifica uso indevido da categoria 'Diversos'."""
        if analysis.categoria.lower() == "diversos" and analysis.valor > 5.00:
            analysis.violacoes.append(ComplianceViolation(
                tipo="categoria_invalida",
                regra="Seção 2",
                descricao=f"Categoria 'Diversos' não é aceitável para valores acima de $5.00. "
                          f"Valor: ${analysis.valor:.2f}",
                severidade="baixa"
            ))
    
    def analyze_all(self) -> list[TransactionAnalysis]:
        """Analisa todas as transações."""
        results = []
        for _, row in self.df.iterrows():
            analysis = self.analyze_transaction(row)
            results.append(analysis)
        return results
    
    def get_violations(self) -> list[TransactionAnalysis]:
        """Retorna apenas transações com violações."""
        return [a for a in self.analyze_all() if a.has_violations]
    
    def search_by_employee(self, employee: str) -> list[TransactionAnalysis]:
        """Busca transações de um funcionário específico."""
        employee_lower = employee.lower()
        results = []
        for _, row in self.df.iterrows():
            if employee_lower in str(row["funcionario"]).lower():
                results.append(self.analyze_transaction(row))
        return results
    
    def search_by_value_range(
        self, 
        min_value: float = 0, 
        max_value: float = float("inf")
    ) -> list[TransactionAnalysis]:
        """Busca transações em um intervalo de valor."""
        mask = (self.df["valor"] >= min_value) & (self.df["valor"] <= max_value)
        results = []
        for _, row in self.df[mask].iterrows():
            results.append(self.analyze_transaction(row))
        return results
    
    def detect_smurfing(
        self, 
        employee: str, 
        date: str, 
        threshold: float = 500.00
    ) -> list[TransactionAnalysis]:
        """
        Detecta possível smurfing (divisão de transações).
        
        Verifica se há múltiplas transações do mesmo funcionário
        no mesmo dia que, somadas, ultrapassam o limite.
        """
        employee_lower = employee.lower()
        
        # Filtrar transações do funcionário na data
        mask = (
            self.df["funcionario"].str.lower().str.contains(employee_lower) &
            (self.df["data"] == date)
        )
        
        day_transactions = self.df[mask]
        
        if len(day_transactions) <= 1:
            return []
        
        total = day_transactions["valor"].sum()
        
        if total > threshold:
            results = []
            for _, row in day_transactions.iterrows():
                analysis = self.analyze_transaction(row)
                analysis.violacoes.append(ComplianceViolation(
                    tipo="smurfing",
                    regra="Seção 1.3",
                    descricao=f"Possível divisão de transações. Total no dia: ${total:.2f}. "
                              f"Número de transações: {len(day_transactions)}",
                    severidade="critica"
                ))
                results.append(analysis)
            return results
        
        return []
    
    def get_summary_by_employee(self) -> pd.DataFrame:
        """Retorna resumo de gastos por funcionário."""
        return self.df.groupby("funcionario").agg({
            "valor": ["sum", "mean", "count", "max"]
        }).round(2)
    
    def get_high_value_transactions(self, threshold: float = 500.00) -> list[TransactionAnalysis]:
        """Retorna transações acima de um valor."""
        return self.search_by_value_range(min_value=threshold)


# Singleton
_analyzer: Optional[TransactionAnalyzer] = None


def get_transaction_analyzer() -> TransactionAnalyzer:
    """Retorna a instância singleton do TransactionAnalyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = TransactionAnalyzer()
    return _analyzer
