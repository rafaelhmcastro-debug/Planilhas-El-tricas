"""
Motor de cálculo elétrico — implementa as regras da seção 5 da especificação:
dimensionamento de cabos (corrente, seção, queda de tensão), ocupação de
eletrodutos/bandejas e demanda de painéis/transformadores (com hierarquia
painel → painel a montante até o TOP).
"""
import json
import math
from typing import Optional

from sqlalchemy.orm import Session

from . import models

SECOES_COMERCIAIS = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 500]
REATANCIA_TIPICA_OHM_KM = 0.08  # valor de referência na ausência de reatância no catálogo (regra 7)
SECAO_MAX_MULTIPOLAR = 35       # até 35 mm² (inclusive) → cabo multipolar; a partir de 50 mm² → cabos singelos

FATOR_UNIDADE_KW = {"kW": 1.0, "W": 0.001, "CV": 0.7355, "HP": 0.7457}


def fmt(v, casas=2):
    if v is None:
        return "-"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def isolacao_grupo(tipo_isolacao: str) -> str:
    return "PVC" if (tipo_isolacao or "").upper() == "PVC" else "EPR_XLPE"


def area_circulo(diametro_mm: float):
    if diametro_mm is None:
        return None
    return math.pi * (diametro_mm / 2) ** 2


def corrente_por_aparente(s_kva, tensao_v, num_fases):
    """I = S / (√3·V) para trifásico; I = S / V para monofásico (F-N) ou bifásico (F-F)."""
    if not s_kva or not tensao_v:
        return None
    if num_fases == 3:
        return (s_kva * 1000) / (math.sqrt(3) * tensao_v)
    return (s_kva * 1000) / tensao_v


# ---------------------------------------------------------------------------
# Equipamentos (regras 1, 2, 3 + rendimento e potência reativa)
# ---------------------------------------------------------------------------

def recalcular_equipamento(db: Session, equip: models.Equipamento, recalcular_paineis=True):
    fp = equip.fator_potencia or 0.92
    eta = equip.rendimento or 1.0
    valor = equip.potencia_valor
    unidade = equip.potencia_unidade or "kW"

    if valor is None:
        equip.potencia_nominal_kw = None
        equip.potencia_ativa_calc_kw = None
        equip.potencia_aparente_calc_kva = None
        equip.potencia_reativa_calc_kvar = None
        equip.corrente_nominal_a = None
        equip.potencia_demanda_kw = None
        equip.potencia_demanda_reativa_kvar = None
    else:
        if unidade == "kVA":
            # potência aparente absorvida da rede: rendimento não se aplica
            s = valor
            p_el = s * fp
            equip.potencia_nominal_kw = p_el
        else:
            pn = valor * FATOR_UNIDADE_KW.get(unidade, 1.0)
            equip.potencia_nominal_kw = pn
            p_el = pn / eta
            s = p_el / fp
        q = math.sqrt(max(0.0, s ** 2 - p_el ** 2))
        equip.potencia_ativa_calc_kw = p_el
        equip.potencia_aparente_calc_kva = s
        equip.potencia_reativa_calc_kvar = q
        equip.corrente_nominal_a = corrente_por_aparente(s, equip.tensao_v, equip.num_fases)
        fd = equip.fator_demanda if equip.fator_demanda is not None else 1.0
        equip.potencia_demanda_kw = p_el * fd
        equip.potencia_demanda_reativa_kvar = q * fd

    db.flush()
    if recalcular_paineis:
        if equip.painel_transformador_tag:
            garantir_painel(db, equip.projeto_id, equip.painel_transformador_tag)
        recalcular_paineis_projeto(db, equip.projeto_id)


