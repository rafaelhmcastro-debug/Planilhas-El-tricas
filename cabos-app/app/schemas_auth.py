from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    senha: str = Field(..., min_length=6)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    usuario: 'UsuarioResponse'


class CadastroRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    email: str = Field(..., min_length=5)
    empresa: str = Field(..., min_length=1, max_length=100)
    senha: str = Field(..., min_length=8)
    confirmar_senha: str = Field(..., min_length=8)


class CadastroResponse(BaseModel):
    id: int
    username: str
    email: str
    empresa: str
    status: str
    data_solicitacao: datetime

    class Config:
        from_attributes = True


class UsuarioResponse(BaseModel):
    id: int
    username: str
    email: str
    empresa: str
    role: str
    ativo: bool
    aprovado: bool
    data_criacao: datetime
    data_aprovacao: Optional[datetime] = None

    class Config:
        from_attributes = True


class UsuarioAdmin(BaseModel):
    id: int
    username: str
    email: str
    empresa: str
    role: str
    ativo: bool
    aprovado: bool
    data_criacao: datetime
    data_aprovacao: Optional[datetime] = None

    class Config:
        from_attributes = True


class SolicitacaoResponse(BaseModel):
    id: int
    username: str
    email: str
    empresa: str
    status: str
    data_solicitacao: datetime
    data_decisao: Optional[datetime] = None

    class Config:
        from_attributes = True


class AprovarSolicitacaoRequest(BaseModel):
    solicitacao_id: int
    aprovar: bool
    motivo_rejeicao: Optional[str] = None


class AccessLogResponse(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    username: Optional[str] = None
    acao: str
    data_hora: datetime
    ip_address: Optional[str] = None
    projeto_id: Optional[int] = None
    detalhes: Optional[dict] = None

    class Config:
        from_attributes = True


class AlterarSenhaRequest(BaseModel):
    senha_atual: str = Field(..., min_length=6)
    nova_senha: str = Field(..., min_length=8)
