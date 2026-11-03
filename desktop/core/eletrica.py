"""
Constantes e funções auxiliares puras, compartilhadas pelos demais módulos do
núcleo. Portado de `cabos-app/app/calculations.py` (mesmas fórmulas).
"""
import math

# Seções comerciais padrão (mm²) — mesma lista usada na busca de seção mínima.
SECOES_COMERCIAIS = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 500]

# Valor de referência na ausência de reatância no catálogo do cabo escolhido
# (decisão 6 de decisions-and-spec-corrections.md: usa a reatância do catálogo
# quando disponível; cai para este valor típico só na falta dela).
REATANCIA_TIPICA_OHM_KM = 0.08

# Até esta seção (inclusive) usa-se cabo multipolar; a partir de 50 mm² usam-se
# cabos singelos (unipolares).
SECAO_MAX_MULTIPOLAR = 35

# Conversão de unidade de potência para kW (decisão D1: campo único + unidade).
FATOR_UNIDADE_KW = {"kW": 1.0, "W": 0.001, "CV": 0.7355, "HP": 0.7457}


def fmt(v, casas=2):
    """Formata um número no padrão brasileiro (vírgula decimal, ponto de milhar)."""
    if v is None:
        return "-"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def isolacao_grupo(tipo_isolacao: str) -> str:
    """Agrupa o tipo de isolação nas duas famílias usadas pelas tabelas de
    capacidade de condução da NBR 5410: PVC ou EPR/XLPE."""
    return "PVC" if (tipo_isolacao or "").upper() == "PVC" else "EPR_XLPE"


def area_circulo(diametro_mm: float):
    if diametro_mm is None:
        return None
    return math.pi * (diametro_mm / 2) ** 2


def corrente_por_aparente(s_kva, tensao_v, num_fases):
    """I = S / (√3·V) para trifásico; I = S / V para monofásico (F-N) ou
    bifásico (F-F). `S` em kVA, `V` em Volts, `I` resulta em Ampères."""
    if not s_kva or not tensao_v:
        return None
    if num_fases == 3:
        return (s_kva * 1000) / (math.sqrt(3) * tensao_v)
    return (s_kva * 1000) / tensao_v
