from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, calculations
from ..database import get_db

router = APIRouter(prefix="/api/projetos/{projeto_id}/eletrodutos-bandejas", tags=["eletrodutos-bandejas"])


def _get_projeto(db, projeto_id):
    projeto = db.get(models.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")
    return projeto


def _aplicar_catalogo(db: Session, infra: models.EletrodutoBandeja):
    if infra.catalogo_infraestrutura_id:
        item = db.get(models.CatalogoInfraestrutura, infra.catalogo_infraestrutura_id)
        if item:
            infra.diametro_nominal_mm = item.diametro_nominal_mm
            infra.parede_mm = item.parede_mm
            infra.area_util_mm2 = item.area_util_mm2
            infra.largura_util_mm = item.largura_util_mm
    else:
        infra.diametro_nominal_mm = None
        infra.parede_mm = None
        infra.area_util_mm2 = None
        infra.largura_util_mm = None


@router.get("", response_model=list[schemas.InfraOut])
def listar(projeto_id: int, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    return db.query(models.EletrodutoBandeja).filter(models.EletrodutoBandeja.projeto_id == projeto_id).order_by(models.EletrodutoBandeja.tag).all()


@router.post("", response_model=schemas.InfraOut)
def criar(projeto_id: int, payload: schemas.InfraCreate, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    if db.query(models.EletrodutoBandeja).filter(
        models.EletrodutoBandeja.projeto_id == projeto_id, models.EletrodutoBandeja.tag == payload.tag
    ).first():
        raise HTTPException(400, "Já existe um item com essa TAG neste projeto.")
    infra = models.EletrodutoBandeja(projeto_id=projeto_id, **payload.model_dump())
    _aplicar_catalogo(db, infra)
    db.add(infra)
    db.flush()
    calculations.recalcular_ocupacao_trecho(db, infra)
    db.commit()
    db.refresh(infra)
    return infra


@router.put("/{infra_id}", response_model=schemas.InfraOut)
def atualizar(projeto_id: int, infra_id: int, payload: schemas.InfraCreate, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    infra = db.query(models.EletrodutoBandeja).filter(
        models.EletrodutoBandeja.id == infra_id, models.EletrodutoBandeja.projeto_id == projeto_id
    ).first()
    if not infra:
        raise HTTPException(404, "Item não encontrado.")
    duplicado = db.query(models.EletrodutoBandeja).filter(
        models.EletrodutoBandeja.projeto_id == projeto_id, models.EletrodutoBandeja.tag == payload.tag,
        models.EletrodutoBandeja.id != infra_id,
    ).first()
    if duplicado:
        raise HTTPException(400, "Já existe um item com essa TAG neste projeto.")
    for k, v in payload.model_dump().items():
        setattr(infra, k, v)
    _aplicar_catalogo(db, infra)
    db.flush()
    calculations.recalcular_ocupacao_trecho(db, infra)

    # comprimento/tipo afetam distância e agrupamento dos cabos que passam por aqui
    cabos_afetados = db.query(models.Cabo).join(models.CaboTrecho).filter(
        models.CaboTrecho.eletroduto_bandeja_id == infra_id
    ).all()
    for cabo in cabos_afetados:
        calculations.recalcular_cabo(db, cabo)

    db.commit()
    db.refresh(infra)
    return infra


@router.delete("/{infra_id}")
def remover(projeto_id: int, infra_id: int, db: Session = Depends(get_db)):
    infra = db.query(models.EletrodutoBandeja).filter(
        models.EletrodutoBandeja.id == infra_id, models.EletrodutoBandeja.projeto_id == projeto_id
    ).first()
    if not infra:
        raise HTTPException(404, "Item não encontrado.")
    em_uso = db.query(models.CaboTrecho).filter(models.CaboTrecho.eletroduto_bandeja_id == infra_id).count()
    if em_uso:
        raise HTTPException(409, f"Item usado no percurso de {em_uso} cabo(s). Remova-o dos cabos antes de excluir.")
    db.delete(infra)
    db.commit()
    return {"ok": True}


@router.get("/{infra_id}/ocupacao")
def ocupacao(projeto_id: int, infra_id: int, db: Session = Depends(get_db)):
    infra = db.query(models.EletrodutoBandeja).filter(
        models.EletrodutoBandeja.id == infra_id, models.EletrodutoBandeja.projeto_id == projeto_id
    ).first()
    if not infra:
        raise HTTPException(404, "Item não encontrado.")
    return calculations.calcular_ocupacao(db, infra)
