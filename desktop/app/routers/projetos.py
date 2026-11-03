from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/projetos", tags=["projetos"])


@router.get("", response_model=list[schemas.ProjetoOut])
def listar(db: Session = Depends(get_db)):
    return db.query(models.Projeto).order_by(models.Projeto.id.desc()).all()


@router.post("", response_model=schemas.ProjetoOut)
def criar(payload: schemas.ProjetoCreate, db: Session = Depends(get_db)):
    if db.query(models.Projeto).filter(models.Projeto.numero_projeto == payload.numero_projeto).first():
        raise HTTPException(400, "Já existe um projeto com esse número.")
    projeto = models.Projeto(**payload.model_dump())
    db.add(projeto)
    db.commit()
    db.refresh(projeto)
    return projeto


@router.get("/{projeto_id}", response_model=schemas.ProjetoOut)
def obter(projeto_id: int, db: Session = Depends(get_db)):
    projeto = db.get(models.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")
    return projeto


@router.put("/{projeto_id}", response_model=schemas.ProjetoOut)
def atualizar(projeto_id: int, payload: schemas.ProjetoCreate, db: Session = Depends(get_db)):
    projeto = db.get(models.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")
    duplicado = db.query(models.Projeto).filter(
        models.Projeto.numero_projeto == payload.numero_projeto, models.Projeto.id != projeto_id
    ).first()
    if duplicado:
        raise HTTPException(400, "Já existe um projeto com esse número.")
    for k, v in payload.model_dump().items():
        setattr(projeto, k, v)
    db.commit()
    db.refresh(projeto)
    return projeto


@router.delete("/{projeto_id}")
def remover(projeto_id: int, db: Session = Depends(get_db)):
    projeto = db.get(models.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")
    db.delete(projeto)
    db.commit()
    return {"ok": True}