# ---------------------------------------------------------------------------
# Painéis / transformadores (regra 11 + hierarquia até o TOP)
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
    """Recalcula todos os painéis do projeto, propagando as cargas dos painéis a jusante
    para os painéis a montante (até o painel TOP)."""
    paineis = db.query(models.PainelTransformador).filter(models.PainelTransformador.projeto_id == projeto_id).all()
    por_tag = {p.tag: p for p in paineis}
    filhos = {}
    for p in paineis:
        pai = (p.painel_alimentador_tag or "").strip()
        if pai:
            filhos.setdefault(pai, []).append(p)

    equipamentos = db.query(models.Equipamento).filter(models.Equipamento.projeto_id == projeto_id).all()
    equip_por_painel = {}
    for e in equipamentos:
        if e.painel_transformador_tag:
            equip_por_painel.setdefault(e.painel_transformador_tag.strip(), []).append(e)

    calculado = {}
    em_progresso = set()

    def calcular(p: models.PainelTransformador):
        if p.tag in calculado:
            return calculado[p.tag]
        if p.tag in em_progresso:  # ciclo na hierarquia — ignora a recursão
            return None
        em_progresso.add(p.tag)

        p_inst = q_inst = pd = qd = i_inst = 0.0
        for e in equip_por_painel.get(p.tag, []):
            p_inst += e.potencia_ativa_calc_kw or 0
            q_inst += e.potencia_reativa_calc_kvar or 0
            pd += e.potencia_demanda_kw or 0
            qd += e.potencia_demanda_reativa_kvar or 0
            i_inst += e.corrente_nominal_a or 0
        for filho in filhos.get(p.tag, []):
            r = calcular(filho)
            if r:
                p_inst += r["p_inst"]
                q_inst += r["q_inst"]
                pd += r["pd"]
                qd += r["qd"]
                i_inst += r["i_inst"]

        fdiv = p.fator_diversidade if p.fator_diversidade is not None else 1.0
        pd *= fdiv
        qd *= fdiv
        s = math.sqrt(pd ** 2 + qd ** 2)
        p.potencia_instalada_kw = p_inst
        p.potencia_reativa_instalada_kvar = q_inst
        p.demanda_total_kw = pd
        p.demanda_reativa_kvar = qd
        p.demanda_aparente_kva = s
        p.fator_potencia_calc = (pd / s) if s else None
        p.corrente_total_a = corrente_por_aparente(s, p.tensao_v, p.num_fases or 3)
        p.corrente_instalada_a = i_inst

        em_progresso.discard(p.tag)
        calculado[p.tag] = {"p_inst": p_inst, "q_inst": q_inst, "pd": pd, "qd": qd, "i_inst": i_inst}
        return calculado[p.tag]

    for p in paineis:
        calcular(p)
    db.flush()


# ---------------------------------------------------------------------------
# Cabos (regras 4 a 9, 12)
# ---------------------------------------------------------------------------

def _capacidade_tabela(db: Session, grupo: str, metodo: str, num_condutores: int, secao: float):
    row = (
        db.query(models.TabCapacidadeConducao)
        .filter(
            models.TabCapacidadeConducao.isolacao_grupo == grupo,
            models.TabCapacidadeConducao.metodo_instalacao == metodo,
            models.TabCapacidadeConducao.num_condutores_carregados == num_condutores,
            models.TabCapacidadeConducao.secao_mm2 == secao,
        )
        .first()
    )
    return row.capacidade_a if row else None


def _fator_temperatura(db: Session, grupo: str, temperatura: float):
    rows = (
        db.query(models.TabFatorTemperatura)
        .filter(models.TabFatorTemperatura.isolacao_grupo == grupo)
        .order_by(models.TabFatorTemperatura.temperatura_c)
        .all()
    )
    if not rows:
        return 1.0
    if temperatura is None:
        temperatura = 30
    if temperatura <= rows[0].temperatura_c:
        return rows[0].fator
    if temperatura >= rows[-1].temperatura_c:
        return rows[-1].fator
    for a, b in zip(rows, rows[1:]):
        if a.temperatura_c <= temperatura <= b.temperatura_c:
            if a.temperatura_c == temperatura:
                return a.fator
            frac = (temperatura - a.temperatura_c) / (b.temperatura_c - a.temperatura_c)
            return a.fator + frac * (b.fator - a.fator)
    return 1.0


def _fator_agrupamento(db: Session, num_circuitos: int):
    rows = db.query(models.TabFatorAgrupamento).order_by(models.TabFatorAgrupamento.num_circuitos).all()
    if not rows:
        return 1.0
    exato = [r for r in rows if r.num_circuitos == num_circuitos]
    if exato:
        return exato[0].fator
    maiores = [r for r in rows if r.num_circuitos >= num_circuitos]
    if maiores:
        return maiores[0].fator
    return rows[-1].fator


