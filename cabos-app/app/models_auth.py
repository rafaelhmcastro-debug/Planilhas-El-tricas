"""
Modelos de Autenticação e Autorização
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from .database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    empresa = Column(String(100), nullable=False)
    senha_hash = Column(String(255), nullable=False)

    # Status
    ativo = Column(Boolean, default=False)
    aprovado = Column(Boolean, default=False)
    role = Column(String(20), default="user")  # admin, user

    # Auditoria
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_aprovacao = Column(DateTime, nullable=True)
    aprovado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    # Relacionamentos
    logs = relationship("AccessLog", back_populates="usuario")
    aprovado_por = relationship("Usuario", remote_side=[id])

    def __repr__(self):
        return f"<Usuario {self.username}>"


class SolicitacaoUsuario(Base):
    __tablename__ = "solicitacoes_usuario"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    empresa = Column(String(100), nullable=False)
    senha_hash = Column(String(255), nullable=False)

    # Status
    status = Column(String(20), default="pendente")  # pendente, aprovado, rejeitado

    # Auditoria
    data_solicitacao = Column(DateTime, default=datetime.utcnow)
    data_decisao = Column(DateTime, nullable=True)
    decidido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    motivo_rejeicao = Column(Text, nullable=True)

    # Relacionamentos
    decidido_por = relationship("Usuario", foreign_keys=[decidido_por_id])

    def __repr__(self):
        return f"<SolicitacaoUsuario {self.username} - {self.status}>"


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)

    # Acesso
    ip_address = Column(String(50), nullable=True)
    data_hora = Column(DateTime, default=datetime.utcnow, index=True)

    # Ação
    acao = Column(String(50), nullable=False, index=True)  # login, logout, criar_projeto, etc
    projeto_id = Column(Integer, nullable=True)

    # Detalhes
    detalhes = Column(JSON, nullable=True)  # dados extras em formato JSON

    # Relacionamentos
    usuario = relationship("Usuario", back_populates="logs")

    def __repr__(self):
        return f"<AccessLog {self.usuario_id} - {self.acao}>"
