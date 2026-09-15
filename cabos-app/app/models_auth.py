from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    empresa = Column(String(255), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    ativo = Column(Boolean, default=True)
    aprovado = Column(Boolean, default=False)
    role = Column(String(50), default="user")
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_aprovacao = Column(DateTime, nullable=True)
    aprovado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    solicitacoes = relationship("SolicitacaoUsuario", back_populates="usuario", foreign_keys="SolicitacaoUsuario.usuario_id")
    logs = relationship("AccessLog", back_populates="usuario")


class SolicitacaoUsuario(Base):
    __tablename__ = "solicitacoes_usuario"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    empresa = Column(String(255), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    status = Column(String(50), default="pendente")
    data_solicitacao = Column(DateTime, default=datetime.utcnow)
    data_decisao = Column(DateTime, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    decidido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    motivo_rejeicao = Column(Text, nullable=True)

    usuario = relationship("Usuario", back_populates="solicitacoes", foreign_keys=[usuario_id])


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    ip_address = Column(String(50), nullable=True)
    data_hora = Column(DateTime, default=datetime.utcnow)
    acao = Column(String(100), nullable=False)
    projeto_id = Column(Integer, nullable=True)
    detalhes = Column(JSON, nullable=True)

    usuario = relationship("Usuario", back_populates="logs")
