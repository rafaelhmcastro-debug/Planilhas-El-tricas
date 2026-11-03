"""
Probabilidades de dano PX, conforme o Anexo B da NBR 5419-2. Funções puras:
recebem os fatores já resolvidos (valores de tabela) e devolvem o resultado.
Quem resolve as chaves de tabela em valores é a orquestração (riscos.py).
"""


def pa(pta: float, pb: float) -> float:
    """PA: choque por descarga na estrutura (Equação B.1). PA = PTA × PB.

    pta: produto dos valores de PTA para cada medida de proteção adotada (B.2.2).
    """
    return pta * pb


def pc(pspd: float, cld: float) -> float:
    """PC: falha de sistemas internos por descarga na estrutura (Equação B.2). PC = PSPD × CLD."""
    return pspd * cld


def ks1_ks2(largura_malha_m: float | None) -> float:
    """KS1 ou KS2: eficiência de uma blindagem tipo malha (Equação B.5/B.6). KS = 0,12 × wm.

    Sem informação de blindagem (largura_malha_m=None), assume-se KS=1 (nenhuma
    blindagem adicional considerada) — simplificação da v1, que não modela o
    SPDA em detalhe (isso é assunto da Parte 3). Resultado limitado a no máximo 1.
    """
    if largura_malha_m is None:
        return 1.0
    return min(1.0, 0.12 * largura_malha_m)


def ks4(uw_kv: float) -> float:
    """KS4: tensão suportável nominal de impulso do sistema a proteger (Equação B.7). KS4 = 1/UW, máx. 1."""
    return min(1.0, 1.0 / uw_kv)


def pms(ks1: float, ks2: float, ks3: float, ks4_valor: float) -> float:
    """PMS (Equação B.4). PMS = (KS1 × KS2 × KS3 × KS4)²."""
    return (ks1 * ks2 * ks3 * ks4_valor) ** 2


def pm(pspd: float, pms_valor: float) -> float:
    """PM: falha de sistemas internos por descarga próxima à estrutura (Equação B.3). PM = PSPD × PMS.

    Sem DPS coordenado, use pspd=1,0 (valor da própria Tabela B.3 para "nenhum
    sistema coordenado de DPS"), o que reduz a equação a PM = PMS (B.4.8).
    """
    return pspd * pms_valor


def pu(ptu: float, peb: float, pld: float, cld: float) -> float:
    """PU: choque por descarga na linha elétrica conectada (Equação B.8). PU = PTU × PEB × PLD × CLD."""
    return ptu * peb * pld * cld


def pv(peb: float, pld: float, cld: float) -> float:
    """PV: danos físicos por descarga na linha elétrica conectada (Equação B.9). PV = PEB × PLD × CLD."""
    return peb * pld * cld


def pw(pspd: float, pld: float, cld: float) -> float:
    """PW: falha de sistemas internos por descarga na linha elétrica conectada (Equação B.10). PW = PSPD × PLD × CLD."""
    return pspd * pld * cld


def pz(pspd: float, pli: float, cli: float) -> float:
    """PZ: falha de sistemas internos por descarga próxima à linha elétrica (Equação B.11). PZ = PSPD × PLI × CLI."""
    return pspd * pli * cli
