"""
Demanda de painéis/transformadores, com hierarquia painel → painel a
montante até o painel TOP (regra 11 da especificação + regra 11-bis,
confirmada por escrito em decisions-and-spec-corrections.md, D2, 2026-11-03):

    O usuário cadastra o painel TOP como o ponto mais a montante da
    instalação (sem alimentador, ou alimentador vazio). Todo painel a jusante
    informa a TAG do painel que o alimenta. A demanda de cada painel é a soma
    das cargas diretas (equipamentos com essa TAG) mais a demanda já calculada
    de cada painel filho, aplicando o fator de diversidade do próprio painel
    sobre essa soma — propagação recursiva jusante→montante até o TOP.

Portado de `recalcular_paineis_projeto()` em `cabos-app/app/calculations.py`,
removendo o acesso a banco (a busca de painéis/equipamentos do projeto é feita
pela camada `app/`, que monta as listas de entrada abaixo).
"""
import math
from dataclasses import dataclass

from .eletrica import corrente_por_aparente


@dataclass
class EntradaPainel:
    tag: str
    painel_alimentador_tag: str = ""   # vazio = painel TOP
    fator_diversidade: float = 1.0
    tensao_v: float = 380.0
    num_fases: int = 3


@dataclass
class EntradaEquipamentoPainel:
    """Só os campos do equipamento que entram na soma do painel."""
    painel_transformador_tag: str
    potencia_ativa_calc_kw: float | None = None
    potencia_reativa_calc_kvar: float | None = None
    potencia_demanda_kw: float | None = None
    potencia_demanda_reativa_kvar: float | None = None
    corrente_nominal_a: float | None = None


@dataclass
class ResultadoPainel:
    tag: str
    potencia_instalada_kw: float = 0.0
    potencia_reativa_instalada_kvar: float = 0.0
    demanda_total_kw: float = 0.0
    demanda_reativa_kvar: float = 0.0
    demanda_aparente_kva: float = 0.0
    fator_potencia_calc: float | None = None
    corrente_total_a: float | None = None
    corrente_instalada_a: float = 0.0   # soma das correntes nominais a jusante
    ciclo_detectado: bool = False        # ver nota abaixo


def calcular_paineis(
    paineis: list[EntradaPainel], equipamentos: list[EntradaEquipamentoPainel]
) -> dict[str, ResultadoPainel]:
    """Calcula a demanda de todos os painéis de um projeto de uma vez,
    propagando painéis a jusante para o painel a montante.

    Nota sobre ciclos: se a cadeia de `painel_alimentador_tag` formar um ciclo
    (ex.: A alimentado por B, B alimentado por A — erro de cadastro), o painel
    que fecha o ciclo é calculado com a recursão interrompida nesse ponto
    (contribuição do ramo em ciclo = 0), sem levantar erro — mesmo
    comportamento do código web atual. `ciclo_detectado=True` sinaliza isso no
    resultado para a camada `app/` decidir como alertar o usuário.
    """
    filhos: dict[str, list[EntradaPainel]] = {}
    for p in paineis:
        pai = (p.painel_alimentador_tag or "").strip()
        if pai:
            filhos.setdefault(pai, []).append(p)

    equip_por_painel: dict[str, list[EntradaEquipamentoPainel]] = {}
    for e in equipamentos:
        tag = (e.painel_transformador_tag or "").strip()
        if tag:
            equip_por_painel.setdefault(tag, []).append(e)

    calculado: dict[str, ResultadoPainel] = {}
    em_progresso: set[str] = set()
    tags_em_ciclo: set[str] = set()

    def calcular(p: EntradaPainel) -> ResultadoPainel:
        if p.tag in calculado:
            return calculado[p.tag]
        if p.tag in em_progresso:
            # A cadeia de painel_alimentador_tag fechou um ciclo em p.tag — a
            # contribuição desse ramo é descartada (mesmo comportamento do
            # código web atual); tags_em_ciclo guarda quem participou do
            # ciclo para o resultado final poder sinalizar isso.
            tags_em_ciclo.add(p.tag)
            return ResultadoPainel(tag=p.tag, ciclo_detectado=True)
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
            p_inst += r.potencia_instalada_kw
            q_inst += r.potencia_reativa_instalada_kvar
            pd += r.demanda_total_kw
            qd += r.demanda_reativa_kvar
            i_inst += r.corrente_instalada_a

        fdiv = p.fator_diversidade if p.fator_diversidade is not None else 1.0
        pd *= fdiv
        qd *= fdiv
        s = math.sqrt(pd ** 2 + qd ** 2)
        resultado = ResultadoPainel(
            tag=p.tag,
            potencia_instalada_kw=p_inst,
            potencia_reativa_instalada_kvar=q_inst,
            demanda_total_kw=pd,
            demanda_reativa_kvar=qd,
            demanda_aparente_kva=s,
            fator_potencia_calc=(pd / s) if s else None,
            corrente_total_a=corrente_por_aparente(s, p.tensao_v, p.num_fases or 3),
            corrente_instalada_a=i_inst,
        )
        em_progresso.discard(p.tag)
        calculado[p.tag] = resultado
        return resultado

    for p in paineis:
        calcular(p)
    for tag in tags_em_ciclo:
        if tag in calculado:
            calculado[tag].ciclo_detectado = True
    return calculado
