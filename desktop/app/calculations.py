"""
Camada de orquestração: busca dados no banco (ORM), repassa para o núcleo de
cálculo puro (`desktop/core/`) e grava os resultados de volta nos objetos do
SQLAlchemy — exatamente a separação proposta em ADR 0001 §4. A matemática em
si (fórmulas, memória de cálculo) mora só em `core/`; aqui só busca/gravação
e orquestração entre entidades (criar painel automaticamente, encadear
recálculo de painéis e de cabos quando uma carga muda).

Portado de `recalcular_equipamento`, `garantir_painel`,
`recalcular_paineis_projeto`, `recalcular_cabo`, `calcular_ocupacao` etc. em
`cabos-app/app/calculations.py`. Mesmo comportamento observável — mesmos
testes de paridade da Fase 1 (`core/tests/test_paridade_com_web.py`) cobrem
as funções puras usadas aqui.
"""
import json
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from . import models, schemas

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import cabos as core_cabos  # noqa: E402
from core import equipamentos as core_equipamentos  # noqa: E402
from core import infraestrutura as core_infra  # noqa: E402
from core import paineis as core_paineis  # noqa: E402


# ---------------------------------------------------------------------------
# Equipamentos (regras 1, 2, 3 + rendimento e potência reativa)
# ---------------------------------------------------------------------------

def recalcular_equipamento(db: Session, equip: models.Equipamento, recalcular_paineis=True):
    entrada = core_equipamentos.EntradaEquipamento(
        potencia_valor=equip.potencia_valor,
        potencia_unidade=equip.potencia_unidade or "kW",
        rendimento=equip.rendimento or 1.0,
        fator_potencia=equip.fator_potencia or 0.92,
        tensao_v=equip.tensao_v,
        num_fases=equip.num_fases,
        fator_demanda=equip.fator_demanda if equip.fator_demanda is not None else 1.0,
    )
    resultado = core_equipamentos.calcular_equipamento(entrada)

    equip.potencia_nominal_kw = resultado.potencia_nominal_kw
    equip.potencia_ativa_calc_kw = resultado.potencia_ativa_calc_kw
    equip.potencia_aparente_calc_kva = resultado.potencia_aparente_calc_kva
    equip.potencia_reativa_calc_kvar = resultado.potencia_reativa_calc_kvar
    equip.corrente_nominal_a = resultado.corrente_nominal_a
    equip.potencia_demanda_kw = resultado.potencia_demanda_kw
    equip.potencia_demanda_reativa_kvar = resultado.potencia_demanda_reativa_kvar

    db.flush()
    if recalcular_paineis:
        if equip.painel_transformador_tag:
            garantir_painel(db, equip.projeto_id, equip.painel_transformador_tag)
        recalcular_paineis_projeto(db, equip.projeto_id)


# ---------------------------------------------------------------------------
# Painéis / transformadores (regra 11 + hierarquia até o TOP, D2)
# ---------------------------------------------------------------------------

def garantir_painel(db: Session, projeto_id: int, tag: str) -> Optional[models.PainelTransformador]:
    tag = (tag or "").strip()
    if not tag:
        return None
    painel = (
        db.query(models.PainelTransformador)
        .filter(models.PainelTransformador.projeto_id == projeto_id, models.PainelTransformador.tag == tag)
        .first()
    )
    if not painel:
        primeiro_equip = (
            db.query(models.Equipamento)
            .filter(models.Equipamento.projeto_id == projeto_id, models.Equipamento.painel_transformador_tag == tag)
            .first()
        )
        painel = models.PainelTransformador(
            projeto_id=projeto_id, tag=tag, tipo="painel",
            tensao_v=primeiro_equip.tensao_v if primeiro_equip else 380,
            num_fases=3, fator_diversidade=1.0, painel_alimentador_tag="",
        )
        db.add(painel)
        db.flush()
    return painel


def recalcular_painel_por_tag(db: Session, projeto_id: int, tag: str):
    garantir_painel(db, projeto_id, tag)
    recalcular_paineis_projeto(db, projeto_id)


def recalcular_painel(db: Session, painel: models.PainelTransformador):
    recalcular_paineis_projeto(db, painel.projeto_id)


