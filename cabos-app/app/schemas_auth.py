"""
Schemas de Autenticação (Pydantic)
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ==================== LOGIN ====================

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    senha: str = Field(..., min_length=6)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: "UsuarioResponse"


# ==================== CADASTRO ====================

class CadastroRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    empresa: str = Field(..., min_length=1, max_length=100)
    senha: str = Field(..., min_length=8)
    confirmar_senha: str


class CadastroResponse(BaseModel):
    id: int
    username: str
    email: str
    empresa: str
    status: str = "pendente"
    data_solicitacao: datetime


# ==================== USUARIO ====================

class UsuarioResponse(BaseModel):
    id: int
    username: str
    email: str
    empresa: str
    ativo: bool
    aprovado: bool
    role: str
    data_criacao: datetime

    class Config:
        from_attributes = True


class UsuarioAdmin(BaseModel):
    id: int
    username: str
    email: str
    empresa: str
    ativo: bool
    aprovado: bool
    role: str
    data_criacao: datetime
    data_aprovacao: Optional[datetime]
    aprovado_por_id: Optional[int]


# ==================== SOLICITACOES ====================

class SolicitacaoResponse(BaseModel):
    id: int
    username: str
    email: str
    empresa: str
    status: str
    data_solicitacao: datetime
    data_decisao: Optional[datetime]
    motivo_rejeicao: Optional[str]

    class Config:
        from_attributes = True


class AprovarSolicitacaoRequest(BaseModel):
    solicitacao_id: int
    aprovar: bool = True
    motivo_rejeicao: Optional[str] = None


# ==================== LOGS ====================

class AccessLogResponse(BaseModel):
    id: int
    usuario_id: int
    username: Optional[str]
    acao: str
    data_hora: datetime
    ip_address: Optional[str]
    projeto_id: Optional[int]
    detalhes: Optional[dict]

    class Config:
        from_attributes = True


class FiltroLogsRequest(BaseModel):
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    usuario_id: Optional[int] = None
    acao: Optional[str] = None
    skip: int = 0
    limit: int = 100