def _resistencia_secao(db: Session, secao: float):
    row = db.query(models.TabResistividadeCondutor).filter(models.TabResistividadeCondutor.secao_mm2 == secao).first()
    return row.resistencia_ohm_km if row else None


def _num_circuitos_no_trecho(db: Session, eletroduto_bandeja_id: int, cabo_id_atual: int):
    trechos = db.query(models.CaboTrecho).filter(models.CaboTrecho.eletroduto_bandeja_id == eletroduto_bandeja_id).all()
    cabo_ids = {t.cabo_id for t in trechos}
    cabo_ids.add(cabo_id_atual)
    return len(cabo_ids)


def _queda_tensao_pct(corrente_a, distancia_km, r_ohm_km, x_ohm_km, fp, tensao_v, num_fases):
    sen_phi = math.sqrt(max(0.0, 1 - fp ** 2))
    termo = r_ohm_km * fp + x_ohm_km * sen_phi
    k = math.sqrt(3) if num_fases == 3 else 2
    return (k * corrente_a * distancia_km * termo) / tensao_v * 100


def _dados_da_carga(cabo: models.Cabo):
    """A carga alimentada pelo cabo é a ponta 'Para' (equipamento ou painel)."""
    if cabo.painel_para:
        p = cabo.painel_para
        return {
            "tipo": "painel", "tag": p.tag, "descricao": f"{p.tipo} {p.tag}",
            "tensao_v": p.tensao_v, "num_fases": p.num_fases or 3,
            "possui_neutro": True, "possui_terra": True,
            "fp": p.fator_potencia_calc or 0.92,
            "potencia_kw": p.demanda_total_kw, "potencia_kva": p.demanda_aparente_kva,
            "corrente_a": p.corrente_total_a,
            "origem_corrente": "corrente do alimentador do painel (demanda total a jusante)",
        }
    e = cabo.equipamento_para or cabo.equipamento_de
    if not e:
        return None
    return {
        "tipo": "equipamento", "tag": e.tag, "descricao": e.descricao or "",
        "tensao_v": e.tensao_v, "num_fases": e.num_fases or 3,
        "possui_neutro": bool(e.possui_neutro), "possui_terra": bool(e.possui_terra),
        "fp": e.fator_potencia or 0.92, "rendimento": e.rendimento or 1.0,
        "potencia_kw": e.potencia_ativa_calc_kw, "potencia_kva": e.potencia_aparente_calc_kva,
        "potencia_kvar": e.potencia_reativa_calc_kvar,
        "potencia_valor": e.potencia_valor, "potencia_unidade": e.potencia_unidade,
        "corrente_a": e.corrente_nominal_a,
        "origem_corrente": "corrente nominal do equipamento",
    }


def _descricao_fases(num_fases, neutro, terra):
    s = f"{num_fases}F"
    if neutro:
        s += "+N"
    if terra:
        s += "+PE"
    return s


def _nome_cabo(c: models.CatalogoCabo):
    return f"{c.fabricante} {c.linha_produto} {c.construcao_basica or ''} ({c.num_condutores}x{fmt(c.secao_nominal_mm2, 1)} mm²)".replace("  ", " ")


def _sugerir_catalogo(db, tipo_isolacao, secao_sugerida, num_condutores):
    """Escolhe o cabo comercial: multipolar até 35 mm², singelo a partir de 50 mm²."""
    base = db.query(models.CatalogoCabo).filter(
        models.CatalogoCabo.tipo_isolacao == tipo_isolacao,
        models.CatalogoCabo.secao_nominal_mm2 >= secao_sugerida,
    )
    if secao_sugerida <= SECAO_MAX_MULTIPOLAR:
        exato = base.filter(models.CatalogoCabo.num_condutores == num_condutores).order_by(models.CatalogoCabo.secao_nominal_mm2).first()
        if exato:
            return exato, "multipolar"
        maior = base.filter(models.CatalogoCabo.num_condutores >= num_condutores).order_by(
            models.CatalogoCabo.secao_nominal_mm2, models.CatalogoCabo.num_condutores).first()
        if maior:
            return maior, "multipolar"
        unip = base.filter(models.CatalogoCabo.num_condutores == 1).order_by(models.CatalogoCabo.secao_nominal_mm2).first()
        return unip, "unipolar"
    unip = base.filter(models.CatalogoCabo.num_condutores == 1).order_by(models.CatalogoCabo.secao_nominal_mm2).first()
    if unip:
        return unip, "unipolar"
    qualquer = base.order_by(models.CatalogoCabo.secao_nominal_mm2).first()
    return qualquer, ("multipolar" if qualquer and qualquer.num_condutores > 1 else "unipolar")