def recalcular_paineis_projeto(db: Session, projeto_id: int):
    """Recalcula todos os painéis do projeto, propagando as cargas dos painéis
    a jusante para os painéis a montante (até o painel TOP)."""
    paineis = db.query(models.PainelTransformador).filter(models.PainelTransformador.projeto_id == projeto_id).all()
    equipamentos = db.query(models.Equipamento).filter(models.Equipamento.projeto_id == projeto_id).all()

    def _montar_entradas():
        entradas_paineis = [
            core_paineis.EntradaPainel(
                tag=p.tag, painel_alimentador_tag=p.painel_alimentador_tag or "",
                fator_diversidade=p.fator_diversidade if p.fator_diversidade is not None else 1.0,
                tensao_v=p.tensao_v, num_fases=p.num_fases or 3,
            )
            for p in paineis
        ]
        entradas_equipamentos = [
            core_paineis.EntradaEquipamentoPainel(
                tag=e.tag or "",
                painel_transformador_tag=e.painel_transformador_tag or "",
                potencia_ativa_calc_kw=e.potencia_ativa_calc_kw,
                potencia_reativa_calc_kvar=e.potencia_reativa_calc_kvar,
                potencia_demanda_kw=e.potencia_demanda_kw,
                potencia_demanda_reativa_kvar=e.potencia_demanda_reativa_kvar,
                corrente_nominal_a=e.corrente_nominal_a,
            )
            for e in equipamentos
        ]
        return entradas_paineis, entradas_equipamentos

    resultados = core_paineis.calcular_paineis(*_montar_entradas())

    # Requisito 1 (potência opcional para painéis): um equipamento tipo
    # "painel/quadro" tem P/Q sempre sincronizadas com o agregado do painel de
    # MESMA TAG (soma das cargas a jusante dele, já calculada acima — inclui
    # subpainéis, recursivamente) — mesmo que o usuário tenha digitado uma
    # potência (ela é ignorada; a tela avisa disso). Refeito aqui, a cada
    # recálculo de painéis do projeto — e não só quando o próprio equipamento
    # é salvo — porque o agregado de QUALQUER painel pode mudar por uma edição
    # em outro lugar (ex.: uma carga nova sob "0D-3302-402"), e sem isso o
    # equipamento "0D-3302-402" ficaria com valores desatualizados.
    sincronizou = False
    for e in equipamentos:
        if e.tipo_carga != schemas.TIPO_CARGA_PAINEL:
            continue
        r = resultados.get(e.tag or "")
        novo = core_equipamentos.calcular_equipamento_tipo_painel(
            potencia_ativa_kw=r.potencia_instalada_kw if r else 0.0,
            potencia_reativa_kvar=r.potencia_reativa_instalada_kvar if r else 0.0,
            tensao_v=e.tensao_v, num_fases=e.num_fases or 3,
            fator_demanda=e.fator_demanda if e.fator_demanda is not None else 1.0,
        )
        e.potencia_nominal_kw = novo.potencia_nominal_kw
        e.potencia_ativa_calc_kw = novo.potencia_ativa_calc_kw
        e.potencia_aparente_calc_kva = novo.potencia_aparente_calc_kva
        e.potencia_reativa_calc_kvar = novo.potencia_reativa_calc_kvar
        e.corrente_nominal_a = novo.corrente_nominal_a
        e.potencia_demanda_kw = novo.potencia_demanda_kw
        e.potencia_demanda_reativa_kvar = novo.potencia_demanda_reativa_kvar
        sincronizou = True

    if sincronizou:
        db.flush()
        resultados = core_paineis.calcular_paineis(*_montar_entradas())

    for p in paineis:
        r = resultados.get(p.tag)
        if not r:
            continue
        p.potencia_instalada_kw = r.potencia_instalada_kw
        p.potencia_reativa_instalada_kvar = r.potencia_reativa_instalada_kvar
        p.demanda_total_kw = r.demanda_total_kw
        p.demanda_reativa_kvar = r.demanda_reativa_kvar
        p.demanda_aparente_kva = r.demanda_aparente_kva
        p.fator_potencia_calc = r.fator_potencia_calc
        p.corrente_total_a = r.corrente_total_a
        p.corrente_instalada_a = r.corrente_instalada_a
        if r.ciclo_detectado:
            import logging
            logging.getLogger(__name__).warning(
                "Hierarquia de painéis em ciclo no projeto %s: painel %s participa de um "
                "ciclo em painel_alimentador_tag — a contribuição desse ramo foi descartada.",
                projeto_id, p.tag,
            )
    db.flush()


# ---------------------------------------------------------------------------
# Cabos (regras 4 a 9, 12)
# ---------------------------------------------------------------------------

