"""
Dimensionamento de cabos: corrente de projeto, seção por capacidade de
condução, seção por queda de tensão, seção sugerida, cabo do catálogo
pré-selecionado (ou escolhido manualmente) e memória de cálculo completa
(regra 12 da especificação, passos 1 a 9).

Portado de `recalcular_cabo()` em `cabos-app/app/calculations.py`, removendo
o acesso a banco: quem resolve a carga (ponta "Para"), o percurso (trechos,
já com o nº de circuitos que cada um compartilha) e as tabelas/catálogo é a
camada `app/`; aqui só a matemática e a memória de cálculo.
"""
import math
from dataclasses import dataclass
from typing import Any

from .eletrica import (
    REATANCIA_TIPICA_OHM_KM, SECAO_MAX_MULTIPOLAR, SECOES_COMERCIAIS, area_circulo, fmt,
)
from .memoria import MemoriaCalculo
from .tabelas_normativas import capacidade_tabela, fator_agrupamento, fator_temperatura, resistencia_secao


@dataclass
class DadosCarga:
    """A carga alimentada pelo cabo — sempre a ponta "Para" (equipamento ou
    painel), já resolvida pela camada `app/` (spec §4.4)."""
    tipo: str              # "equipamento" ou "painel"
    tag: str
    descricao: str
    tensao_v: float
    num_fases: int
    possui_neutro: bool
    possui_terra: bool
    fp: float
    potencia_kw: float | None
    potencia_kva: float | None
    corrente_a: float | None
    origem_corrente: str
    potencia_kvar: float | None = None
    rendimento: float | None = None        # só equipamento — exibido na memória
    potencia_valor: float | None = None    # só equipamento — exibido na memória
    potencia_unidade: str | None = None    # só equipamento — exibido na memória


@dataclass
class TrechoPercurso:
    tag: str
    tipo: str
    comprimento_m: float
    ordem: int
    num_circuitos: int = 1   # nº de cabos distintos (incluindo este) que compartilham o trecho


@dataclass
class ItemCatalogoCabo:
    id: Any
    fabricante: str
    linha_produto: str
    construcao_basica: str
    tipo_isolacao: str
    num_condutores: int
    secao_nominal_mm2: float
    diametro_externo_nominal_mm: float
    resistencia_condutor_20c_ohm_km: float | None = None
    reatancia_ohm_km: float | None = None

    def nome(self) -> str:
        return f"{self.fabricante} {self.linha_produto} {self.construcao_basica or ''} ({self.num_condutores}x{fmt(self.secao_nominal_mm2, 1)} mm²)".replace("  ", " ")


@dataclass
class EntradaCabo:
    tag: str
    tipo_isolacao: str = "PVC"
    metodo_instalacao: str = "B1"
    temperatura_ambiente_c: float = 30.0
    fator_agrupamento_manual: float | None = None
    queda_tensao_admissivel_pct: float = 3.0
    num_cabos_paralelo: int = 1
    # Cabo escolhido manualmente pelo usuário (None = deixar o cálculo sugerir).
    catalogo_escolhido_manualmente: ItemCatalogoCabo | None = None


@dataclass
class ResultadoCabo:
    tensao_v: float | None = None
    num_fases: int | None = None
    num_condutores_calc: int | None = None
    num_condutores_carregados: int | None = None
    corrente_projeto_a: float | None = None
    distancia_total_m: float | None = None
    fator_temperatura_calc: float | None = None
    fator_agrupamento_calc: float | None = None
    secao_por_capacidade_mm2: float | None = None
    secao_por_queda_mm2: float | None = None
    secao_sugerida_mm2: float | None = None
    catalogo_cabo_escolhido: ItemCatalogoCabo | None = None
    secao_definida_manualmente: bool = False
    secao_mm2: float | None = None
    diametro_externo_mm: float | None = None
    area_secao_transversal_mm2: float | None = None
    tipo_construcao: str | None = None          # "multipolar" ou "unipolar"
    num_cabos_fisicos: int | None = None
    queda_tensao_calc_pct: float | None = None
    alerta_secao_insuficiente: bool = False


def _descricao_fases(num_fases, neutro, terra):
    s = f"{num_fases}F"
    if neutro:
        s += "+N"
    if terra:
        s += "+PE"
    return s


