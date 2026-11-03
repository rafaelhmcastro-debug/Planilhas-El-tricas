"""
Ocupação de eletrodutos, eletrocalhas, perfilados e leitos (regra 10),
tratada de forma diferente por tipo (10a para eletroduto, 10b para os
demais), com sugestão de dimensão a partir do catálogo Elecon.

Portado de `calcular_ocupacao()` em `cabos-app/app/calculations.py`,
removendo o acesso a banco: a camada `app/` já traz a lista de cabos que
passam pelo trecho e o catálogo de infraestrutura candidato.
"""
from dataclasses import dataclass
from typing import Any

from .eletrica import fmt
from .tabelas_normativas import limite_ocupacao_eletroduto


@dataclass
class CaboNoTrecho:
    tag: str
    de: str
    para: str
    secao_mm2: float | None
    diametro_externo_mm: float | None
    area_secao_transversal_mm2: float | None
    tipo_construcao: str | None
    num_cabos_paralelo: int
    num_cabos_fisicos: int | None = None   # None = usa num_cabos_paralelo


@dataclass
class ItemCatalogoInfra:
    id: Any
    linha_produto: str
    tipo: str   # eletroduto, eletrocalha, perfilado, leito
    diametro_nominal_mm: float | None = None
    diametro_nominal_pol: str | None = None
    area_util_mm2: float | None = None
    largura_nominal_mm: float | None = None
    largura_util_mm: float | None = None

    def descricao(self) -> str:
        if self.tipo == "eletroduto":
            return f"{self.linha_produto} DN {fmt(self.diametro_nominal_mm, 0)} mm ({self.diametro_nominal_pol})"
        return f"{self.linha_produto} — {fmt(self.largura_nominal_mm, 0)} mm"


@dataclass
class EntradaInfra:
    id: Any
    tag: str
    tipo: str
    area_util_mm2: float | None = None     # eletroduto — herdado do item do catálogo escolhido
    largura_util_mm: float | None = None   # eletrocalha/perfilado/leito — idem
    item_escolhido: ItemCatalogoInfra | None = None   # para filtrar a sugestão pela mesma linha (eletroduto)


@dataclass
class ResultadoOcupacao:
    infra_id: Any
    tag: str
    tipo: str
    item_escolhido_desc: str | None
    num_cabos_fisicos: int
    area_ocupada_mm2: float | None = None      # eletroduto
    area_util_mm2: float | None = None         # eletroduto
    soma_diametros_mm: float | None = None     # eletrocalha/perfilado/leito
    largura_util_mm: float | None = None       # eletrocalha/perfilado/leito
    ocupacao_pct: float | None = None
    limite_pct: float | None = None
    alerta: bool = False
    dimensao_sugerida: ItemCatalogoInfra | None = None
    escolha_insuficiente: bool = False


def _num_fisicos(c: CaboNoTrecho) -> int:
    return c.num_cabos_fisicos or c.num_cabos_paralelo or 1


def calcular_ocupacao(
    infra: EntradaInfra,
    cabos: list[CaboNoTrecho],
    *,
    tab_limite_ocupacao_eletroduto: list[dict],
    catalogo_infraestrutura: list[ItemCatalogoInfra],
) -> ResultadoOcupacao:
    num_cabos_fisicos = sum(_num_fisicos(c) for c in cabos)
    resultado = ResultadoOcupacao(
        infra_id=infra.id, tag=infra.tag, tipo=infra.tipo,
        item_escolhido_desc=infra.item_escolhido.descricao() if infra.item_escolhido else None,
        num_cabos_fisicos=num_cabos_fisicos,
    )

    if infra.tipo == "eletroduto":
        area_ocupada = sum((c.area_secao_transversal_mm2 or 0) * _num_fisicos(c) for c in cabos)
        taxa = (area_ocupada / infra.area_util_mm2 * 100) if infra.area_util_mm2 else None
        limite = limite_ocupacao_eletroduto(tab_limite_ocupacao_eletroduto, num_cabos_fisicos) if num_cabos_fisicos else None
        resultado.area_ocupada_mm2 = area_ocupada
        resultado.area_util_mm2 = infra.area_util_mm2
        resultado.ocupacao_pct = taxa
        resultado.limite_pct = limite
        resultado.alerta = bool(taxa is not None and limite is not None and taxa > limite)

        sugerido = None
        if num_cabos_fisicos:
            linha = infra.item_escolhido.linha_produto if infra.item_escolhido else None
            candidatos = [i for i in catalogo_infraestrutura if i.tipo == "eletroduto" and (linha is None or i.linha_produto == linha)]
            for item in sorted(candidatos, key=lambda i: (i.diametro_nominal_mm is None, i.diametro_nominal_mm)):
                if item.area_util_mm2 and area_ocupada / item.area_util_mm2 * 100 <= limite:
                    sugerido = item
                    break
    else:
        soma_diametros = sum((c.diametro_externo_mm or 0) * _num_fisicos(c) for c in cabos)
        largura_util = infra.largura_util_mm
        taxa = (soma_diametros / largura_util * 100) if largura_util else None
        resultado.soma_diametros_mm = soma_diametros
        resultado.largura_util_mm = largura_util
        resultado.ocupacao_pct = taxa
        resultado.limite_pct = 100.0
        resultado.alerta = bool(largura_util is not None and soma_diametros > largura_util)

        sugerido = None
        if num_cabos_fisicos:
            candidatos = [i for i in catalogo_infraestrutura if i.tipo == infra.tipo]
            for item in sorted(candidatos, key=lambda i: (i.largura_nominal_mm is None, i.largura_nominal_mm)):
                if item.largura_util_mm and item.largura_util_mm >= soma_diametros:
                    sugerido = item
                    break

    resultado.dimensao_sugerida = sugerido
    resultado.escolha_insuficiente = resultado.alerta
    return resultado
