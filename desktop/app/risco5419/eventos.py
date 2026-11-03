"""
Número médio anual de eventos perigosos (N) e áreas de exposição equivalentes,
conforme o Anexo A da NBR 5419-2. Funções puras: recebem os parâmetros já
resolvidos (NG, dimensões, fatores de tabela) e devolvem o resultado — quem
resolve NG e os fatores de tabela é o chamador (ng.py / tabelas.py).
"""
import math


def area_ad(comprimento_m: float, largura_m: float, altura_m: float) -> float:
    """AD de uma estrutura retangular isolada em solo plano (Equação A.1).

    AD = L×W + 2×(3×H)×(L+W) + π×(3×H)²
    """
    l, w, h = comprimento_m, largura_m, altura_m
    return l * w + 2 * (3 * h) * (l + w) + math.pi * (3 * h) ** 2


def area_ad_salicencia(altura_saliencia_m: float) -> float:
    """AD' de uma saliência elevada na cobertura (Equação A.2). AD' = π×(3×HP)²."""
    return math.pi * (3 * altura_saliencia_m) ** 2


def area_am(comprimento_m: float, largura_m: float) -> float:
    """AM: área de exposição para descargas próximas à estrutura, raio 500 m (Equação A.6).

    AM = 2×500×(L+W) + π×500²
    """
    return 2 * 500 * (comprimento_m + largura_m) + math.pi * 500 ** 2


def area_al(comprimento_trecho_m: float) -> float:
    """AL: área de exposição para descarga na linha elétrica (Equação A.8). AL = 40 × LL."""
    return 40 * comprimento_trecho_m


def area_al_solo_alta_resistividade(comprimento_trecho_m: float, resistividade_ohm_m: float) -> float:
    """AL para trecho enterrado com resistividade do solo ρ > 400 Ω·m (Tabela A.2, Nota 1).

    AL = 0,6 × √ρ × LL
    """
    return 0.6 * math.sqrt(resistividade_ohm_m) * comprimento_trecho_m


def area_ai(comprimento_trecho_m: float) -> float:
    """AI: área de exposição para descarga próxima à linha elétrica (Equação A.10). AI = 4000 × LL."""
    return 4000 * comprimento_trecho_m


def nd(ng: float, ad_m2: float, cd: float) -> float:
    """ND: eventos perigosos por descarga na estrutura (Equação A.3). ND = NG × AD × CD × 10⁻⁶."""
    return ng * ad_m2 * cd * 1e-6


def ndj(ng: float, adj_m2: float, cdj: float, ct: float) -> float:
    """NDJ: eventos perigosos na estrutura adjacente, na ponta da linha (Equação A.4).

    NDJ = NG × ADJ × CDJ × CT × 10⁻⁶
    """
    return ng * adj_m2 * cdj * ct * 1e-6


def nm(ng: float, am_m2: float) -> float:
    """NM: eventos perigosos por descarga próxima à estrutura (Equação A.5). NM = NG × AM × 10⁻⁶."""
    return ng * am_m2 * 1e-6


def nl(ng: float, al_m2: float, ci: float, ce: float, ct: float) -> float:
    """NL: eventos perigosos por descarga na linha elétrica (Equação A.7). NL = NG × AL × CI × CE × CT × 10⁻⁶."""
    return ng * al_m2 * ci * ce * ct * 1e-6


def ni(ng: float, ai_m2: float, ci: float, ce: float, ct: float) -> float:
    """NI: eventos perigosos por descarga próxima à linha elétrica (Equação A.9). NI = NG × AI × CI × CE × CT × 10⁻⁶."""
    return ng * ai_m2 * ci * ce * ct * 1e-6
