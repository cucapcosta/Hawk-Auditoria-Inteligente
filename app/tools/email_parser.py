"""
Email Parser
============

Parser para o formato de dump de emails da Dunder Mifflin.
"""

import re
from typing import Optional
from dataclasses import dataclass

from app.config import EMAILS_FILE


@dataclass
class Email:
    """Representa um email parseado."""
    de: str
    para: str
    data: str
    assunto: str
    mensagem: str
    linha: int  # Linha inicial no arquivo
    
    def to_dict(self) -> dict:
        return {
            "de": self.de,
            "para": self.para,
            "data": self.data,
            "assunto": self.assunto,
            "mensagem": self.mensagem,
            "linha": self.linha
        }


class EmailParser:
    """
    Parser para o dump de emails.
    
    O formato esperado é:
    -------------------------------------------------------------------------------
    De: nome <email>
    Para: nome <email>
    Data: YYYY-MM-DD HH:MM
    Assunto: texto
    Mensagem:
    texto da mensagem
    -------------------------------------------------------------------------------
    """
    
    # Padrões regex
    SEPARATOR = r"-{70,}"
    DE_PATTERN = r"^De:\s*(.+)$"
    PARA_PATTERN = r"^Para:\s*(.+)$"
    DATA_PATTERN = r"^Data:\s*(.+)$"
    ASSUNTO_PATTERN = r"^Assunto:\s*(.+)$"
    MENSAGEM_PATTERN = r"^Mensagem:\s*$"
    
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or str(EMAILS_FILE)
        self._emails: Optional[list[Email]] = None
    
    @property
    def emails(self) -> list[Email]:
        """Lazy loading dos emails."""
        if self._emails is None:
            self._emails = self._parse_file()
        return self._emails
    
    def _parse_file(self) -> list[Email]:
        """Parseia o arquivo completo de emails."""
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Dividir por separadores
        blocks = re.split(self.SEPARATOR, content)
        
        emails = []
        current_line = 1
        
        for block in blocks:
            block = block.strip()
            if not block:
                current_line += block.count("\n") + 1
                continue
            
            # Pular cabeçalho do arquivo
            if "DUMP DE SERVIDOR" in block or "PERÍODO:" in block:
                current_line += block.count("\n") + 1
                continue
            
            email = self._parse_block(block, current_line)
            if email:
                emails.append(email)
            
            current_line += block.count("\n") + 1
        
        return emails
    
    def _parse_block(self, block: str, start_line: int) -> Optional[Email]:
        """Parseia um bloco de email individual."""
        lines = block.strip().split("\n")
        
        de = para = data = assunto = ""
        mensagem_lines = []
        in_message = False
        
        for line in lines:
            line = line.strip()
            
            # Tentar casar com padrões
            de_match = re.match(self.DE_PATTERN, line, re.IGNORECASE)
            para_match = re.match(self.PARA_PATTERN, line, re.IGNORECASE)
            data_match = re.match(self.DATA_PATTERN, line, re.IGNORECASE)
            assunto_match = re.match(self.ASSUNTO_PATTERN, line, re.IGNORECASE)
            mensagem_match = re.match(self.MENSAGEM_PATTERN, line, re.IGNORECASE)
            
            if de_match:
                de = de_match.group(1).strip()
                in_message = False
            elif para_match:
                para = para_match.group(1).strip()
                in_message = False
            elif data_match:
                data = data_match.group(1).strip()
                in_message = False
            elif assunto_match:
                assunto = assunto_match.group(1).strip()
                in_message = False
            elif mensagem_match:
                in_message = True
            elif in_message:
                mensagem_lines.append(line)
        
        # Validar que temos dados mínimos
        if not (de and para):
            return None
        
        mensagem = "\n".join(mensagem_lines).strip()
        
        return Email(
            de=de,
            para=para,
            data=data,
            assunto=assunto,
            mensagem=mensagem,
            linha=start_line
        )
    
    def parse_all(self) -> list[dict]:
        """Retorna todos os emails como dicionários."""
        return [e.to_dict() for e in self.emails]
    
    def search_by_sender(self, sender: str) -> list[Email]:
        """Busca emails por remetente (busca parcial)."""
        sender_lower = sender.lower()
        return [e for e in self.emails if sender_lower in e.de.lower()]
    
    def search_by_recipient(self, recipient: str) -> list[Email]:
        """Busca emails por destinatário (busca parcial)."""
        recipient_lower = recipient.lower()
        return [e for e in self.emails if recipient_lower in e.para.lower()]
    
    def search_by_person(self, person: str) -> list[Email]:
        """Busca emails onde a pessoa é remetente ou destinatário."""
        person_lower = person.lower()
        return [
            e for e in self.emails 
            if person_lower in e.de.lower() or person_lower in e.para.lower()
        ]
    
    def search_by_content(self, keyword: str) -> list[Email]:
        """Busca emails que contêm a palavra-chave no assunto ou mensagem."""
        keyword_lower = keyword.lower()
        return [
            e for e in self.emails
            if keyword_lower in e.assunto.lower() or keyword_lower in e.mensagem.lower()
        ]
    
    def search_by_date_range(self, start_date: str, end_date: str) -> list[Email]:
        """Busca emails em um intervalo de datas (formato: YYYY-MM-DD)."""
        return [
            e for e in self.emails
            if start_date <= e.data[:10] <= end_date
        ]
    
    def get_by_line(self, line: int) -> Optional[Email]:
        """Busca email pela linha aproximada no arquivo."""
        for email in self.emails:
            if abs(email.linha - line) < 20:  # Tolerância de 20 linhas
                return email
        return None


# Singleton
_parser: Optional[EmailParser] = None


def get_email_parser() -> EmailParser:
    """Retorna a instância singleton do EmailParser."""
    global _parser
    if _parser is None:
        _parser = EmailParser()
    return _parser