def _queda_tensao_pct(corrente_a, distancia_km, r_ohm_km, x_ohm_km, fp, tensao_v, num_fases):
    """ΔV% = k × Ib × L(km) × (R×cosφ + X×senφ) / V × 100 (regra 7).
    k = √3 (trifásico) ou 2 (monofásico/bifásico)."""
    sen_phi = math.sqrt(max(0.0, 1 - fp ** 2))
    termo = r_ohm_km * fp + x_ohm_km * sen_phi
    k = math.sqrt(3) if num_fases == 3 else 2
    return (k * corrente_a * distancia_km * termo) / tensao_v * 100


def sugerir_catalogo(catalogo: list[ItemCatalogoCabo], tipo_isolacao, secao_sugerida, num_condutores):
    """Escolhe o cabo comercial: multipolar até `SECAO_MAX_MULTIPOLAR` mm²,
    singelo (unipolar) a partir de 50 mm² (regra 8/9). Retorna
    `(item, "multipolar"|"unipolar")` ou `(None, None)` se não houver item
    compatível no catálogo informado."""
    candidatos = [c for c in catalogo if c.tipo_isolacao == tipo_isolacao and c.secao_nominal_mm2 >= secao_sugerida]
    if secao_sugerida <= SECAO_MAX_MULTIPOLAR:
        exatos = sorted((c for c in candidatos if c.num_condutores == num_condutores), key=lambda c: c.secao_nominal_mm2)
        if exatos:
            return exatos[0], "multipolar"
        maiores = sorted((c for c in candidatos if c.num_condutores >= num_condutores),
                          key=lambda c: (c.secao_nominal_mm2, c.num_condutores))
        if maiores:
            return maiores[0], "multipolar"
        unip = sorted((c for c in candidatos if c.num_condutores == 1), key=lambda c: c.secao_nominal_mm2)
        if unip:
            return unip[0], "unipolar"
        return None, None
    unip = sorted((c for c in candidatos if c.num_condutores == 1), key=lambda c: c.secao_nominal_mm2)
    if unip:
        return unip[0], "unipolar"
    qualquer = sorted(candidatos, key=lambda c: c.secao_nominal_mm2)
    if qualquer:
        return qualquer[0], ("multipolar" if qualquer[0].num_condutores > 1 else "unipolar")
    return None, None