def recalcular_cabo(db: Session, cabo: models.Cabo):
    passos = []

    def passo(titulo, linhas, resultado=None):
        passos.append({"titulo": titulo, "linhas": linhas, "resultado": resultado})

    carga = _dados_da_carga(cabo)
    if not carga:
        cabo.memoria_calculo_json = json.dumps({"passos": [{"titulo": "Erro", "linhas": ["Cabo sem carga (ponta 'Para') definida."], "resultado": None}]}, ensure_ascii=False)
        db.flush()
        return

    tensao_v = carga["tensao_v"]
    fp = carga["fp"]
    num_fases = carga["num_fases"]
    neutro, terra = carga["possui_neutro"], carga["possui_terra"]
    num_condutores = num_fases + (1 if neutro else 0) + (1 if terra else 0)
    num_cond_carregados = 3 if num_fases == 3 else 2

    cabo.tensao_v = tensao_v
    cabo.num_fases = num_fases
    cabo.num_condutores_calc = num_condutores
    cabo.num_condutores_carregados = num_cond_carregados

    # 1. Dados de entrada
    linhas = [
        f"Cabo {cabo.tag}: de {cabo.de_tag or '-'} para {cabo.para_tag or '-'}.",
        f"A carga alimentada é a ponta 'Para': {carga['tag']} ({carga['descricao'] or carga['tipo']}).",
        f"Tensão do circuito: {fmt(tensao_v, 0)} V | Configuração: {_descricao_fases(num_fases, neutro, terra)} "
        f"→ {num_condutores} condutores no cabo, {num_cond_carregados} condutores carregados para a tabela de capacidade.",
        f"Fator de potência (cos φ): {fmt(fp, 2)}.",
    ]
    if carga["tipo"] == "equipamento":
        linhas.append(
            f"Potência informada: {fmt(carga['potencia_valor'])} {carga['potencia_unidade']} | Rendimento (η): {fmt(carga['rendimento'], 2)}."
        )
    passo("1. Dados de entrada (herdados da carga)", linhas)

    # 2. Potência
    if carga["tipo"] == "equipamento":
        linhas = [
            f"Potência nominal convertida: Pn = {fmt(cabo.equipamento_para.potencia_nominal_kw if cabo.equipamento_para else None)} kW.",
            f"Potência ativa absorvida da rede: P = Pn / η = {fmt(carga['potencia_kw'])} kW.",
            f"Potência aparente: S = P / cos φ = {fmt(carga['potencia_kw'])} / {fmt(fp)} = {fmt(carga['potencia_kva'])} kVA.",
            f"Potência reativa: Q = √(S² − P²) = {fmt(carga.get('potencia_kvar'))} kvar.",
        ]
    else:
        linhas = [
            f"Demanda total do painel (equipamentos diretos + painéis a jusante, com fator de diversidade): P = {fmt(carga['potencia_kw'])} kW.",
            f"Potência aparente de demanda: S = {fmt(carga['potencia_kva'])} kVA.",
        ]
    passo("2. Potências da carga", linhas)

    # 3. Corrente de projeto
    corrente_carga = carga["corrente_a"]
    ib = (corrente_carga / cabo.num_cabos_paralelo) if (corrente_carga is not None and cabo.num_cabos_paralelo) else None
    cabo.corrente_projeto_a = ib
    formula_i = "I = S × 1000 / (√3 × V)" if num_fases == 3 else "I = S × 1000 / V"
    passo("3. Corrente de projeto (Ib)", [
        f"Corrente da carga ({carga['origem_corrente']}): {formula_i} = {fmt(carga['potencia_kva'])} × 1000 / "
        f"({'√3 × ' if num_fases == 3 else ''}{fmt(tensao_v, 0)}) = {fmt(corrente_carga)} A.",
        f"Nº de cabos em paralelo por fase: {cabo.num_cabos_paralelo}.",
        f"Corrente de projeto por cabo: Ib = {fmt(corrente_carga)} / {cabo.num_cabos_paralelo} = {fmt(ib)} A.",
    ], f"Ib = {fmt(ib)} A")

    # 4. Percurso
    trechos = sorted(cabo.trechos, key=lambda t: t.ordem)
    distancia_total = sum((t.eletroduto_bandeja.comprimento_m or 0) for t in trechos)
    cabo.distancia_total_m = distancia_total
    linhas = [f"Trecho {i + 1}: {t.eletroduto_bandeja.tag} ({t.eletroduto_bandeja.tipo}) — {fmt(t.eletroduto_bandeja.comprimento_m, 1)} m"
              for i, t in enumerate(trechos)] or ["Nenhum trecho de eletroduto/bandeja informado (distância = 0)."]
    linhas.append(f"Distância total: L = {fmt(distancia_total, 1)} m.")
    passo("4. Percurso e distância total", linhas, f"L = {fmt(distancia_total, 1)} m")

    # 5. Capacidade de condução
    grupo = isolacao_grupo(cabo.tipo_isolacao)
    temperatura = cabo.temperatura_ambiente_c if cabo.temperatura_ambiente_c is not None else 30.0
    fator_temp = _fator_temperatura(db, grupo, temperatura)
    num_circuitos = 1
    for t in trechos:
        num_circuitos = max(num_circuitos, _num_circuitos_no_trecho(db, t.eletroduto_bandeja_id, cabo.id or -1))
    if cabo.fator_agrupamento_manual:
        fator_agr = cabo.fator_agrupamento_manual
        origem_agr = "informado manualmente pelo usuário"
    else:
        fator_agr = _fator_agrupamento(db, num_circuitos)
        origem_agr = f"tabela NBR 5410 para {num_circuitos} circuito(s) compartilhando o mesmo trecho"
    cabo.fator_temperatura_calc = fator_temp
    cabo.fator_agrupamento_calc = fator_agr

    secao_por_capacidade = None
    cap_final = None
    tentativas = []
    for secao in SECOES_COMERCIAIS:
        cap = _capacidade_tabela(db, grupo, cabo.metodo_instalacao, num_cond_carregados, secao)
        if cap is None:
            continue
        cap_corr = cap * fator_temp * fator_agr
        ok = ib is not None and cap_corr >= ib
        tentativas.append(f"  {fmt(secao, 1)} mm²: capacidade de tabela {fmt(cap, 0)} A × {fmt(fator_temp)} × {fmt(fator_agr)} = {fmt(cap_corr, 1)} A → {'ATENDE' if ok else 'não atende'}")
        if ok:
            secao_por_capacidade = secao
            cap_final = cap_corr
            break
    cabo.secao_por_capacidade_mm2 = secao_por_capacidade
    linhas = [
        f"Tabela consultada: capacidade de condução NBR 5410 — isolação {cabo.tipo_isolacao} (grupo {grupo}), "
        f"método de instalação {cabo.metodo_instalacao}, {num_cond_carregados} condutores carregados.",
        f"Fator de correção por temperatura ambiente ({fmt(temperatura, 0)} °C): {fmt(fator_temp)}.",
        f"Fator de correção por agrupamento: {fmt(fator_agr)} ({origem_agr}).",
        "Critério: capacidade da tabela × fator de temperatura × fator de agrupamento ≥ Ib. Testando as seções em ordem crescente:",
        *tentativas,
    ]
    if secao_por_capacidade is None:
        linhas.append("Nenhuma seção da tabela atende à corrente de projeto — verifique o método de instalação ou use cabos em paralelo.")
    passo("5. Seção mínima por capacidade de condução", linhas,
          f"{fmt(secao_por_capacidade, 1)} mm² (capacidade corrigida {fmt(cap_final, 1)} A)" if secao_por_capacidade else "não determinada")

    # 6. Queda de tensão
    distancia_km = (distancia_total or 0) / 1000
    secao_por_queda = None
    queda_final = None
    tentativas = []
    for secao in SECOES_COMERCIAIS:
        r = _resistencia_secao(db, secao)
        if r is None or ib is None or not tensao_v:
            continue
        queda = _queda_tensao_pct(ib, distancia_km, r, REATANCIA_TIPICA_OHM_KM, fp, tensao_v, num_fases)
        ok = queda <= cabo.queda_tensao_admissivel_pct
        tentativas.append(f"  {fmt(secao, 1)} mm²: R = {fmt(r, 3)} Ω/km → ΔV = {fmt(queda)} % → {'ATENDE' if ok else 'não atende'}")
        if ok:
            secao_por_queda = secao
            queda_final = queda
            break
    cabo.secao_por_queda_mm2 = secao_por_queda
    k_txt = "√3" if num_fases == 3 else "2"
    sen_phi = math.sqrt(max(0.0, 1 - fp ** 2))
    passo("6. Seção mínima por queda de tensão", [
        f"Fórmula: ΔV(%) = {k_txt} × Ib × L(km) × (R × cos φ + X × sen φ) / V × 100.",
        f"Valores: Ib = {fmt(ib)} A | L = {fmt(distancia_km, 3)} km | cos φ = {fmt(fp)} | sen φ = {fmt(sen_phi)} | "
        f"X = {fmt(REATANCIA_TIPICA_OHM_KM, 3)} Ω/km (valor de referência) | V = {fmt(tensao_v, 0)} V.",
        f"Queda de tensão admissível: {fmt(cabo.queda_tensao_admissivel_pct, 1)} %.",
        "Testando as seções em ordem crescente:",
        *tentativas,
    ], f"{fmt(secao_por_queda, 1)} mm² (ΔV = {fmt(queda_final)} %)" if secao_por_queda else "não determinada")

    # 7. Seção sugerida e cabo do catálogo
    secao_sugerida = None
    candidatas = [s for s in (secao_por_capacidade, secao_por_queda) if s is not None]
    if candidatas:
        secao_sugerida = max(candidatas)
    cabo.secao_sugerida_mm2 = secao_sugerida

    sugerido, construcao_sugerida = (None, None)
    if secao_sugerida is not None:
        sugerido, construcao_sugerida = _sugerir_catalogo(db, cabo.tipo_isolacao, secao_sugerida, num_condutores)
    linhas = [
        f"Seção sugerida = maior entre capacidade de condução ({fmt(secao_por_capacidade, 1)} mm²) e queda de tensão ({fmt(secao_por_queda, 1)} mm²) = {fmt(secao_sugerida, 1)} mm².",
        f"Regra construtiva: até {SECAO_MAX_MULTIPOLAR} mm² usa-se cabo multipolar ({num_condutores} vias); a partir de 50 mm² usam-se cabos singelos ({num_condutores} cabos unipolares).",
    ]
    if sugerido:
        linhas.append(f"Cabo comercial pré-selecionado no catálogo: {_nome_cabo(sugerido)} — {construcao_sugerida}.")
    else:
        linhas.append("Nenhum cabo compatível encontrado no catálogo (verifique o catálogo de cabos para esta isolação).")
    passo("7. Seção sugerida e cabo pré-selecionado", linhas, f"{fmt(secao_sugerida, 1)} mm²" if secao_sugerida else "-")

    # 8. Cabo efetivamente escolhido
    if not cabo.secao_definida_manualmente and sugerido:
        cabo.catalogo_cabo_id = sugerido.id
    escolhido = db.get(models.CatalogoCabo, cabo.catalogo_cabo_id) if cabo.catalogo_cabo_id else None
    if not escolhido:
        escolhido = sugerido
        cabo.catalogo_cabo_id = sugerido.id if sugerido else None
        cabo.secao_definida_manualmente = False
    if sugerido and escolhido and escolhido.id == sugerido.id:
        cabo.secao_definida_manualmente = False

    if escolhido:
        cabo.secao_mm2 = escolhido.secao_nominal_mm2
        cabo.diametro_externo_mm = escolhido.diametro_externo_nominal_mm
        cabo.area_secao_transversal_mm2 = area_circulo(escolhido.diametro_externo_nominal_mm)
        cabo.tipo_construcao = "multipolar" if escolhido.num_condutores > 1 else "unipolar"
        cabo.num_cabos_fisicos = cabo.num_cabos_paralelo * (1 if cabo.tipo_construcao == "multipolar" else num_condutores)
        r_esc = escolhido.resistencia_condutor_20c_ohm_km or _resistencia_secao(db, escolhido.secao_nominal_mm2)
        x_esc = escolhido.reatancia_ohm_km or REATANCIA_TIPICA_OHM_KM
        if r_esc is not None and ib is not None and tensao_v:
            cabo.queda_tensao_calc_pct = _queda_tensao_pct(ib, distancia_km, r_esc, x_esc, fp, tensao_v, num_fases)
        else:
            cabo.queda_tensao_calc_pct = None
        cabo.alerta_secao_insuficiente = bool(secao_sugerida is not None and escolhido.secao_nominal_mm2 < secao_sugerida)
        linhas = [f"Cabo adotado: {_nome_cabo(escolhido)} — {'escolhido manualmente pelo usuário' if cabo.secao_definida_manualmente else 'sugestão automática do cálculo'}."]
        if cabo.tipo_construcao == "multipolar":
            linhas.append(f"Construção: multipolar com {escolhido.num_condutores} vias → {cabo.num_cabos_fisicos} cabo(s) físico(s) no percurso.")
        else:
            linhas.append(f"Construção: singelo (unipolar) → {num_condutores} cabos × {cabo.num_cabos_paralelo} em paralelo = {cabo.num_cabos_fisicos} cabo(s) físico(s) no percurso.")
        linhas.append(f"Queda de tensão recalculada para o cabo adotado (R = {fmt(r_esc, 3)} Ω/km, X = {fmt(x_esc, 3)} Ω/km): ΔV = {fmt(cabo.queda_tensao_calc_pct)} %"
                      f" ({'dentro' if cabo.queda_tensao_calc_pct is not None and cabo.queda_tensao_calc_pct <= cabo.queda_tensao_admissivel_pct else 'ACIMA'} do limite de {fmt(cabo.queda_tensao_admissivel_pct, 1)} %).")
        if cabo.alerta_secao_insuficiente:
            linhas.append(f"ATENÇÃO: a seção adotada ({fmt(escolhido.secao_nominal_mm2, 1)} mm²) é MENOR que a seção sugerida ({fmt(secao_sugerida, 1)} mm²).")
        passo("8. Cabo efetivamente adotado", linhas, f"{fmt(escolhido.secao_nominal_mm2, 1)} mm² — ΔV = {fmt(cabo.queda_tensao_calc_pct)} %")
    else:
        cabo.secao_mm2 = None
        cabo.diametro_externo_mm = None
        cabo.area_secao_transversal_mm2 = None
        cabo.tipo_construcao = None
        cabo.num_cabos_fisicos = None
        cabo.queda_tensao_calc_pct = None
        cabo.alerta_secao_insuficiente = False
        passo("8. Cabo efetivamente adotado", ["Nenhum cabo adotado."], "-")

    # 9. Ocupação
    linhas = []
    if escolhido:
        linhas.append(f"Diâmetro externo do cabo: {fmt(cabo.diametro_externo_mm, 1)} mm → área = π × ({fmt(cabo.diametro_externo_mm, 1)}/2)² = {fmt(cabo.area_secao_transversal_mm2, 1)} mm² por cabo físico.")
        linhas.append(f"Área total ocupada por este circuito: {cabo.num_cabos_fisicos} × {fmt(cabo.area_secao_transversal_mm2, 1)} = {fmt((cabo.area_secao_transversal_mm2 or 0) * (cabo.num_cabos_fisicos or 0), 1)} mm².")
    linhas.append("Trechos percorridos: " + (", ".join(t.eletroduto_bandeja.tag for t in trechos) or "nenhum") + ".")
    passo("9. Área do cabo e ocupação dos trechos", linhas)

    cabo.memoria_calculo_json = json.dumps({"passos": passos}, ensure_ascii=False)
    db.flush()

    for t in trechos:
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

