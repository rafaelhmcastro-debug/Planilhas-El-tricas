from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..risco5419 import ng, schemas
from ..risco5419.modelos import AnaliseRisco, MunicipioNG

router = APIRouter(tags=["risco5419"])


def _get_projeto(db, projeto_id):
    projeto = db.get(models.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")
    return projeto


# ---------------- Consulta de NG (Anexo F) ----------------

@router.get("/api/risco5419/ng/ufs", response_model=list[str])
def listar_ufs(db: Session = Depends(get_db)):
    return ng.listar_ufs(db)


@router.get("/api/risco5419/ng/municipios", response_model=list[schemas.MunicipioNGOut])
def buscar_municipios(uf: str, q: str = "", db: Session = Depends(get_db)):
    return ng.buscar_municipios(db, uf, q)


# ---------------- Análises de risco (por projeto) ----------------

@router.get("/api/projetos/{projeto_id}/risco5419/analises", response_model=list[schemas.AnaliseRiscoOut])
def listar_analises(projeto_id: int, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    return (
        db.query(AnaliseRisco)
        .filter(AnaliseRisco.projeto_id == projeto_id)
        .order_by(AnaliseRisco.id.desc())
        .all()
    )


@router.post("/api/projetos/{projeto_id}/risco5419/analises", response_model=schemas.AnaliseRiscoOut)
def criar_analise(projeto_id: int, payload: schemas.AnaliseRiscoCreate, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    try:
        if payload.ng_modo == "manual":
            resolvido = ng.resolver_ng_manual(payload.ng_valor_manual, payload.ng_fonte_manual)
        else:
            resolvido = ng.resolver_ng_municipio(db, payload.ng_municipio, payload.ng_uf)
    except ValueError as e:
        raise HTTPException(422, str(e))

    analise = AnaliseRisco(projeto_id=projeto_id, tag=payload.tag, **resolvido)
    db.add(analise)
    db.commit()
    db.refresh(analise)
    return analise


@router.get("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}", response_model=schemas.AnaliseRiscoOut)
def obter_analise(projeto_id: int, analise_id: int, db: Session = Depends(get_db)):
    analise = db.get(AnaliseRisco, analise_id)
    if not analise or analise.projeto_id != projeto_id:
        raise HTTPException(404, "Análise não encontrada.")
    return analise


@router.delete("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}")
def remover_analise(projeto_id: int, analise_id: int, db: Session = Depends(get_db)):
    analise = db.get(AnaliseRisco, analise_id)
    if not analise or analise.projeto_id != projeto_id:
        raise HTTPException(404, "Análise não encontrada.")
    db.delete(analise)
    db.commit()
    return {"ok": True}