def calcular_cabo(
    entrada: EntradaCabo,
    carga: DadosCarga,
    trechos: list[TrechoPercurso],
    *,
    tab_capacidade: list[dict],
    tab_fator_temperatura: list[dict],
    tab_fator_agrupamento: list[dict],
    tab_resistividade: list[dict],
    catalogo_cabos: list[ItemCatalogoCabo],
    de_tag: str = "-",
    para_tag: str = "-",
) -> tuple[ResultadoCabo, MemoriaCalculo]:
    """Executa os passos 1 a 9 da regra 12 e devolve o resultado mais a
    memória de cálculo completa (fórmulas e valores substituídos)."""
    mem = MemoriaCalculo()
    resultado = ResultadoCabo()

    tensao_v = carga.tensao_v
    fp = carga.fp
    num_fases = carga.num_fases
    neutro, terra = carga.possui_neutro, carga.possui_terra
    num_condutores = num_fases + (1 if neutro else 0) + (1 if terra else 0)
    num_cond_carregados = 3 if num_fases == 3 else 2

    resultado.tensao_v = tensao_v
    resultado.num_fases = num_fases
    resultado.num_condutores_calc = num_condutores
    resultado.num_condutores_carregados = num_cond_carregados

    # 1. Dados de entrada
    linhas = [
        f"Cabo {entrada.tag}: de {de_tag} para {para_tag}.",
        f"A carga alimentada é a ponta 'Para': {carga.tag} ({carga.descricao or carga.tipo}).",
        f"Tensão do circuito: {fmt(tensao_v, 0)} V | Configuração: {_descricao_fases(num_fases, neutro, terra)} "
        f"→ {num_condutores} condutores no cabo, {num_cond_carregados} condutores carregados para a tabela de capacidade.",
        f"Fator de potência (cos φ): {fmt(fp, 2)}.",
    ]
    if carga.tipo == "equipamento":
        linhas.append(
            f"Potência informada: {fmt(carga.potencia_valor)} {carga.potencia_unidade} | Rendimento (η): {fmt(carga.rendimento, 2)}."
        )
    mem.registrar("1. Dados de entrada (herdados da carga)", linhas)

    # 2. Potência
    if carga.tipo == "equipamento":
        linhas = [
            f"Potência ativa absorvida da rede: P = Pn / η = {fmt(carga.potencia_kw)} kW.",
            f"Potência aparente: S = P / cos φ = {fmt(carga.potencia_kw)} / {fmt(fp)} = {fmt(carga.potencia_kva)} kVA.",
            f"Potência reativa: Q = √(S² − P²) = {fmt(carga.potencia_kvar)} kvar.",
        ]
    else:
        linhas = [
            f"Demanda total do painel (equipamentos diretos + painéis a jusante, com fator de diversidade): P = {fmt(carga.potencia_kw)} kW.",
            f"Potência aparente de demanda: S = {fmt(carga.potencia_kva)} kVA.",
        ]
    mem.registrar("2. Potências da carga", linhas)

    # 3. Corrente de projeto (Ib) — regra 4: dividida pelo nº de cabos em paralelo
    corrente_carga = carga.corrente_a
    ib = (corrente_carga / entrada.num_cabos_paralelo) if (corrente_carga is not None and entrada.num_cabos_paralelo) else None
    resultado.corrente_projeto_a = ib
    formula_i = "I = S × 1000 / (√3 × V)" if num_fases == 3 else "I = S × 1000 / V"
    mem.registrar("3. Corrente de projeto (Ib)", [
        f"Corrente da carga ({carga.origem_corrente}): {formula_i} = {fmt(carga.potencia_kva)} × 1000 / "
        f"({'√3 × ' if num_fases == 3 else ''}{fmt(tensao_v, 0)}) = {fmt(corrente_carga)} A.",
        f"Nº de cabos em paralelo por fase: {entrada.num_cabos_paralelo}.",
        f"Corrente de projeto por cabo: Ib = {fmt(corrente_carga)} / {entrada.num_cabos_paralelo} = {fmt(ib)} A.",
    ], f"Ib = {fmt(ib)} A")

    # 4. Percurso (regra 5)
    trechos_ordenados = sorted(trechos, key=lambda t: t.ordem)
    distancia_total = sum((t.comprimento_m or 0) for t in trechos_ordenados)
    resultado.distancia_total_m = distancia_total
    linhas = [f"Trecho {i + 1}: {t.tag} ({t.tipo}) — {fmt(t.comprimento_m, 1)} m"
              for i, t in enumerate(trechos_ordenados)] or ["Nenhum trecho de eletroduto/bandeja informado (distância = 0)."]
    linhas.append(f"Distância total: L = {fmt(distancia_total, 1)} m.")
    mem.registrar("4. Percurso e distância total", linhas, f"L = {fmt(distancia_total, 1)} m")

    # 5. Seção mínima por capacidade de condução (regra 6)
    grupo = "PVC" if (entrada.tipo_isolacao or "").upper() == "PVC" else "EPR_XLPE"
    temperatura = entrada.temperatura_ambiente_c if entrada.temperatura_ambiente_c is not None else 30.0
    fator_temp = fator_temperatura(tab_fator_temperatura, grupo, temperatura)
    num_circuitos = max((t.num_circuitos for t in trechos_ordenados), default=1)
    if entrada.fator_agrupamento_manual:
        fator_agr = entrada.fator_agrupamento_manual
        origem_agr = "informado manualmente pelo usuário"
    else:
        fator_agr = fator_agrupamento(tab_fator_agrupamento, num_circuitos)
        origem_agr = f"tabela NBR 5410 para {num_circuitos} circuito(s) compartilhando o mesmo trecho"
    resultado.fator_temperatura_calc = fator_temp
    resultado.fator_agrupamento_calc = fator_agr

    secao_por_capacidade = None
    cap_final = None
    tentativas = []
    for secao in SECOES_COMERCIAIS:
        cap = capacidade_tabela(tab_capacidade, grupo, entrada.metodo_instalacao, num_cond_carregados, secao)
        if cap is None:
            continue
        cap_corr = cap * fator_temp * fator_agr
        ok = ib is not None and cap_corr >= ib
        tentativas.append(f"  {fmt(secao, 1)} mm²: capacidade de tabela {fmt(cap, 0)} A × {fmt(fator_temp)} × {fmt(fator_agr)} = {fmt(cap_corr, 1)} A → {'ATENDE' if ok else 'não atende'}")
        if ok:
            secao_por_capacidade = secao
            cap_final = cap_corr
            break
    resultado.secao_por_capacidade_mm2 = secao_por_capacidade
    linhas = [
        f"Tabela consultada: capacidade de condução NBR 5410 — isolação {entrada.tipo_isolacao} (grupo {grupo}), "
        f"método de instalação {entrada.metodo_instalacao}, {num_cond_carregados} condutores carregados.",
        f"Fator de correção por temperatura ambiente ({fmt(temperatura, 0)} °C): {fmt(fator_temp)}.",
        f"Fator de correção por agrupamento: {fmt(fator_agr)} ({origem_agr}).",
        "Critério: capacidade da tabela × fator de temperatura × fator de agrupamento ≥ Ib. Testando as seções em ordem crescente:",
        *tentativas,
    ]
    if secao_por_capacidade is None:
        linhas.append("Nenhuma seção da tabela atende à corrente de projeto — verifique o método de instalação ou use cabos em paralelo.")
    mem.registrar("5. Seção mínima por capacidade de condução", linhas,
                  f"{fmt(secao_por_capacidade, 1)} mm² (capacidade corrigida {fmt(cap_final, 1)} A)" if secao_por_capacidade else "não determinada")

    # 6. Seção mínima por queda de tensão (regra 7)
    distancia_km = (distancia_total or 0) / 1000
    secao_por_queda = None
    queda_final = None
    tentativas = []
    for secao in SECOES_COMERCIAIS:
        r = resistencia_secao(tab_resistividade, secao)
        if r is None or ib is None or not tensao_v:
            continue
        queda = _queda_tensao_pct(ib, distancia_km, r, REATANCIA_TIPICA_OHM_KM, fp, tensao_v, num_fases)
        ok = queda <= entrada.queda_tensao_admissivel_pct
        tentativas.append(f"  {fmt(secao, 1)} mm²: R = {fmt(r, 3)} Ω/km → ΔV = {fmt(queda)} % → {'ATENDE' if ok else 'não atende'}")
        if ok:
            secao_por_queda = secao
            queda_final = queda
            break
    resultado.secao_por_queda_mm2 = secao_por_queda
    k_txt = "√3" if num_fases == 3 else "2"
    sen_phi = math.sqrt(max(0.0, 1 - fp ** 2))
    mem.registrar("6. Seção mínima por queda de tensão", [
        f"Fórmula: ΔV(%) = {k_txt} × Ib × L(km) × (R × cos φ + X × sen φ) / V × 100.",
        f"Valores: Ib = {fmt(ib)} A | L = {fmt(distancia_km, 3)} km | cos φ = {fmt(fp)} | sen φ = {fmt(sen_phi)} | "
        f"X = {fmt(REATANCIA_TIPICA_OHM_KM, 3)} Ω/km (valor de referência) | V = {fmt(tensao_v, 0)} V.",
        f"Queda de tensão admissível: {fmt(entrada.queda_tensao_admissivel_pct, 1)} %.",
        "Testando as seções em ordem crescente:",
        *tentativas,
    ], f"{fmt(secao_por_queda, 1)} mm² (ΔV = {fmt(queda_final)} %)" if secao_por_queda else "não determinada")

    # 7. Seção sugerida e cabo do catálogo pré-selecionado (regra 8)
    candidatas = [s for s in (secao_por_capacidade, secao_por_queda) if s is not None]
    secao_sugerida = max(candidatas) if candidatas else None
    resultado.secao_sugerida_mm2 = secao_sugerida

    sugerido, construcao_sugerida = (None, None)
    if secao_sugerida is not None:
        sugerido, construcao_sugerida = sugerir_catalogo(catalogo_cabos, entrada.tipo_isolacao, secao_sugerida, num_condutores)
    linhas = [
        f"Seção sugerida = maior entre capacidade de condução ({fmt(secao_por_capacidade, 1)} mm²) e queda de tensão ({fmt(secao_por_queda, 1)} mm²) = {fmt(secao_sugerida, 1)} mm².",
        f"Regra construtiva: até {SECAO_MAX_MULTIPOLAR} mm² usa-se cabo multipolar ({num_condutores} vias); a partir de 50 mm² usam-se cabos singelos ({num_condutores} cabos unipolares).",
    ]
    if sugerido:
        linhas.append(f"Cabo comercial pré-selecionado no catálogo: {sugerido.nome()} — {construcao_sugerida}.")
    else:
        linhas.append("Nenhum cabo compatível encontrado no catálogo (verifique o catálogo de cabos para esta isolação).")
    mem.registrar("7. Seção sugerida e cabo pré-selecionado", linhas, f"{fmt(secao_sugerida, 1)} mm²" if secao_sugerida else "-")

    # 8. Cabo efetivamente escolhido (regra 8: usuário pode sobrescrever)
    escolhido = entrada.catalogo_escolhido_manualmente or sugerido
    manual = entrada.catalogo_escolhido_manualmente is not None and (
        sugerido is None or entrada.catalogo_escolhido_manualmente.id != sugerido.id
    )
    resultado.secao_definida_manualmente = manual
    resultado.catalogo_cabo_escolhido = escolhido

    if escolhido:
        resultado.secao_mm2 = escolhido.secao_nominal_mm2
        resultado.diametro_externo_mm = escolhido.diametro_externo_nominal_mm
        resultado.area_secao_transversal_mm2 = area_circulo(escolhido.diametro_externo_nominal_mm)
        resultado.tipo_construcao = "multipolar" if escolhido.num_condutores > 1 else "unipolar"
        resultado.num_cabos_fisicos = entrada.num_cabos_paralelo * (1 if resultado.tipo_construcao == "multipolar" else num_condutores)
        r_esc = escolhido.resistencia_condutor_20c_ohm_km or resistencia_secao(tab_resistividade, escolhido.secao_nominal_mm2)
        x_esc = escolhido.reatancia_ohm_km or REATANCIA_TIPICA_OHM_KM
        if r_esc is not None and ib is not None and tensao_v:
            resultado.queda_tensao_calc_pct = _queda_tensao_pct(ib, distancia_km, r_esc, x_esc, fp, tensao_v, num_fases)
        else:
            resultado.queda_tensao_calc_pct = None
        resultado.alerta_secao_insuficiente = bool(secao_sugerida is not None and escolhido.secao_nominal_mm2 < secao_sugerida)
        linhas = [f"Cabo adotado: {escolhido.nome()} — {'escolhido manualmente pelo usuário' if manual else 'sugestão automática do cálculo'}."]
        if resultado.tipo_construcao == "multipolar":
            linhas.append(f"Construção: multipolar com {escolhido.num_condutores} vias → {resultado.num_cabos_fisicos} cabo(s) físico(s) no percurso.")
        else:
            linhas.append(f"Construção: singelo (unipolar) → {num_condutores} cabos × {entrada.num_cabos_paralelo} em paralelo = {resultado.num_cabos_fisicos} cabo(s) físico(s) no percurso.")
        dentro = resultado.queda_tensao_calc_pct is not None and resultado.queda_tensao_calc_pct <= entrada.queda_tensao_admissivel_pct
        linhas.append(f"Queda de tensão recalculada para o cabo adotado (R = {fmt(r_esc, 3)} Ω/km, X = {fmt(x_esc, 3)} Ω/km): ΔV = {fmt(resultado.queda_tensao_calc_pct)} %"
                      f" ({'dentro' if dentro else 'ACIMA'} do limite de {fmt(entrada.queda_tensao_admissivel_pct, 1)} %).")
        if resultado.alerta_secao_insuficiente:
            linhas.append(f"ATENÇÃO: a seção adotada ({fmt(escolhido.secao_nominal_mm2, 1)} mm²) é MENOR que a seção sugerida ({fmt(secao_sugerida, 1)} mm²).")
        mem.registrar("8. Cabo efetivamente adotado", linhas, f"{fmt(escolhido.secao_nominal_mm2, 1)} mm² — ΔV = {fmt(resultado.queda_tensao_calc_pct)} %")
    else:
        mem.registrar("8. Cabo efetivamente adotado", ["Nenhum cabo adotado."], "-")

    # 9. Área do cabo e ocupação dos trechos (regra 9 e 10)
    linhas = []
    if escolhido:
        linhas.append(f"Diâmetro externo do cabo: {fmt(resultado.diametro_externo_mm, 1)} mm → área = π × ({fmt(resultado.diametro_externo_mm, 1)}/2)² = {fmt(resultado.area_secao_transversal_mm2, 1)} mm² por cabo físico.")
        linhas.append(f"Área total ocupada por este circuito: {resultado.num_cabos_fisicos} × {fmt(resultado.area_secao_transversal_mm2, 1)} = {fmt((resultado.area_secao_transversal_mm2 or 0) * (resultado.num_cabos_fisicos or 0), 1)} mm².")
    linhas.append("Trechos percorridos: " + (", ".join(t.tag for t in trechos_ordenados) or "nenhum") + ".")
    mem.registrar("9. Área do cabo e ocupação dos trechos", linhas)

    return resultado, mem
