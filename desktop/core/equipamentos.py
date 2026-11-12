"""
Cálculo de potências e corrente nominal de um equipamento (carga).

Portado de `recalcular_equipamento()` em `cabos-app/app/calculations.py`,
removendo a parte de orquestração (criar painel automaticamente, disparar
recálculo de painéis e de cabos) — isso é responsabilidade da camada `app/`,
que tem acesso ao banco; aqui só a matemática.
"""
import math
from dataclasses import dataclass

from .eletrica import FATOR_UNIDADE_KW, corrente_por_aparente


@dataclass
class EntradaEquipamento:
    potencia_valor: float | None       # None = equipamento sem potência informada ainda
    potencia_unidade: str = "kW"       # "kW", "W", "CV", "HP" ou "kVA"
    rendimento: float = 1.0            # η (0–1)
    fator_potencia: float = 0.92       # cos φ (0–1]
    tensao_v: float = 380.0
    num_fases: int = 3                 # 1, 2 ou 3
    fator_demanda: float = 1.0         # FD (0–1]


@dataclass
class ResultadoEquipamento:
    potencia_nominal_kw: float | None = None         # Pn informada, convertida para kW
    potencia_ativa_calc_kw: float | None = None       # P = Pn/η (potência elétrica absorvida)
    potencia_aparente_calc_kva: float | None = None   # S = P/cosφ
    potencia_reativa_calc_kvar: float | None = None   # Q = √(S²−P²)
    corrente_nominal_a: float | None = None
    potencia_demanda_kw: float | None = None          # Pd = P×FD
    potencia_demanda_reativa_kvar: float | None = None


def calcular_equipamento(entrada: EntradaEquipamento) -> ResultadoEquipamento:
    """Regras 1 e 3 da especificação (completar potência + potência de demanda),
    mais rendimento e potência reativa.

    Para a unidade `kVA`, o valor informado já é a potência aparente absorvida
    da rede — o rendimento não se aplica (não há "potência no eixo" a converter
    para potência elétrica; a entrada já é elétrica). Para as demais unidades
    (kW/W/CV/HP), o valor informado é a potência nominal no eixo (ou nominal do
    equipamento); P = Pn/η e S = P/cosφ, conforme regra 1.
    """
    if entrada.potencia_valor is None:
        return ResultadoEquipamento()

    fp = entrada.fator_potencia or 0.92
    eta = entrada.rendimento or 1.0
    unidade = entrada.potencia_unidade or "kW"

    if unidade == "kVA":
        s = entrada.potencia_valor
        p_el = s * fp
        pn = p_el
    else:
        pn = entrada.potencia_valor * FATOR_UNIDADE_KW.get(unidade, 1.0)
        p_el = pn / eta
        s = p_el / fp

    q = math.sqrt(max(0.0, s ** 2 - p_el ** 2))
    corrente = corrente_por_aparente(s, entrada.tensao_v, entrada.num_fases)
    fd = entrada.fator_demanda if entrada.fator_demanda is not None else 1.0

    return ResultadoEquipamento(
        potencia_nominal_kw=pn,
        potencia_ativa_calc_kw=p_el,
        potencia_aparente_calc_kva=s,
        potencia_reativa_calc_kvar=q,
        corrente_nominal_a=corrente,
        potencia_demanda_kw=p_el * fd,
        potencia_demanda_reativa_kvar=q * fd,
    )


def calcular_equipamento_tipo_painel(
    potencia_ativa_kw: float, potencia_reativa_kvar: float,
    tensao_v: float, num_fases: int, fator_demanda: float = 1.0,
) -> ResultadoEquipamento:
    """Requisito 1 (potência opcional para equipamentos tipo "painel/quadro"):
    quando o equipamento representa um painel/quadro (ex.: um CCM que também
    aparece como carga direta de um painel a montante), P e Q não vêm de uma
    potência nominal digitada — vêm da soma das cargas diretamente alimentadas
    por ele, já agregada por `core/paineis.calcular_paineis()` (que também
    inclui subpainéis dele, recursivamente). Rendimento e fator de potência
    não se aplicam aqui: a potência agregada já é elétrica (não há "potência
    no eixo" de uma carga única para converter). S e In derivam de P/Q; Pd/Qd
    aplicam o fator de demanda do próprio equipamento (conceito independente
    do fator de diversidade do painel que ele espelha)."""
    s = math.sqrt(potencia_ativa_kw ** 2 + potencia_reativa_kvar ** 2)
    corrente = corrente_por_aparente(s, tensao_v, num_fases)
    fd = fator_demanda if fator_demanda is not None else 1.0

    return ResultadoEquipamento(
        potencia_nominal_kw=None,
        potencia_ativa_calc_kw=potencia_ativa_kw,
        potencia_aparente_calc_kva=s,
        potencia_reativa_calc_kvar=potencia_reativa_kvar,
        corrente_nominal_a=corrente,
        potencia_demanda_kw=potencia_ativa_kw * fd,
        potencia_demanda_reativa_kvar=potencia_reativa_kvar * fd,
    )
