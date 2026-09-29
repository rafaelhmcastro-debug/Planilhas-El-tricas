"""
Carrega e valida os coeficientes normativos de dados/*.json (NBR 5419-2).
Nenhuma função aqui decide um valor por conta própria: se o coeficiente
pedido está null ou não existe, o erro aponta exatamente a tabela e a chave
que faltam, para o engenheiro preencher a partir da norma.
"""
import json
from pathlib import Path

DADOS_DIR = Path(__file__).parent / "dados"

_cache: dict[str, dict] = {}


class ValorNaoDisponivel(Exception):
    """Levantado quando um coeficiente necessário está null ou não foi encontrado."""


def _carregar(tabela: str) -> dict:
    if tabela not in _cache:
        caminho = DADOS_DIR / f"{tabela}.json"
        if not caminho.exists():
            raise ValorNaoDisponivel(f'Arquivo de dados "{tabela}.json" não existe em {DADOS_DIR}.')
        with open(caminho, encoding="utf-8") as f:
            _cache[tabela] = json.load(f)
    return _cache[tabela]


def _todas_entradas(dados: dict):
    if "entradas" in dados:
        yield from dados["entradas"]
    for grupo in dados.get("grupos", []):
        yield from grupo.get("entradas", [])


def _entrada(tabela: str, chave: str) -> dict:
    dados = _carregar(tabela)
    for entrada in _todas_entradas(dados):
        if entrada.get("chave") == chave:
            return entrada
    disponiveis = [e.get("chave") for e in _todas_entradas(dados)]
    raise ValorNaoDisponivel(
        f'Chave "{chave}" não encontrada em {tabela} ({dados.get("tabela", tabela)}). '
        f"Chaves disponíveis: {disponiveis}"
    )


def valor(tabela: str, chave: str) -> float:
    """Valor numérico de uma entrada simples (a maioria das tabelas)."""
    entrada = _entrada(tabela, chave)
    v = entrada.get("valor")
    if v is None:
        raise ValorNaoDisponivel(
            f'Valor de "{chave}" em {tabela} ({entrada.get("descricao")}) ainda não foi definido '
            f'(referência: {entrada.get("referencia")}). {entrada.get("observacao", "")}'
        )
    return float(v)


def valor_grupo(tabela: str, grupo: str, chave: str) -> float:
    """Valor de uma entrada dentro de um grupo nomeado (ex.: LT/LF/LO em C.2 e D.2)."""
    dados = _carregar(tabela)
    for g in dados.get("grupos", []):
        if g.get("grupo") == grupo:
            for entrada in g.get("entradas", []):
                if entrada.get("chave") == chave:
                    v = entrada.get("valor")
                    if v is None:
                        raise ValorNaoDisponivel(f'Valor de "{grupo}/{chave}" em {tabela} não foi definido.')
                    return float(v)
            disponiveis = [e.get("chave") for e in g.get("entradas", [])]
            raise ValorNaoDisponivel(f'Chave "{chave}" não encontrada no grupo "{grupo}" de {tabela}. Disponíveis: {disponiveis}')
    grupos_disponiveis = [g.get("grupo") for g in dados.get("grupos", [])]
    raise ValorNaoDisponivel(f'Grupo "{grupo}" não encontrado em {tabela}. Grupos disponíveis: {grupos_disponiveis}')


def cld_cli(chave: str) -> tuple[float, float]:
    """Fatores CLD e CLI (Tabela B.4), que vêm juntos na mesma linha da tabela."""
    entrada = _entrada("anexo_b_tabela_b4_cld_cli", chave)
    return float(entrada["cld"]), float(entrada["cli"])


def valor_por_uw(tabela: str, chave: str, uw_kv: float) -> float:
    """
    Valor de uma tabela 2D indexada por tensão suportável nominal de impulso UW
    (Tabelas B.8 e B.9). Se uw_kv não coincide com uma coluna tabelada, usa a
    coluna imediatamente inferior (mais conservadora — maior probabilidade),
    conforme documentado nas próprias tabelas de dados. Não extrapola abaixo
    da menor coluna: nesse caso, levanta erro em vez de estimar.
    """
    dados = _carregar(tabela)
    colunas = dados["colunas_uw_kv"]
    entrada = _entrada(tabela, chave)
    valores = entrada["valores_por_uw"]

    candidatos = [(col, v) for col, v in zip(colunas, valores) if col <= uw_kv]
    if not candidatos:
        raise ValorNaoDisponivel(
            f"UW = {uw_kv} kV é menor que a menor coluna tabelada em {tabela} ({min(colunas)} kV). "
            "A norma não permite extrapolar para um valor mais conservador que o tabelado; "
            "confirme o UW do equipamento ou trate este caso manualmente."
        )
    col_usada, v = max(candidatos, key=lambda par: par[0])
    return float(v)


def info(tabela: str, chave: str) -> dict:
    """Entrada completa (chave, descricao, valor, referencia) — usado para montar a memória de cálculo."""
    return _entrada(tabela, chave)


def info_grupo(tabela: str, grupo: str, chave: str) -> dict:
    dados = _carregar(tabela)
    for g in dados.get("grupos", []):
        if g.get("grupo") == grupo:
            for entrada in g.get("entradas", []):
                if entrada.get("chave") == chave:
                    return entrada
    raise ValorNaoDisponivel(f'Chave "{chave}" não encontrada no grupo "{grupo}" de {tabela}.')


def limpar_cache():
    """Usado nos testes para forçar releitura dos arquivos JSON."""
    _cache.clear()