def _dados_da_carga(cabo: models.Cabo):
    """A carga alimentada pelo cabo é a ponta 'Para' (equipamento ou painel) — spec §4.4."""
    if cabo.painel_para:
        p = cabo.painel_para
        return core_cabos.DadosCarga(
            tipo="painel", tag=p.tag, descricao=f"{p.tipo} {p.tag}",
            tensao_v=p.tensao_v, num_fases=p.num_fases or 3,
            possui_neutro=True, possui_terra=True,
            fp=p.fator_potencia_calc or 0.92,
            potencia_kw=p.demanda_total_kw, potencia_kva=p.demanda_aparente_kva,
            corrente_a=p.corrente_total_a,
            origem_corrente="corrente do alimentador do painel (demanda total a jusante)",
        )
    e = cabo.equipamento_para or cabo.equipamento_de
    if not e:
        return None
    return core_cabos.DadosCarga(
        tipo="equipamento", tag=e.tag, descricao=e.descricao or "",
        tensao_v=e.tensao_v, num_fases=e.num_fases or 3,
        possui_neutro=bool(e.possui_neutro), possui_terra=bool(e.possui_terra),
        fp=e.fator_potencia or 0.92, rendimento=e.rendimento or 1.0,
        potencia_kw=e.potencia_ativa_calc_kw, potencia_kva=e.potencia_aparente_calc_kva,
        potencia_kvar=e.potencia_reativa_calc_kvar,
        potencia_valor=e.potencia_valor, potencia_unidade=e.potencia_unidade,
        corrente_a=e.corrente_nominal_a,
        origem_corrente="corrente nominal do equipamento",
    )


def _num_circuitos_no_trecho(db: Session, eletroduto_bandeja_id: int, cabo_id_atual: int):
    trechos = db.query(models.CaboTrecho).filter(models.CaboTrecho.eletroduto_bandeja_id == eletroduto_bandeja_id).all()
    cabo_ids = {t.cabo_id for t in trechos}
    cabo_ids.add(cabo_id_atual)
    return len(cabo_ids)


def _catalogo_cabo_para_core(c: models.CatalogoCabo) -> core_cabos.ItemCatalogoCabo:
    return core_cabos.ItemCatalogoCabo(
        id=c.id, fabricante=c.fabricante, linha_produto=c.linha_produto,
        construcao_basica=c.construcao_basica, tipo_isolacao=c.tipo_isolacao,
        num_condutores=c.num_condutores, secao_nominal_mm2=c.secao_nominal_mm2,
        diametro_externo_nominal_mm=c.diametro_externo_nominal_mm,
        resistencia_condutor_20c_ohm_km=c.resistencia_condutor_20c_ohm_km,
        reatancia_ohm_km=c.reatancia_ohm_km,
    )


def _tab_capacidade_dict(db: Session):
    return [
        {"isolacao_grupo": r.isolacao_grupo, "metodo_instalacao": r.metodo_instalacao,
         "num_condutores_carregados": r.num_condutores_carregados, "secao_mm2": r.secao_mm2,
         "capacidade_a": r.capacidade_a}
        for r in db.query(models.TabCapacidadeConducao).all()
    ]


def _tab_fator_temperatura_dict(db: Session):
    return [{"isolacao_grupo": r.isolacao_grupo, "temperatura_c": r.temperatura_c, "fator": r.fator}
            for r in db.query(models.TabFatorTemperatura).all()]


def _tab_fator_agrupamento_dict(db: Session):
    return [{"num_circuitos": r.num_circuitos, "fator": r.fator}
            for r in db.query(models.TabFatorAgrupamento).all()]


def _tab_resistividade_dict(db: Session):
    return [{"secao_mm2": r.secao_mm2, "resistencia_ohm_km": r.resistencia_ohm_km}
            for r in db.query(models.TabResistividadeCondutor).all()]


