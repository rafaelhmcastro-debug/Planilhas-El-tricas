from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, calculations
from ..database import get_db

router = APIRouter(prefix="/api/projetos/{projeto_id}/paineis", tags=["paineis"])


def _get(db, projeto_id, painel_id):
    painel = db.query(models.PainelTransformador).filter(
        models.PainelTransformador.id == painel_id, models.PainelTransformador.projeto_id == projeto_id
    ).first()
    if not painel:
        raise HTTPException(404, "Painel não encontrado.")
    return painel


def _recalcular_tudo(db, projeto_id):
    calculations.recalcular_paineis_projeto(db, projeto_id)
    for p in db.query(models.PainelTransformador).filter(models.PainelTransformador.projeto_id == projeto_id).all():
        calculations.recalcular_cabos_da_carga(db, projeto_id, painel_id=p.id)


@router.get("", response_model=list[schemas.PainelOut])
def listar(projeto_id: int, db: Session = Depends(get_db)):
    return db.query(models.PainelTransformador).filter(models.PainelTransformador.projeto_id == projeto_id).order_by(models.PainelTransformador.tag).all()


@router.get("/arvore")
def arvore(projeto_id: int, db: Session = Depends(get_db)):
    """Hierarquia dos painéis (TOP → jusante) com os equipamentos de cada um."""
    paineis = db.query(models.PainelTransformador).filter(models.PainelTransformador.projeto_id == projeto_id).order_by(models.PainelTransformador.tag).all()
    equipamentos = db.query(models.Equipamento).filter(models.Equipamento.projeto_id == projeto_id).order_by(models.Equipamento.tag).all()
    por_painel = {}
    for e in equipamentos:
        if e.painel_transformador_tag:
            por_painel.setdefault(e.painel_transformador_tag.strip(), []).append(e)
    tags = {p.tag for p in paineis}

    def no(p, visitados):
        visitados = visitados | {p.tag}
        filhos = [x for x in paineis if (x.painel_alimentador_tag or "").strip() == p.tag and x.tag not in visitados]
        return {
            "painel": schemas.PainelOut.model_validate(p).model_dump(),
            "equipamentos": [schemas.EquipamentoOut.model_validate(e).model_dump() for e in por_painel.get(p.tag, [])],
            "filhos": [no(f, visitados) for f in filhos],
        }

    raizes = [p for p in paineis if not (p.painel_alimentador_tag or "").strip() or (p.painel_alimentador_tag or "").strip() not in tags]
    return [no(p, set()) for p in raizes]


@router.post("", response_model=schemas.PainelOut)
def criar(projeto_id: int, payload: schemas.PainelCreate, db: Session = Depends(get_db)):
    if db.query(models.PainelTransformador).filter(models.PainelTransformador.projeto_id == projeto_id, models.PainelTransformador.tag == payload.tag).first():
        raise HTTPException(400, "Já existe um painel com essa TAG neste projeto.")
    painel = models.PainelTransformador(projeto_id=projeto_id, **payload.model_dump())
    db.add(painel)
    db.flush()
    if painel.painel_alimentador_tag:
        calculations.garantir_painel(db, projeto_id, painel.painel_alimentador_tag)
    _recalcular_tudo(db, projeto_id)
    db.commit()
    db.refresh(painel)
    return painel


@router.get("/{painel_id}/equipamentos", response_model=list[schemas.EquipamentoOut])
def equipamentos_do_painel(projeto_id: int, painel_id: int, db: Session = Depends(get_db)):
    painel = _get(db, projeto_id, painel_id)
    return db.query(models.Equipamento).filter(
        models.Equipamento.projeto_id == projeto_id, models.Equipamento.painel_transformador_tag == painel.tag
    ).order_by(models.Equipamento.tag).all()


@router.put("/{painel_id}", response_model=schemas.PainelOut)
def atualizar(projeto_id: int, painel_id: int, payload: schemas.PainelUpdate, db: Session = Depends(get_db)):
    painel = _get(db, projeto_id, painel_id)
    dados = payload.model_dump(exclude_unset=True)
    tag_antiga = painel.tag
    if "tag" in dados and dados["tag"] != tag_antiga:
        if db.query(models.PainelTransformador).filter(models.PainelTransformador.projeto_id == projeto_id, models.PainelTransformador.tag == dados["tag"]).first():
            raise HTTPException(400, "Já existe um painel com essa TAG neste projeto.")
        # propaga a nova TAG para equipamentos e painéis filhos
        db.query(models.Equipamento).filter(models.Equipamento.projeto_id == projeto_id, models.Equipamento.painel_transformador_tag == tag_antiga).update({"painel_transformador_tag": dados["tag"]})
        db.query(models.PainelTransformador).filter(models.PainelTransformador.projeto_id == projeto_id, models.PainelTransformador.painel_alimentador_tag == tag_antiga).update({"painel_alimentador_tag": dados["tag"]})
    if "painel_alimentador_tag" in dados and dados["painel_alimentador_tag"] and dados["painel_alimentador_tag"].strip() == (dados.get("tag") or tag_antiga):
        raise HTTPException(400, "Um painel não pode alimentar a si mesmo.")
    for k, v in dados.items():
        setattr(painel, k, v)
    db.flush()
    if painel.painel_alimentador_tag:
        calculations.garantir_painel(db, projeto_id, painel.painel_alimentador_tag)
    _recalcular_tudo(db, projeto_id)
    db.commit()
    db.refresh(painel)
    return painel


@router.delete("/{painel_id}")
def remover(projeto_id: int, painel_id: int, db: Session = Depends(get_db)):
    painel = _get(db, projeto_id, painel_id)
    em_uso = db.query(models.Equipamento).filter(
        models.Equipamento.projeto_id == projeto_id, models.Equipamento.painel_transformador_tag == painel.tag
    ).count()
    filhos = db.query(models.PainelTransformador).filter(
        models.PainelTransformador.projeto_id == projeto_id, models.PainelTransformador.painel_alimentador_tag == painel.tag
    ).count()
    cabos = db.query(models.Cabo).filter(
        models.Cabo.projeto_id == projeto_id, (models.Cabo.painel_de_id == painel_id) | (models.Cabo.painel_para_id == painel_id)
    ).count()
    if em_uso or filhos or cabos:
        raise HTTPException(409, f"Painel referenciado por {em_uso} equipamento(s), {filhos} painel(is) a jusante e {cabos} cabo(s). Remova essas referências antes de excluir.")
    db.delete(painel)
    db.flush()
    _recalcular_tudo(db, projeto_id)
    db.commit()
    return {"ok": True}
