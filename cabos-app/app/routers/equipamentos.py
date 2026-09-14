from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, calculations
from ..database import get_db

router = APIRouter(prefix="/api/projetos/{projeto_id}/equipamentos", tags=["equipamentos"])


def _get_projeto(db, projeto_id):
    projeto = db.get(models.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")
    return projeto


@router.get("", response_model=list[schemas.EquipamentoOut])
def listar(projeto_id: int, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    return db.query(models.Equipamento).filter(models.Equipamento.projeto_id == projeto_id).order_by(models.Equipamento.tag).all()


def _pos_salvar(db, projeto_id, equip):
    if equip.painel_transformador_tag:
        calculations.garantir_painel(db, projeto_id, equip.painel_transformador_tag)
    calculations.recalcular_equipamento(db, equip)
    calculations.recalcular_cabos_da_carga(db, projeto_id, equipamento_id=equip.id)
    # painéis a montante mudaram de demanda → cabos que alimentam painéis também
    for p in db.query(models.PainelTransformador).filter(models.PainelTransformador.projeto_id == projeto_id).all():
        calculations.recalcular_cabos_da_carga(db, projeto_id, painel_id=p.id)


@router.post("", response_model=schemas.EquipamentoOut)
def criar(projeto_id: int, payload: schemas.EquipamentoCreate, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    existente = db.query(models.Equipamento).filter(
        models.Equipamento.projeto_id == projeto_id, models.Equipamento.tag == payload.tag
    ).first()
    if existente:
        raise HTTPException(400, "Já existe um equipamento com essa TAG neste projeto.")
    equip = models.Equipamento(projeto_id=projeto_id, **payload.model_dump())
    db.add(equip)
    db.flush()
    _pos_salvar(db, projeto_id, equip)
    db.commit()
    db.refresh(equip)
    return equip


@router.put("/{equipamento_id}", response_model=schemas.EquipamentoOut)
def atualizar(projeto_id: int, equipamento_id: int, payload: schemas.EquipamentoCreate, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    equip = db.query(models.Equipamento).filter(
        models.Equipamento.id == equipamento_id, models.Equipamento.projeto_id == projeto_id
    ).first()
    if not equip:
        raise HTTPException(404, "Equipamento não encontrado.")
    duplicado = db.query(models.Equipamento).filter(
        models.Equipamento.projeto_id == projeto_id, models.Equipamento.tag == payload.tag,
        models.Equipamento.id != equipamento_id,
    ).first()
    if duplicado:
        raise HTTPException(400, "Já existe um equipamento com essa TAG neste projeto.")
    for k, v in payload.model_dump().items():
        setattr(equip, k, v)
    db.flush()
    _pos_salvar(db, projeto_id, equip)
    db.commit()
    db.refresh(equip)
    return equip


@router.delete("/{equipamento_id}")
def remover(projeto_id: int, equipamento_id: int, force: bool = False, db: Session = Depends(get_db)):
    equip = db.query(models.Equipamento).filter(
        models.Equipamento.id == equipamento_id, models.Equipamento.projeto_id == projeto_id
    ).first()
    if not equip:
        raise HTTPException(404, "Equipamento não encontrado.")
    cabos = db.query(models.Cabo).filter(
        models.Cabo.projeto_id == projeto_id,
        (models.Cabo.equipamento_de_id == equipamento_id) | (models.Cabo.equipamento_para_id == equipamento_id),
    ).all()
    if cabos and not force:
        raise HTTPException(409, f"Equipamento referenciado por {len(cabos)} cabo(s). Confirme a exclusão com force=true.")
    for c in cabos:
        db.delete(c)
    db.delete(equip)
    db.flush()
    calculations.recalcular_paineis_projeto(db, projeto_id)
    db.commit()
    return {"ok": True}


@router.post("/{equipamento_id}/duplicar", response_model=schemas.EquipamentoOut)
def duplicar(projeto_id: int, equipamento_id: int, nova_tag: str, db: Session = Depends(get_db)):
    original = db.query(models.Equipamento).filter(
        models.Equipamento.id == equipamento_id, models.Equipamento.projeto_id == projeto_id
    ).first()
    if not original:
        raise HTTPException(404, "Equipamento não encontrado.")
    if db.query(models.Equipamento).filter(models.Equipamento.projeto_id == projeto_id, models.Equipamento.tag == nova_tag).first():
        raise HTTPException(400, "Já existe um equipamento com essa TAG neste projeto.")
    dados = {c.name: getattr(original, c.name) for c in models.Equipamento.__table__.columns if c.name not in ("id", "tag")}
    novo = models.Equipamento(tag=nova_tag, **dados)
    db.add(novo)
    db.flush()
    _pos_salvar(db, projeto_id, novo)
    db.commit()
    db.refresh(novo)
    return novo
