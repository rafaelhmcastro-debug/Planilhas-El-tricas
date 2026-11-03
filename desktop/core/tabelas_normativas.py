"""
Buscas sobre as tabelas normativas (NBR 5410), recebidas já carregadas como
listas de dicionários — quem carrega do banco (ou de um arquivo de dados
local) é a camada `app/`; aqui só a lógica de busca/interpolação.

Portado de `cabos-app/app/calculations.py` (_capacidade_tabela,
_fator_temperatura, _fator_agrupamento, _resistencia_secao,
_limite_ocupacao_eletroduto), mantendo exatamente as mesmas regras.
"""


def capacidade_tabela(linhas, grupo, metodo, num_condutores, secao):
    """Capacidade de condução tabelada (A) para a combinação exata de grupo de
    isolação, método de instalação, nº de condutores carregados e seção — ou
    `None` se a combinação não constar na tabela.

    `linhas`: lista de dicts com `isolacao_grupo`, `metodo_instalacao`,
    `num_condutores_carregados`, `secao_mm2`, `capacidade_a`.
    """
    for r in linhas:
        if (r["isolacao_grupo"] == grupo and r["metodo_instalacao"] == metodo
                and r["num_condutores_carregados"] == num_condutores and r["secao_mm2"] == secao):
            return r["capacidade_a"]
    return None


def fator_temperatura(linhas, grupo, temperatura):
    """Fator de correção por temperatura ambiente, com interpolação linear
    entre os pontos tabelados; fora da faixa tabelada, usa o valor da ponta
    mais próxima (sem extrapolar). Sem nenhuma linha para o grupo, retorna 1.0
    (sem correção) — mesma regra do código web atual.

    `linhas`: lista de dicts com `isolacao_grupo`, `temperatura_c`, `fator`.
    """
    rows = sorted((r for r in linhas if r["isolacao_grupo"] == grupo), key=lambda r: r["temperatura_c"])
    if not rows:
        return 1.0
    if temperatura is None:
        temperatura = 30
    if temperatura <= rows[0]["temperatura_c"]:
        return rows[0]["fator"]
    if temperatura >= rows[-1]["temperatura_c"]:
        return rows[-1]["fator"]
    for a, b in zip(rows, rows[1:]):
        if a["temperatura_c"] <= temperatura <= b["temperatura_c"]:
            if a["temperatura_c"] == temperatura:
                return a["fator"]
            frac = (temperatura - a["temperatura_c"]) / (b["temperatura_c"] - a["temperatura_c"])
            return a["fator"] + frac * (b["fator"] - a["fator"])
    return 1.0


def fator_agrupamento(linhas, num_circuitos):
    """Fator de correção por agrupamento de circuitos. Sem correspondência
    exata, usa o fator do próximo nº de circuitos tabelado para cima (mais
    conservador); acima do maior valor tabelado, usa o fator do maior nº de
    circuitos tabelado.

    `linhas`: lista de dicts com `num_circuitos`, `fator`.
    """
    rows = sorted(linhas, key=lambda r: r["num_circuitos"])
    if not rows:
        return 1.0
    exato = [r for r in rows if r["num_circuitos"] == num_circuitos]
    if exato:
        return exato[0]["fator"]
    maiores = [r for r in rows if r["num_circuitos"] >= num_circuitos]
    if maiores:
        return maiores[0]["fator"]
    return rows[-1]["fator"]


def resistencia_secao(linhas, secao):
    """`linhas`: lista de dicts com `secao_mm2`, `resistencia_ohm_km`."""
    for r in linhas:
        if r["secao_mm2"] == secao:
            return r["resistencia_ohm_km"]
    return None


def limite_ocupacao_eletroduto(linhas, num_cabos):
    """Taxa de ocupação máxima (%) conforme o nº de cabos físicos no trecho
    (regra 10a: 1 cabo = 53%, 2 cabos = 31%, 3+ cabos = 40%). Sem a tabela
    carregada, usa 40% como padrão — mesma regra do código web atual.

    `linhas`: lista de dicts com `num_cabos` ("1"/"2"/"3+"), `taxa_max_pct`.
    """
    bucket = "1" if num_cabos == 1 else ("2" if num_cabos == 2 else "3+")
    for r in linhas:
        if r["num_cabos"] == bucket:
            return r["taxa_max_pct"]
    return 40.0
