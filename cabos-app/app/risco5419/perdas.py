"""
Perdas consequentes LX, conforme o Anexo C (R1, R3) e o Anexo D (R4) da
NBR 5419-2. Funções puras: recebem os fatores já resolvidos e devolvem o
resultado. LA=LU, LB=LV e LC=LM=LW=LZ têm, cada par, a mesma fórmula
(Tabela 5) — por isso uma função só cobre os dois símbolos em cada caso.
"""


def perda_choque_r1(rt: float, lt: float, nz: float, nt: float, tz: float, rs: float) -> float:
    """LA = LU (perda de vida por choque, R1) — Equações C.1/C.2.

    LA = LU = rt × LT × (nz/nt) × (tz/8760) × rs
    """
    if nt <= 0:
        raise ValueError("nt (total de pessoas na estrutura) deve ser maior que zero.")
    return rt * lt * (nz / nt) * (tz / 8760) * rs


def perda_fisica_r1(rp: float, rf: float, hz: float, lf: float, nz: float, nt: float, tz: float, rs: float) -> float:
    """LB = LV (perda de vida por dano físico, R1) — Equação C.3.

    LB = LV = rp × rf × hz × LF × (nz/nt) × (tz/8760) × rs
    """
    if nt <= 0:
        raise ValueError("nt (total de pessoas na estrutura) deve ser maior que zero.")
    return rp * rf * hz * lf * (nz / nt) * (tz / 8760) * rs


def perda_sistema_interno_r1(lo: float, nz: float, nt: float, tz: float, rs: float) -> float:
    """LC = LM = LW = LZ (perda de vida por falha de sistema interno, R1) — Equação C.4.

    LC = LM = LW = LZ = LO × (nz/nt) × (tz/8760) × rs
    """
    if nt <= 0:
        raise ValueError("nt (total de pessoas na estrutura) deve ser maior que zero.")
    return lo * (nz / nt) * (tz / 8760) * rs


def perda_fisica_r3(rp: float, rf: float, lf: float, cz: float, ct: float) -> float:
    """LB = LV (perda de patrimônio cultural, R3) — Equação C.7.

    LB = LV = rp × rf × LF × (cz/ct)
    """
    if ct <= 0:
        raise ValueError("ct (valor total da estrutura) deve ser maior que zero.")
    return rp * rf * lf * (cz / ct)


def perda_choque_r4(rt: float, lt: float, ca: float = 1.0, ct: float = 1.0) -> float:
    """LA = LU (perda econômica por choque em animais, R4) — Equações D.1/D.2.

    LA = LU = rt × LT × (ca/ct)

    Por padrão ca=ct=1 (relação neutra): conforme D.1.4-nota, quando a análise
    usa o valor representativo de RT4 da Tabela 4 (em vez do procedimento
    detalhado de 6.10/Anexo D), as relações de valor não são usadas e devem
    ser substituídas por 1. Informe ca e ct explicitamente só se for conduzir
    a análise detalhada com valores econômicos reais.
    """
    if ct <= 0:
        raise ValueError("ct deve ser maior que zero.")
    return rt * lt * (ca / ct)


def perda_fisica_r4(rp: float, rf: float, lf: float, ca: float = 1.0, cb: float = 1.0, cc: float = 1.0, cs: float = 1.0, ct: float = 1.0) -> float:
    """LB = LV (perda econômica por dano físico, R4) — Equação D.3.

    LB = LV = rp × rf × LF × (ca+cb+cc+cs)/ct

    Valores padrão (relação = 1) conforme D.1.4-nota — ver perda_choque_r4.
    """
    if ct <= 0:
        raise ValueError("ct deve ser maior que zero.")
    return rp * rf * lf * ((ca + cb + cc + cs) / ct)


def perda_sistema_interno_r4(lo: float, cs: float = 1.0, ct: float = 1.0) -> float:
    """LC = LM = LW = LZ (perda econômica por falha de sistema interno, R4) — Equação D.4.

    LC = LM = LW = LZ = LO × (cs/ct)

    Valor padrão (relação = 1) conforme D.1.4-nota — ver perda_choque_r4.
    """
    if ct <= 0:
        raise ValueError("ct deve ser maior que zero.")
    return lo * (cs / ct)