def _limite_ocupacao_eletroduto(db: Session, num_cabos: int):
    bucket = "1" if num_cabos == 1 else ("2" if num_cabos == 2 else "3+")
    row = db.query(models.TabLimiteOcupacaoEletroduto).filter(models.TabLimiteOcupacaoEletroduto.num_cabos == bucket).first()
    return row.taxa_max_pct if row else 40.0


def _desc_item(item: models.CatalogoInfraestrutura):
    if not item:
        return None
    if item.tipo == "eletroduto":
        return f"{item.linha_produto} DN {fmt(item.diametro_nominal_mm, 0)} mm ({item.diametro_nominal_pol})"
    return f"{item.linha_produto} — {fmt(item.largura_nominal_mm, 0)} mm"


def calcular_ocupacao(db: Session, infra: models.EletrodutoBandeja):
    trechos = db.query(models.CaboTrecho).filter(models.CaboTrecho.eletroduto_bandeja_id == infra.id).all()
    cabos = [t.cabo for t in trechos if t.cabo]

    resultado = {
        "infra_id": infra.id, "tag": infra.tag, "tipo": infra.tipo,
        "item_escolhido": _desc_item(infra.catalogo_item),
        "cabos": [
            {
                "id": c.id, "tag": c.tag, "de": c.de_tag, "para": c.para_tag,
                "secao_mm2": c.secao_mm2, "diametro_externo_mm": c.diametro_externo_mm,
                "tipo_construcao": c.tipo_construcao, "num_cabos_paralelo": c.num_cabos_paralelo,
                "num_cabos_fisicos": c.num_cabos_fisicos or c.num_cabos_paralelo,
                "area_total_mm2": (c.area_secao_transversal_mm2 or 0) * (c.num_cabos_fisicos or c.num_cabos_paralelo or 1),
            }
            for c in cabos
        ],
    }
    num_cabos_fisicos = sum((c.num_cabos_fisicos or c.num_cabos_paralelo or 1) for c in cabos)
    resultado["num_cabos_fisicos"] = num_cabos_fisicos

    if infra.tipo == "eletroduto":
        area_ocupada = sum((c.area_secao_transversal_mm2 or 0) * (c.num_cabos_fisicos or c.num_cabos_paralelo or 1) for c in cabos)
        taxa = (area_ocupada / infra.area_util_mm2 * 100) if infra.area_util_mm2 else None
        limite = _limite_ocupacao_eletroduto(db, num_cabos_fisicos) if num_cabos_fisicos else None
        resultado.update({
            "area_ocupada_mm2": area_ocupada, "area_util_mm2": infra.area_util_mm2,
            "ocupacao_pct": taxa, "limite_pct": limite,
            "alerta": bool(taxa is not None and limite is not None and taxa > limite),
        })
        sugerido = None
        if num_cabos_fisicos:
            linha = infra.catalogo_item.linha_produto if infra.catalogo_item else None
            q = db.query(models.CatalogoInfraestrutura).filter(models.CatalogoInfraestrutura.tipo == "eletroduto")
            if linha:
                q = q.filter(models.CatalogoInfraestrutura.linha_produto == linha)
            for item in q.order_by(models.CatalogoInfraestrutura.diametro_nominal_mm.asc()).all():
                if item.area_util_mm2 and area_ocupada / item.area_util_mm2 * 100 <= limite:
                    sugerido = item
                    break
    else:
        soma_diametros = sum((c.diametro_externo_mm or 0) * (c.num_cabos_fisicos or c.num_cabos_paralelo or 1) for c in cabos)
        largura_util = infra.largura_util_mm
        taxa = (soma_diametros / largura_util * 100) if largura_util else None
        resultado.update({
            "soma_diametros_mm": soma_diametros, "largura_util_mm": largura_util,
            "ocupacao_pct": taxa, "limite_pct": 100.0,
            "alerta": bool(largura_util is not None and soma_diametros > largura_util),
        })
        sugerido = None
        if num_cabos_fisicos:
            for item in db.query(models.CatalogoInfraestrutura).filter(models.CatalogoInfraestrutura.tipo == infra.tipo).order_by(models.CatalogoInfraestrutura.largura_nominal_mm.asc()).all():
                if item.largura_util_mm and item.largura_util_mm >= soma_diametros:
                    sugerido = item
                    break

    resultado["dimensao_sugerida_id"] = sugerido.id if sugerido else None
    resultado["dimensao_sugerida_desc"] = _desc_item(sugerido)
    resultado["escolha_insuficiente"] = bool(resultado.get("alerta"))
    return resultado


def recalcular_ocupacao_trecho(db: Session, infra: models.EletrodutoBandeja):
    resultado = calcular_ocupacao(db, infra)
    infra.dimensao_sugerida_id = resultado.get("dimensao_sugerida_id")
    db.flush()
    return resultado