def recalcular_cabo(db: Session, cabo: models.Cabo):
    carga = _dados_da_carga(cabo)
    if not carga:
        cabo.memoria_calculo_json = json.dumps(
            {"passos": [{"titulo": "Erro", "linhas": ["Cabo sem carga (ponta 'Para') definida."], "resultado": None}]},
            ensure_ascii=False,
        )
        db.flush()
        return

    trechos_orm = sorted(cabo.trechos, key=lambda t: t.ordem)
    trechos = [
        core_cabos.TrechoPercurso(
            tag=t.eletroduto_bandeja.tag, tipo=t.eletroduto_bandeja.tipo,
            comprimento_m=t.eletroduto_bandeja.comprimento_m or 0, ordem=t.ordem,
            num_circuitos=_num_circuitos_no_trecho(db, t.eletroduto_bandeja_id, cabo.id or -1),
        )
        for t in trechos_orm
    ]

    catalogo_cabos = [_catalogo_cabo_para_core(c) for c in db.query(models.CatalogoCabo).all()]

    escolhido_manual = None
    if cabo.secao_definida_manualmente and cabo.catalogo_cabo_id:
        row = db.get(models.CatalogoCabo, cabo.catalogo_cabo_id)
        if row:
            escolhido_manual = _catalogo_cabo_para_core(row)

    entrada = core_cabos.EntradaCabo(
        tag=cabo.tag, tipo_isolacao=cabo.tipo_isolacao, metodo_instalacao=cabo.metodo_instalacao,
        temperatura_ambiente_c=cabo.temperatura_ambiente_c if cabo.temperatura_ambiente_c is not None else 30.0,
        fator_agrupamento_manual=cabo.fator_agrupamento_manual,
        queda_tensao_admissivel_pct=cabo.queda_tensao_admissivel_pct,
        num_cabos_paralelo=cabo.num_cabos_paralelo,
        catalogo_escolhido_manualmente=escolhido_manual,
    )

    resultado, mem = core_cabos.calcular_cabo(
        entrada, carga, trechos,
        tab_capacidade=_tab_capacidade_dict(db),
        tab_fator_temperatura=_tab_fator_temperatura_dict(db),
        tab_fator_agrupamento=_tab_fator_agrupamento_dict(db),
        tab_resistividade=_tab_resistividade_dict(db),
        catalogo_cabos=catalogo_cabos,
        de_tag=cabo.de_tag or "-", para_tag=cabo.para_tag or "-",
    )

    cabo.tensao_v = resultado.tensao_v
    cabo.num_fases = resultado.num_fases
    cabo.num_condutores_calc = resultado.num_condutores_calc
    cabo.num_condutores_carregados = resultado.num_condutores_carregados
    cabo.corrente_projeto_a = resultado.corrente_projeto_a
    cabo.distancia_total_m = resultado.distancia_total_m
    cabo.fator_temperatura_calc = resultado.fator_temperatura_calc
    cabo.fator_agrupamento_calc = resultado.fator_agrupamento_calc
    cabo.secao_por_capacidade_mm2 = resultado.secao_por_capacidade_mm2
    cabo.secao_por_queda_mm2 = resultado.secao_por_queda_mm2
    cabo.secao_sugerida_mm2 = resultado.secao_sugerida_mm2
    cabo.secao_definida_manualmente = resultado.secao_definida_manualmente
    cabo.catalogo_cabo_id = resultado.catalogo_cabo_escolhido.id if resultado.catalogo_cabo_escolhido else None
    cabo.secao_mm2 = resultado.secao_mm2
    cabo.diametro_externo_mm = resultado.diametro_externo_mm
    cabo.area_secao_transversal_mm2 = resultado.area_secao_transversal_mm2
    cabo.tipo_construcao = resultado.tipo_construcao
    cabo.num_cabos_fisicos = resultado.num_cabos_fisicos
    cabo.queda_tensao_calc_pct = resultado.queda_tensao_calc_pct
    cabo.alerta_secao_insuficiente = resultado.alerta_secao_insuficiente
    cabo.memoria_calculo_json = mem.to_json()
    db.flush()

    for t in trechos_orm:
        recalcular_ocupacao_trecho(db, t.eletroduto_bandeja)


def recalcular_cabos_da_carga(db: Session, projeto_id: int, equipamento_id=None, painel_id=None):
    q = db.query(models.Cabo).filter(models.Cabo.projeto_id == projeto_id)
    if equipamento_id:
        q = q.filter((models.Cabo.equipamento_para_id == equipamento_id) | (models.Cabo.equipamento_de_id == equipamento_id))
    if painel_id:
        q = q.filter((models.Cabo.painel_para_id == painel_id) | (models.Cabo.painel_de_id == painel_id))
    for cabo in q.all():
        recalcular_cabo(db, cabo)


def recalcular_todos_cabos(db: Session, projeto_id: int):
    for cabo in db.query(models.Cabo).filter(models.Cabo.projeto_id == projeto_id).all():
        recalcular_cabo(db, cabo)


# ---------------------------------------------------------------------------
# Eletrodutos / bandejas (regra 10)
# ---------------------------------------------------------------------------

