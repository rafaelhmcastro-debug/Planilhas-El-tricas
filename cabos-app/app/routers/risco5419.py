import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models
from ..database import get_db
from ..risco5419 import ng, schemas, tabelas, riscos
from ..risco5419.modelos import (
    AnaliseRisco, MunicipioNG, Estrutura, ZonaEstudo, LinhaEletrica, TrechoLinha,
    MedidasProtecao, ResultadoRisco,
)

router = APIRouter(tags=["risco5419"])


def _get_projeto(db, projeto_id):
    projeto = db.get(models.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")
    return projeto


def _get_analise(db, projeto_id, analise_id):
    analise = db.get(AnaliseRisco, analise_id)
    if not analise or analise.projeto_id != projeto_id:
        raise HTTPException(404, "Análise não encontrada.")
    return analise


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
    return _get_analise(db, projeto_id, analise_id)


@router.delete("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}")
def remover_analise(projeto_id: int, analise_id: int, db: Session = Depends(get_db)):
    analise = _get_analise(db, projeto_id, analise_id)
    db.delete(analise)
    db.commit()
    return {"ok": True}


# ---------------- Estrutura (1:1) ----------------

@router.put("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}/estrutura", response_model=schemas.EstruturaOut)
def salvar_estrutura(projeto_id: int, analise_id: int, payload: schemas.EstruturaIn, db: Session = Depends(get_db)):
    analise = _get_analise(db, projeto_id, analise_id)
    try:
        tabelas.valor("anexo_a_tabela_a1_cd", payload.fator_localizacao)
        tabelas.valor("anexo_c_tabela_c7_rs", payload.tipo_construcao)
    except tabelas.ValorNaoDisponivel as e:
        raise HTTPException(422, str(e))

    estrutura = analise.estrutura or Estrutura(analise_id=analise_id)
    for campo, valor in payload.model_dump().items():
        setattr(estrutura, campo, valor)
    db.add(estrutura)
    db.commit()
    db.refresh(estrutura)
    return estrutura


# ---------------- Zonas de estudo ----------------

@router.get("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}/zonas", response_model=list[schemas.ZonaEstudoOut])
def listar_zonas(projeto_id: int, analise_id: int, db: Session = Depends(get_db)):
    _get_analise(db, projeto_id, analise_id)
    return db.query(ZonaEstudo).filter(ZonaEstudo.analise_id == analise_id).order_by(ZonaEstudo.id).all()


@router.post("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}/zonas", response_model=schemas.ZonaEstudoOut)
def criar_zona(projeto_id: int, analise_id: int, payload: schemas.ZonaEstudoIn, db: Session = Depends(get_db)):
    _get_analise(db, projeto_id, analise_id)
    try:
        for tabela, chave in [
            ("anexo_c_tabela_c3_rt_piso", payload.tipo_piso),
            ("anexo_c_tabela_c4_rp", payload.providencias_incendio),
            ("anexo_c_tabela_c5_rf", payload.risco_incendio),
            ("anexo_c_tabela_c6_hz", payload.perigo_especial),
        ]:
            tabelas.valor(tabela, chave)
        tabelas.valor_grupo("anexo_c_tabela_c2_perdas_r1", "LF", payload.categoria_dano_fisico_lf)
        tabelas.valor_grupo("anexo_c_tabela_c2_perdas_r1", "LO", payload.categoria_falha_sistema_lo)
    except tabelas.ValorNaoDisponivel as e:
        raise HTTPException(422, str(e))

    zona = ZonaEstudo(analise_id=analise_id, **payload.model_dump())
    db.add(zona)
    db.commit()
    db.refresh(zona)
    return zona


@router.delete("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}/zonas/{zona_id}")
def remover_zona(projeto_id: int, analise_id: int, zona_id: int, db: Session = Depends(get_db)):
    _get_analise(db, projeto_id, analise_id)
    zona = db.get(ZonaEstudo, zona_id)
    if not zona or zona.analise_id != analise_id:
        raise HTTPException(404, "Zona não encontrada.")
    db.delete(zona)
    db.commit()
    return {"ok": True}


# ---------------- Linhas elétricas ----------------

@router.get("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}/linhas", response_model=list[schemas.LinhaEletricaOut])
def listar_linhas(projeto_id: int, analise_id: int, db: Session = Depends(get_db)):
    _get_analise(db, projeto_id, analise_id)
    return (
        db.query(LinhaEletrica).options(joinedload(LinhaEletrica.trechos))
        .filter(LinhaEletrica.analise_id == analise_id).order_by(LinhaEletrica.id).all()
    )


@router.post("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}/linhas", response_model=schemas.LinhaEletricaOut)
def criar_linha(projeto_id: int, analise_id: int, payload: schemas.LinhaEletricaIn, db: Session = Depends(get_db)):
    _get_analise(db, projeto_id, analise_id)
    try:
        for i, trecho in enumerate(payload.trechos):
            tabelas.valor("anexo_a_tabela_a2_ci", trecho.tipo_instalacao)
            tabelas.valor("anexo_a_tabela_a4_ce", trecho.ambiente)
            tabelas.cld_cli(trecho.categoria_blindagem)
            tabelas.valor_por_uw("anexo_b_tabela_b8_pld", trecho.categoria_pld, payload.tensao_suportavel_kv)
    except tabelas.ValorNaoDisponivel as e:
        raise HTTPException(422, str(e))

    linha = LinhaEletrica(
        analise_id=analise_id, tag=payload.tag, tipo=payload.tipo,
        tem_transformador_at_bt=payload.tem_transformador_at_bt, tensao_suportavel_kv=payload.tensao_suportavel_kv,
    )
    db.add(linha)
    db.flush()
    for i, trecho in enumerate(payload.trechos):
        db.add(TrechoLinha(linha_id=linha.id, ordem=i, **trecho.model_dump()))
    db.commit()
    return (
        db.query(LinhaEletrica).options(joinedload(LinhaEletrica.trechos))
        .filter(LinhaEletrica.id == linha.id).first()
    )


@router.delete("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}/linhas/{linha_id}")
def remover_linha(projeto_id: int, analise_id: int, linha_id: int, db: Session = Depends(get_db)):
    _get_analise(db, projeto_id, analise_id)
    linha = db.get(LinhaEletrica, linha_id)
    if not linha or linha.analise_id != analise_id:
        raise HTTPException(404, "Linha não encontrada.")
    db.delete(linha)
    db.commit()
    return {"ok": True}


# ---------------- Medidas de proteção (1:1) ----------------

@router.put("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}/medidas-protecao", response_model=schemas.MedidasProtecaoOut)
def salvar_medidas_protecao(projeto_id: int, analise_id: int, payload: schemas.MedidasProtecaoIn, db: Session = Depends(get_db)):
    analise = _get_analise(db, projeto_id, analise_id)
    try:
        tabelas.valor("anexo_b_tabela_b2_pb", payload.classe_spda)
        for chave in payload.medidas_pta:
            tabelas.valor("anexo_b_tabela_b1_pta", chave)
        tabelas.valor("anexo_b_tabela_b3_pspd", payload.dps_coordenado)
        tabelas.valor("anexo_b_tabela_b7_peb", payload.dps_classe_i)
        tabelas.valor("anexo_b_tabela_b6_ptu", payload.medida_ptu)
        tabelas.valor("anexo_b_tabela_b5_ks3", payload.fiacao_interna)
    except tabelas.ValorNaoDisponivel as e:
        raise HTTPException(422, str(e))

    medidas = analise.medidas_protecao or MedidasProtecao(analise_id=analise_id)
    dados = payload.model_dump(exclude={"medidas_pta"})
    for campo, valor in dados.items():
        setattr(medidas, campo, valor)
    medidas.medidas_pta_json = json.dumps(payload.medidas_pta)
    db.add(medidas)
    db.commit()
    db.refresh(medidas)
    return medidas


# ---------------- Cálculo ----------------

@router.post("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}/calcular", response_model=schemas.ResultadoRiscoOut)
def calcular_analise(projeto_id: int, analise_id: int, db: Session = Depends(get_db)):
    analise = _get_analise(db, projeto_id, analise_id)
    if not analise.estrutura:
        raise HTTPException(422, "Cadastre a estrutura antes de calcular.")
    zonas = db.query(ZonaEstudo).filter(ZonaEstudo.analise_id == analise_id).all()
    if not zonas:
        raise HTTPException(422, "Cadastre ao menos uma zona de estudo antes de calcular.")
    if not analise.medidas_protecao:
        raise HTTPException(422, "Cadastre as medidas de proteção antes de calcular.")
    linhas = (
        db.query(LinhaEletrica).options(joinedload(LinhaEletrica.trechos))
        .filter(LinhaEletrica.analise_id == analise_id).all()
    )

    rt1 = analise.rt1_customizado or tabelas.valor("tabela_04_risco_toleravel", "rt_r1")
    rt3 = analise.rt3_customizado or tabelas.valor("tabela_04_risco_toleravel", "rt_r3")
    ft_chave = "sistema_critico" if analise.estrutura.sistema_critico else "sistema_nao_critico"
    ft_valor = tabelas.valor("tabela_07_frequencia_toleravel", ft_chave)

    try:
        resultado, mem = riscos.calcular(
            analise.estrutura, zonas, linhas, analise.medidas_protecao,
            ng=analise.ng_valor, rt1=rt1, rt3=rt3, ft_valor=ft_valor,
        )
    except tabelas.ValorNaoDisponivel as e:
        raise HTTPException(422, str(e))

    registro = analise.resultado or ResultadoRisco(analise_id=analise_id)
    registro.r1, registro.rt1, registro.r1_atende = resultado["r1"], resultado["rt1"], resultado["r1_atende"]
    registro.r3, registro.rt3, registro.r3_atende = resultado["r3"], resultado["rt3"], resultado["r3_atende"]
    registro.f_total, registro.ft, registro.f_atende = resultado["f_total"], resultado["ft"], resultado["f_atende"]
    registro.memoria_calculo_json = mem.to_json()
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


@router.get("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}/resultado", response_model=schemas.ResultadoRiscoOut)
def obter_resultado(projeto_id: int, analise_id: int, db: Session = Depends(get_db)):
    analise = _get_analise(db, projeto_id, analise_id)
    if not analise.resultado:
        raise HTTPException(404, "Análise ainda não foi calculada.")
    return analise.resultado


@router.get("/api/projetos/{projeto_id}/risco5419/analises/{analise_id}/memoria-calculo")
def obter_memoria_calculo(projeto_id: int, analise_id: int, db: Session = Depends(get_db)):
    analise = _get_analise(db, projeto_id, analise_id)
    if not analise.resultado or not analise.resultado.memoria_calculo_json:
        raise HTTPException(404, "Análise ainda não foi calculada.")
    return json.loads(analise.resultado.memoria_calculo_json)
