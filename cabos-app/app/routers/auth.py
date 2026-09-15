from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models_auth import Usuario, SolicitacaoUsuario, AccessLog
from ..schemas_auth import (
    LoginRequest, LoginResponse, CadastroRequest, CadastroResponse,
    UsuarioResponse, AlterarSenhaRequest
)
from ..utils_auth import (
    criar_access_token, decodificar_token, autenticar_usuario,
    obter_usuario_por_username, obter_usuario_por_email, criar_usuario,
    hash_senha, verificar_senha
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def obter_usuario_atual(
    request: Request,
    db: Session = Depends(get_db)
) -> Usuario:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não fornecido"
        )

    token = auth_header.split(" ")[1]
    dados = decodificar_token(token)

    if not dados:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )

    usuario = db.query(Usuario).filter(Usuario.id == int(dados["usuario_id"])).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado"
        )

    if not usuario.ativo or not usuario.aprovado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta não ativa ou não aprovada"
        )

    return usuario


def _registrar_log(
    db: Session,
    usuario_id: int,
    acao: str,
    ip_address: str,
    projeto_id: int = None,
    detalhes: dict = None
):
    log = AccessLog(
        usuario_id=usuario_id,
        ip_address=ip_address,
        acao=acao,
        projeto_id=projeto_id,
        detalhes=detalhes,
        data_hora=datetime.utcnow()
    )
    db.add(log)
    db.commit()


@router.post("/login", response_model=LoginResponse)
def fazer_login(
    dados: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    usuario = autenticar_usuario(db, dados.username, dados.senha)

    if not usuario:
        _registrar_log(
            db,
            usuario_id=None,
            acao="login_falha",
            ip_address=request.client.host if request.client else None,
            detalhes={"username": dados.username}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos"
        )

    token = criar_access_token(usuario.id, usuario.username)

    _registrar_log(
        db,
        usuario_id=usuario.id,
        acao="login",
        ip_address=request.client.host if request.client else None
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": UsuarioResponse.from_orm(usuario)
    }


@router.post("/logout")
def fazer_logout(
    usuario: Usuario = Depends(obter_usuario_atual),
    request: Request = None,
    db: Session = Depends(get_db)
):
    _registrar_log(
        db,
        usuario_id=usuario.id,
        acao="logout",
        ip_address=request.client.host if request.client else None
    )
    return {"mensagem": "Logout realizado com sucesso"}


@router.post("/cadastro", response_model=CadastroResponse)
def fazer_cadastro(
    dados: CadastroRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    if dados.senha != dados.confirmar_senha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="As senhas não conferem"
        )

    usuario_existente = obter_usuario_por_username(db, dados.username)
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username já existe"
        )

    email_existente = obter_usuario_por_email(db, dados.email)
    if email_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já está cadastrado"
        )

    solicitacao_existente = db.query(SolicitacaoUsuario).filter(
        SolicitacaoUsuario.username == dados.username,
        SolicitacaoUsuario.status == "pendente"
    ).first()

    if solicitacao_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma solicitação de cadastro pendente para este username"
        )

    senha_hash = hash_senha(dados.senha)
    solicitacao = SolicitacaoUsuario(
        username=dados.username,
        email=dados.email,
        empresa=dados.empresa,
        senha_hash=senha_hash,
        status="pendente",
        data_solicitacao=datetime.utcnow()
    )

    db.add(solicitacao)
    db.commit()
    db.refresh(solicitacao)

    _registrar_log(
        db,
        usuario_id=None,
        acao="cadastro_solicitado",
        ip_address=request.client.host if request.client else None,
        detalhes={"username": dados.username, "email": dados.email}
    )

    return {
        "id": solicitacao.id,
        "username": solicitacao.username,
        "email": solicitacao.email,
        "empresa": solicitacao.empresa,
        "status": solicitacao.status,
        "data_solicitacao": solicitacao.data_solicitacao
    }


@router.get("/perfil", response_model=UsuarioResponse)
def obter_perfil(usuario: Usuario = Depends(obter_usuario_atual)):
    return UsuarioResponse.from_orm(usuario)


@router.post("/alterar-senha")
def alterar_senha(
    dados: AlterarSenhaRequest,
    usuario: Usuario = Depends(obter_usuario_atual),
    request: Request = None,
    db: Session = Depends(get_db)
):
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta"
        )

    usuario.senha_hash = hash_senha(dados.nova_senha)
    db.commit()

    _registrar_log(
        db,
        usuario_id=usuario.id,
        acao="alterar_senha",
        ip_address=request.client.host if request.client else None
    )

    return {"mensagem": "Senha alterada com sucesso"}
