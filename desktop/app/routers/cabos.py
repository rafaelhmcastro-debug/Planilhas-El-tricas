import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, calculations
from ..database import get_db

router = APIRouter(prefix="/api/projetos/{projeto_id}/cabos", tags=["cabos"])


def _get_projeto(db, projeto_id):
    projeto = db.get(models.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")
    return projeto


def _validar_pontas(db, projeto_id, payload: schemas.CaboBase):
    de_ok = bool(payload.equipamento_de_id) ^ bool(payload.painel_de_id)
    para_ok = bool(payload.equipamento_para_id) ^ bool(payload.painel_para_id)
    if not de_ok or not para_ok:
        raise HTTPException(400, "Informe exatamente uma origem ('De') e um destino ('Para') — cada um pode ser um equipamento ou um painel.")
    for campo, modelo in (("equipamento_de_id", models.Equipamento), ("equipamento_para_id", models.Equipamento),
                          ("painel_de_id", models.PainelTransformador), ("painel_para_id", models.PainelTransformador)):
        _id = getattr(payload, campo)
        if _id and not db.query(modelo).filter(modelo.id == _id, modelo.projeto_id == projeto_id).first():
            raise HTTPException(400, f"Referência inválida em '{campo}' para este projeto.")
    if payload.painel_de_id and payload.painel_de_id == payload.painel_para_id:
        raise HTTPException(400, "Origem e destino não podem ser o mesmo painel.")
    if payload.equipamento_de_id and payload.equipamento_de_id == payload.equipamento_para_id:
        raise HTTPException(400, "Origem e destino não podem ser o mesmo equipamento.")


def _set_trechos(db, cabo, trechos_in):
    db.query(models.CaboTrecho).filter(models.CaboTrecho.cabo_id == cabo.id).delete()
    db.flush()
    for t in sorted(trechos_in, key=lambda x: x.ordem):
        infra = db.query(models.EletrodutoBandeja).filter(
            models.EletrodutoBandeja.id == t.eletroduto_bandeja_id, models.EletrodutoBandeja.projeto_id == cabo.projeto_id
        ).first()
        if not infra:
            raise HTTPException(400, f"Eletroduto/bandeja id={t.eletroduto_bandeja_id} inválido para este projeto.")
        db.add(models.CaboTrecho(cabo_id=cabo.id, eletroduto_bandeja_id=t.eletroduto_bandeja_id, ordem=t.ordem))
    db.flush()
    db.expire(cabo, ["trechos"])


@router.get("", response_model=list[schemas.CaboOut])
def listar(projeto_id: int, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    return db.query(models.Cabo).filter(models.Cabo.projeto_id == projeto_id).order_by(models.Cabo.tag).all()


@router.post("", response_model=schemas.CaboOut)
def criar(projeto_id: int, payload: schemas.CaboCreate, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    _validar_pontas(db, projeto_id, payload)
    if db.query(models.Cabo).filter(models.Cabo.projeto_id == projeto_id, models.Cabo.tag == payload.tag).first():
        raise HTTPException(400, "Já existe um cabo com essa TAG neste projeto.")

    dados = payload.model_dump(exclude={"trechos"})
    cabo = models.Cabo(projeto_id=projeto_id, **dados)
    cabo.secao_definida_manualmente = payload.catalogo_cabo_id is not None
    db.add(cabo)
    db.flush()
    _set_trechos(db, cabo, payload.trechos)
    calculations.recalcular_cabo(db, cabo)
    db.commit()
    db.refresh(cabo)
    return cabo


@router.put("/{cabo_id}", response_model=schemas.CaboOut)
def atualizar(projeto_id: int, cabo_id: int, payload: schemas.CaboCreate, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    cabo = db.query(models.Cabo).filter(models.Cabo.id == cabo_id, models.Cabo.projeto_id == projeto_id).first()
    if not cabo:
        raise HTTPException(404, "Cabo não encontrado.")
    _validar_pontas(db, projeto_id, payload)
    duplicado = db.query(models.Cabo).filter(
        models.Cabo.projeto_id == projeto_id, models.Cabo.tag == payload.tag, models.Cabo.id != cabo_id
    ).first()
    if duplicado:
        raise HTTPException(400, "Já existe um cabo com essa TAG neste projeto.")

    trechos_antigos = {t.eletroduto_bandeja_id for t in cabo.trechos}
    dados = payload.model_dump(exclude={"trechos"})
    for k, v in dados.items():
        setattr(cabo, k, v)
    # catálogo enviado explicitamente = escolha manual; vazio = volta à sugestão automática
    cabo.secao_definida_manualmente = payload.catalogo_cabo_id is not None
    db.flush()
    _set_trechos(db, cabo, payload.trechos)
    calculations.recalcular_cabo(db, cabo)
    # trechos removidos do percurso precisam ter a ocupação refeita
    novos = {t.eletroduto_bandeja_id for t in cabo.trechos}
    for infra_id in trechos_antigos - novos:
        infra = db.get(models.EletrodutoBandeja, infra_id)
        if infra:
            calculations.recalcular_ocupacao_trecho(db, infra)
    db.commit()
    db.refresh(cabo)
    return cabo


@router.delete("/{cabo_id}")
def remover(projeto_id: int, cabo_id: int, db: Session = Depends(get_db)):
    cabo = db.query(models.Cabo).filter(models.Cabo.id == cabo_id, models.Cabo.projeto_id == projeto_id).first()
    if not cabo:
        raise HTTPException(404, "Cabo não encontrado.")
    trechos_ids = [t.eletroduto_bandeja_id for t in cabo.trechos]
    db.delete(cabo)
    db.flush()
    for infra_id in trechos_ids:
        infra = db.get(models.EletrodutoBandeja, infra_id)
        if infra:
            calculations.recalcular_ocupacao_trecho(db, infra)
    db.commit()
    return {"ok": True}


@router.post("/recalcular-todos")
def recalcular_todos(projeto_id: int, db: Session = Depends(get_db)):
    _get_projeto(db, projeto_id)
    calculations.recalcular_paineis_projeto(db, projeto_id)
    calculations.recalcular_todos_cabos(db, projeto_id)
    db.commit()
    return {"ok": True}


@router.post("/{cabo_id}/recalcular", response_model=schemas.CaboOut)
def recalcular(projeto_id: int, cabo_id: int, db: Session = Depends(get_db)):
    cabo = db.query(models.Cabo).filter(models.Cabo.id == cabo_id, models.Cabo.projeto_id == projeto_id).first()
    if not cabo:
        raise HTTPException(404, "Cabo não encontrado.")
    calculations.recalcular_cabo(db, cabo)
    db.commit()
    db.refresh(cabo)
    return cabo


@router.get("/{cabo_id}/trechos")
def listar_trechos(projeto_id: int, cabo_id: int, db: Session = Depends(get_db)):
    cabo = db.query(models.Cabo).filter(models.Cabo.id == cabo_id, models.Cabo.projeto_id == projeto_id).first()
    if not cabo:
        raise HTTPException(404, "Cabo não encontrado.")
    return [
        {"eletroduto_bandeja_id": t.eletroduto_bandeja_id, "ordem": t.ordem, "tag": t.eletroduto_bandeja.tag}
        for t in sorted(cabo.trechos, key=lambda t: t.ordem)
    ]


@router.get("/{cabo_id}/memoria-calculo")
def memoria_calculo(projeto_id: int, cabo_id: int, db: Session = Depends(get_db)):
    cabo = db.query(models.Cabo).filter(models.Cabo.id == cabo_id, models.Cabo.projeto_id == projeto_id).first()
    if not cabo:
        raise HTTPException(404, "Cabo não encontrado.")
    memoria = json.loads(cabo.memoria_calculo_json) if cabo.memoria_calculo_json else {"passos": []}
    return {"cabo_tag": cabo.tag, "de": cabo.de_tag, "para": cabo.para_tag, **memoria}
