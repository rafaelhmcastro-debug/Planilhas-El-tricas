from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from ..database import get_db
from ..models_auth import Usuario, SolicitacaoUsuario, AccessLog
from ..schemas_auth import SolicitacaoResponse, UsuarioAdmin, AccessLogResponse, AprovarSolicitacaoRequest
from ..routers.auth import obter_usuario_atual
from ..utils_auth import criar_usuario, hash_senha

router = APIRouter(prefix="/api/admin", tags=["admin"])


def verificar_admin(usuario: Usuario = Depends(obter_usuario_atual)) -> Usuario:
    if usuario.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso apenas para administradores"
        )
    return usuario


@router.get("/dashboard")
def obter_dashboard(
    admin: Usuario = Depends(verificar_admin),
    db: Session = Depends(get_db)
):
    total_usuarios = db.query(Usuario).count()
    total_acessos = db.query(AccessLog).count()

    usuarios_online = db.query(func.count(distinct(AccessLog.usuario_id))).filter(
        AccessLog.acao.in_(["login", "logout"]),
        AccessLog.data_hora >= datetime.utcnow() - timedelta(minutes=15)
    ).scalar() or 0

    solicitacoes_pendentes = db.query(SolicitacaoUsuario).filter(
        SolicitacaoUsuario.status == "pendente"
    ).count()

    return {
        "total_usuarios": total_usuarios,
        "total_acessos": total_acessos,
        "usuarios_online": usuarios_online,
        "solicitacoes_pendentes": solicitacoes_pendentes
    }


@router.get("/solicitacoes", response_model=List[SolicitacaoResponse])
def listar_solicitacoes(
    admin: Usuario = Depends(verificar_admin),
    db: Session = Depends(get_db),
    status_filtro: str = "pendente"
):
    solicitacoes = db.query(SolicitacaoUsuario).filter(
        SolicitacaoUsuario.status == status_filtro
    ).order_by(SolicitacaoUsuario.data_solicitacao.desc()).all()

    return solicitacoes


@router.post("/solicitacoes/aprovar")
def aprovar_solicitacao(
    dados: AprovarSolicitacaoRequest,
    admin: Usuario = Depends(verificar_admin),
    db: Session = Depends(get_db)
):
    solicitacao = db.query(SolicitacaoUsuario).filter(
        SolicitacaoUsuario.id == dados.solicitacao_id
    ).first()

    if not solicitacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitação não encontrada"
        )

    if solicitacao.status != "pendente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solicitação já foi processada"
        )

    if dados.aprovar:
        usuario = criar_usuario(
            db=db,
            username=solicitacao.username,
            email=solicitacao.email,
            empresa=solicitacao.empresa,
            senha=solicitacao.senha_hash,
            role="user",
            ativo=True,
            aprovado=True
        )
        usuario.senha_hash = solicitacao.senha_hash

        solicitacao.status = "aprovado"
        solicitacao.data_decisao = datetime.utcnow()
        solicitacao.decidido_por_id = admin.id
        solicitacao.usuario_id = usuario.id

        db.commit()

        return {
            "mensagem": f"Usuário {solicitacao.username} aprovado com sucesso",
            "usuario_id": usuario.id
        }
    else:
        solicitacao.status = "rejeitado"
        solicitacao.data_decisao = datetime.utcnow()
        solicitacao.decidido_por_id = admin.id
        solicitacao.motivo_rejeicao = dados.motivo_rejeicao

        db.commit()

        return {
            "mensagem": f"Solicitação de {solicitacao.username} rejeitada"
        }


@router.get("/usuarios", response_model=List[UsuarioAdmin])
def listar_usuarios(
    admin: Usuario = Depends(verificar_admin),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    usuarios = db.query(Usuario).offset(skip).limit(limit).all()
    return usuarios


@router.post("/usuarios/{usuario_id}/desativar")
def desativar_usuario(
    usuario_id: int,
    admin: Usuario = Depends(verificar_admin),
    db: Session = Depends(get_db)
):
    if usuario_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode desativar a si mesmo"
        )

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    usuario.ativo = False
    db.commit()

    return {"mensagem": f"Usuário {usuario.username} desativado"}


@router.get("/logs", response_model=List[AccessLogResponse])
def listar_logs(
    admin: Usuario = Depends(verificar_admin),
    db: Session = Depends(get_db),
    usuario_id: int = None,
    acao: str = None,
    skip: int = 0,
    limit: int = 100
):
    query = db.query(AccessLog)

    if usuario_id:
        query = query.filter(AccessLog.usuario_id == usuario_id)

    if acao:
        query = query.filter(AccessLog.acao == acao)

    logs = query.order_by(AccessLog.data_hora.desc()).offset(skip).limit(limit).all()

    resultado = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "usuario_id": log.usuario_id,
            "username": log.usuario.username if log.usuario else None,
            "acao": log.acao,
            "data_hora": log.data_hora,
            "ip_address": log.ip_address,
            "projeto_id": log.projeto_id,
            "detalhes": log.detalhes
        }
        resultado.append(log_dict)

    return resultado


@router.get("/logs/resumo")
def resumo_logs(
    admin: Usuario = Depends(verificar_admin),
    db: Session = Depends(get_db),
    dias: int = 30
):
    data_limite = datetime.utcnow() - timedelta(days=dias)

    acessos_por_dia = db.query(
        func.date(AccessLog.data_hora).label("data"),
        func.count(AccessLog.id).label("total")
    ).filter(
        AccessLog.data_hora >= data_limite
    ).group_by(
        func.date(AccessLog.data_hora)
    ).all()

    acoes_frequentes = db.query(
        AccessLog.acao,
        func.count(AccessLog.id).label("total")
    ).filter(
        AccessLog.data_hora >= data_limite
    ).group_by(
        AccessLog.acao
    ).all()

    return {
        "acessos_por_dia": [
            {"data": str(row[0]), "total": row[1]}
            for row in acessos_por_dia
        ],
        "acoes_frequentes": [
            {"acao": row[0], "total": row[1]}
            for row in acoes_frequentes
        ]
    }