def _catalogo_infra_para_core(item: models.CatalogoInfraestrutura) -> core_infra.ItemCatalogoInfra:
    return core_infra.ItemCatalogoInfra(
        id=item.id, linha_produto=item.linha_produto, tipo=item.tipo,
        diametro_nominal_mm=item.diametro_nominal_mm, diametro_nominal_pol=item.diametro_nominal_pol,
        area_util_mm2=item.area_util_mm2, largura_nominal_mm=item.largura_nominal_mm,
        largura_util_mm=item.largura_util_mm,
    )


def calcular_ocupacao(db: Session, infra: models.EletrodutoBandeja) -> dict:
    """Devolve um dict com o mesmo formato de `cabos-app/app/calculations.py`
    (usado por `routers/infraestrutura.py` e por `excel_export.py`): a
    matemática vem de `core/infraestrutura.py`, mas a lista `cabos` (detalhe
    por cabo no trecho, usada no relatório) é montada aqui, a partir do ORM,
    porque não faz parte do núcleo puro (não é cálculo, é formatação de
    detalhe de exibição)."""
    trechos = db.query(models.CaboTrecho).filter(models.CaboTrecho.eletroduto_bandeja_id == infra.id).all()
    cabos_orm = [t.cabo for t in trechos if t.cabo]

    entrada = core_infra.EntradaInfra(
        id=infra.id, tag=infra.tag, tipo=infra.tipo,
        area_util_mm2=infra.area_util_mm2, largura_util_mm=infra.largura_util_mm,
        item_escolhido=_catalogo_infra_para_core(infra.catalogo_item) if infra.catalogo_item else None,
    )
    cabos_core = [
        core_infra.CaboNoTrecho(
            tag=c.tag, de=c.de_tag, para=c.para_tag, secao_mm2=c.secao_mm2,
            diametro_externo_mm=c.diametro_externo_mm, area_secao_transversal_mm2=c.area_secao_transversal_mm2,
            tipo_construcao=c.tipo_construcao, num_cabos_paralelo=c.num_cabos_paralelo,
            num_cabos_fisicos=c.num_cabos_fisicos,
        )
        for c in cabos_orm
    ]
    catalogo_infra = [_catalogo_infra_para_core(i) for i in db.query(models.CatalogoInfraestrutura).all()]

    resultado = core_infra.calcular_ocupacao(
        entrada, cabos_core,
        tab_limite_ocupacao_eletroduto=[
            {"num_cabos": r.num_cabos, "taxa_max_pct": r.taxa_max_pct}
            for r in db.query(models.TabLimiteOcupacaoEletroduto).all()
        ],
        catalogo_infraestrutura=catalogo_infra,
    )

    return {
        "infra_id": resultado.infra_id, "tag": resultado.tag, "tipo": resultado.tipo,
        "item_escolhido": resultado.item_escolhido_desc,
        "cabos": [
            {
                "id": c.id, "tag": c.tag, "de": c.de_tag, "para": c.para_tag,
                "secao_mm2": c.secao_mm2, "diametro_externo_mm": c.diametro_externo_mm,
                "tipo_construcao": c.tipo_construcao, "num_cabos_paralelo": c.num_cabos_paralelo,
                "num_cabos_fisicos": c.num_cabos_fisicos or c.num_cabos_paralelo,
                "area_total_mm2": (c.area_secao_transversal_mm2 or 0) * (c.num_cabos_fisicos or c.num_cabos_paralelo or 1),
            }
            for c in cabos_orm
        ],
        "num_cabos_fisicos": resultado.num_cabos_fisicos,
        "area_ocupada_mm2": resultado.area_ocupada_mm2, "area_util_mm2": resultado.area_util_mm2,
        "soma_diametros_mm": resultado.soma_diametros_mm, "largura_util_mm": resultado.largura_util_mm,
        "ocupacao_pct": resultado.ocupacao_pct, "limite_pct": resultado.limite_pct,
        "alerta": resultado.alerta,
        "dimensao_sugerida_id": resultado.dimensao_sugerida.id if resultado.dimensao_sugerida else None,
        "dimensao_sugerida_desc": resultado.dimensao_sugerida.descricao() if resultado.dimensao_sugerida else None,
        "escolha_insuficiente": resultado.escolha_insuficiente,
    }


def recalcular_ocupacao_trecho(db: Session, infra: models.EletrodutoBandeja):
    resultado = calcular_ocupacao(db, infra)
    infra.dimensao_sugerida_id = resultado.get("dimensao_sugerida_id")
    db.flush()
    return resultado
