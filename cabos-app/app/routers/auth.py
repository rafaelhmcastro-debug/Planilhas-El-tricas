"""
Rotas de Autenticação
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models_auth import Usuario, SolicitacaoUsuario, AccessLog
from ..schemas_auth import (
    LoginRequest, LoginResponse, UsuarioResponse,
    CadastroRequest, CadastroResponse,
    SolicitacaoResponse
)
from ..utils_auth import (
    autenticar_usuario, criar_access_token, decodificar_token,
    obter_usuario_por_id, obter_usuario_por_username,
    obter_usuario_por_email, hash_senha
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


# ==================== DEPENDÊNCIAS ====================

def obter_usuario_atual(
    token: str = None,
    db: Session = Depends(get_db),
    request: Request = None
) -> Usuario:
    """
    Extrai usuário do token JWT
    Retorna None se token inválido ou usuário não existe
    """
    if not token:
        # Tentar pegar do header
        auth_header = request.headers.get("Authorization") if request else None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token não fornecido"
            )

    payload = decodificar_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )

    usuario = obter_usuario_por_id(db, payload["usuario_id"])
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado"
        )

    if not usuario.ativo or not usuario.aprovado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não ativo ou não aprovado"
        )

    return usuario


# ==================== LOGIN ====================

@router.post("/login", response_model=LoginResponse)
def login(
    dados: LoginRequest,
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Endpoint de login
    Retorna JWT token se credenciais corretas
    """
    usuario = autenticar_usuario(db, dados.username, dados.senha)

    if not usuario:
        # Registrar tentativa falha
        _registrar_log(db, None, "login_falha", None, request)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos"
        )

    # Registrar login bem-sucedido
    _registrar_log(db, usuario.id, "login", None, request)

    access_token = criar_access_token(usuario.id, usuario.username)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": UsuarioResponse.from_orm(usuario)
    }


@router.post("/logout")
def logout(
    usuario: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Registra logout do usuário"""
    _registrar_log(db, usuario.id, "logout", None, request)
    return {"mensagem": "Logout realizado com sucesso"}


# ==================== CADASTRO ====================

@router.post("/cadastro", response_model=CadastroResponse)
def cadastro(
    dados: CadastroRequest,
    db: Session = Depends(get_db),
):
    """
    Endpoint de cadastro
    Cria solicitação pendente de aprovação
    """
    # Validações
    if dados.senha != dados.confirmar_senha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senhas não conferem"
        )

    # Verificar se username já existe
    if obter_usuario_por_username(db, dados.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username já utilizado"
        )

    # Verificar se email já existe
    if obter_usuario_por_email(db, dados.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já utilizado"
        )

    # Verificar se já existe solicitação pendente
    solicitacao_existente = db.query(SolicitacaoUsuario).filter(
        (SolicitacaoUsuario.username == dados.username) |
        (SolicitacaoUsuario.email == dados.email)
    ).filter(
        SolicitacaoUsuario.status == "pendente"
    ).first()

    if solicitacao_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você já tem uma solicitação pendente"
        )

    # Criar solicitação
    solicitacao = SolicitacaoUsuario(
        username=dados.username,
        email=dados.email,
        empresa=dados.empresa,
        senha_hash=hash_senha(dados.senha),
        status="pendente"
    )

    db.add(solicitacao)
    db.commit()
    db.refresh(solicitacao)

    return {
        "id": solicitacao.id,
        "username": solicitacao.username,
        "email": solicitacao.email,
        "empresa": solicitacao.empresa,
        "status": "pendente",
        "data_solicitacao": solicitacao.data_solicitacao
    }


# ==================== PERFIL ====================

@router.get("/perfil", response_model=UsuarioResponse)
def obter_perfil(
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Retorna dados do usuário logado"""
    return usuario


# ==================== UTILITÁRIOS ====================

def _obter_ip(request: Request) -> str:
    """Extrai IP do cliente"""
    if request:
        return request.client.host if request.client else None
    return None


def _registrar_log(
    db: Session,
    usuario_id: int,
    acao: str,
    projeto_id: int = None,
    request: Request = None
):
    """Registra ação do usuário em access_logs"""
    try:
        log = AccessLog(
            usuario_id=usuario_id,
            acao=acao,
            projeto_id=projeto_id,
            ip_address=_obter_ip(request),
            data_hora=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        # Não deixar log quebrar a aplicação
        print(f"Erro ao registrar log: {e}")
        pass
