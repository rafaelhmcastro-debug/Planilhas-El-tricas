"""
Orquestra eventos.py, probabilidades.py e perdas.py para calcular R1, R3 e a
frequência de danos F (Seção 7), comparar com os limites toleráveis e montar
a memória de cálculo passo a passo.

Simplificações desta v1 (documentadas, não escondidas):
- NDJ (estrutura adjacente na ponta da linha, 6.5/Fig. A.5) é considerado 0.
  A própria norma permite isso ("em muitos casos, NDJ pode ser desprezado", 6.4.1).
- F (Seção 7) é calculado para a estrutura inteira como uma única zona de estudo
  (7.4.2), não por zona — é o caso mais simples que a norma já prevê.
- R4 (Anexo D) ainda não está implementado aqui.
"""
import json

from . import eventos, probabilidades, perdas, tabelas
from .memoria import MemoriaCalculo, fmt


def _pta_produto(medidas_pta_json: str, mem: MemoriaCalculo) -> float:
    chaves = json.loads(medidas_pta_json or "[]")
    if not chaves:
        mem.registrar("PTA — medidas de proteção contra toque/passo", ["Nenhuma medida informada → PTA = 1 (Tabela B.1)."], 1.0)
        return 1.0
    produto = 1.0
    linhas = []
    for chave in chaves:
        info = tabelas.info("anexo_b_tabela_b1_pta", chave)
        produto *= info["valor"]
        linhas.append(f"{info['descricao']}: PTA = {fmt(info['valor'])} ({info['referencia']}).")
    linhas.append(f"Mais de uma medida adotada → PTA = produto dos valores (B.2.2) = {fmt(produto)}.")
    mem.registrar("PTA — medidas de proteção contra toque/passo", linhas, produto)
    return produto


def _ks_fatores(medidas, mem: MemoriaCalculo):
    ks1 = probabilidades.ks1_ks2(medidas.largura_malha_externa_m)
    ks2 = probabilidades.ks1_ks2(medidas.largura_malha_interna_m)
    ks3_info = tabelas.info("anexo_b_tabela_b5_ks3", medidas.fiacao_interna)
    ks3 = ks3_info["valor"]
    ks4 = probabilidades.ks4(medidas.tensao_suportavel_sistema_interno_kv)
    mem.registrar(
        "Fatores KS1, KS2, KS3, KS4 (para PMS — Equação B.4)",
        [
            f"KS1 = 0,12×wm (Eq. B.5) = {fmt(ks1)}" + (" (sem blindagem espacial informada → KS1=1)." if medidas.largura_malha_externa_m is None else "."),
            f"KS2 = 0,12×wm (Eq. B.6) = {fmt(ks2)}" + (" (sem blindagem interna informada → KS2=1)." if medidas.largura_malha_interna_m is None else "."),
            f"KS3 ({ks3_info['descricao']}) = {fmt(ks3)} ({ks3_info['referencia']}).",
            f"KS4 = 1/UW = 1/{medidas.tensao_suportavel_sistema_interno_kv} = {fmt(ks4)} (Eq. B.7).",
        ],
    )
    return ks1, ks2, ks3, ks4


def _probabilidades_estrutura(medidas, mem: MemoriaCalculo):
    pb_info = tabelas.info("anexo_b_tabela_b2_pb", medidas.classe_spda)
    pb = pb_info["valor"]
    mem.registrar("PB — probabilidade de dano físico (Tabela B.2)", [f"{pb_info['descricao']}: PB = {fmt(pb)} ({pb_info['referencia']})."], pb)

    pta = _pta_produto(medidas.medidas_pta_json, mem)
    pa = probabilidades.pa(pta, pb)
    mem.registrar("PA — choque por descarga na estrutura (Equação B.1)", [f"PA = PTA × PB = {fmt(pta)} × {fmt(pb)} = {fmt(pa)}."], pa)

    pspd_info = tabelas.info("anexo_b_tabela_b3_pspd", medidas.dps_coordenado)
    pspd = pspd_info["valor"]
    mem.registrar("PSPD — DPS coordenado (Tabela B.3)", [f"{pspd_info['descricao']}: PSPD = {fmt(pspd)} ({pspd_info['referencia']})."], pspd)

    peb_info = tabelas.info("anexo_b_tabela_b7_peb", medidas.dps_classe_i)
    peb = peb_info["valor"]
    mem.registrar("PEB — DPS classe I / ligação equipotencial (Tabela B.7)", [f"{peb_info['descricao']}: PEB = {fmt(peb)} ({peb_info['referencia']})."], peb)

    ptu_info = tabelas.info("anexo_b_tabela_b6_ptu", medidas.medida_ptu)
    ptu = ptu_info["valor"]
    mem.registrar("PTU — proteção contra tensão de toque em linha (Tabela B.6)", [f"{ptu_info['descricao']}: PTU = {fmt(ptu)} ({ptu_info['referencia']})."], ptu)

    ks1, ks2, ks3, ks4 = _ks_fatores(medidas, mem)
    pms = probabilidades.pms(ks1, ks2, ks3, ks4)
    mem.registrar("PMS (Equação B.4)", [f"PMS = (KS1×KS2×KS3×KS4)² = ({fmt(ks1)}×{fmt(ks2)}×{fmt(ks3)}×{fmt(ks4)})² = {fmt(pms)}."], pms)
    pm = probabilidades.pm(pspd, pms)
    mem.registrar("PM — falha de sistema interno por descarga próxima (Equação B.3)", [f"PM = PSPD × PMS = {fmt(pspd)} × {fmt(pms)} = {fmt(pm)}."], pm)

    pc = probabilidades.pc(pspd, 1.0)  # CLD estrutura-nível para PC: ver nota abaixo
    return {"pa": pa, "pb": pb, "pspd": pspd, "peb": peb, "ptu": ptu, "pm": pm, "_pc_base": pc}


def _n_estrutura(ng: float, estrutura, mem: MemoriaCalculo):
    cd_info = tabelas.info("anexo_a_tabela_a1_cd", estrutura.fator_localizacao)
    cd = cd_info["valor"]
    ad = eventos.area_ad(estrutura.comprimento_m, estrutura.largura_m, estrutura.altura_m)
    mem.registrar(
        "AD — área de exposição equivalente da estrutura (Equação A.1)",
        [f"AD = L×W + 2×(3×H)×(L+W) + π×(3×H)² = {estrutura.comprimento_m}×{estrutura.largura_m} + 2×(3×{estrutura.altura_m})×({estrutura.comprimento_m}+{estrutura.largura_m}) + π×(3×{estrutura.altura_m})² = {fmt(ad, 1)} m²."],
        ad,
    )
    nd_valor = eventos.nd(ng, ad, cd)
    mem.registrar(
        "ND — eventos perigosos por descarga na estrutura (Equação A.3)",
        [f"CD ({cd_info['descricao']}) = {fmt(cd)} ({cd_info['referencia']}).",
         f"ND = NG × AD × CD × 10⁻⁶ = {ng} × {fmt(ad, 1)} × {fmt(cd)} × 10⁻⁶ = {fmt(nd_valor, 6)}."],
        nd_valor,
    )

    am = eventos.area_am(estrutura.comprimento_m, estrutura.largura_m)
    mem.registrar("AM — área de exposição para descarga próxima à estrutura (Equação A.6)", [f"AM = 2×500×(L+W) + π×500² = {fmt(am, 1)} m²."], am)
    nm_valor = eventos.nm(ng, am)
    mem.registrar("NM — eventos perigosos por descarga próxima à estrutura (Equação A.5)", [f"NM = NG × AM × 10⁻⁶ = {ng} × {fmt(am, 1)} × 10⁻⁶ = {fmt(nm_valor, 6)}."], nm_valor)
    return nd_valor, nm_valor


def _n_e_p_trecho(ng: float, linha, trecho, probs: dict, mem: MemoriaCalculo):
    ci_info = tabelas.info("anexo_a_tabela_a2_ci", trecho.tipo_instalacao)
    ce_info = tabelas.info("anexo_a_tabela_a4_ce", trecho.ambiente)
    ct_chave = "at_com_transformador_at_bt" if linha.tem_transformador_at_bt else "bt_ou_sinal"
    ct_info = tabelas.info("anexo_a_tabela_a3_ct", ct_chave)
    ci, ce, ct = ci_info["valor"], ce_info["valor"], ct_info["valor"]

    al = eventos.area_al(trecho.comprimento_m)
    ai = eventos.area_ai(trecho.comprimento_m)
    nl_valor = eventos.nl(ng, al, ci, ce, ct)
    ni_valor = eventos.ni(ng, ai, ci, ce, ct)
    mem.registrar(
        f'NL, NI — trecho "{linha.tag}" ({fmt(trecho.comprimento_m, 0)} m) — Equações A.7, A.8, A.9, A.10',
        [
            f"CI ({ci_info['descricao']}) = {fmt(ci)} ({ci_info['referencia']}).",
            f"CE ({ce_info['descricao']}) = {fmt(ce)} ({ce_info['referencia']}).",
            f"CT ({ct_info['descricao']}) = {fmt(ct)} ({ct_info['referencia']}).",
            f"AL = 40×LL = {fmt(al, 1)} m²; AI = 4000×LL = {fmt(ai, 1)} m².",
            f"NL = NG×AL×CI×CE×CT×10⁻⁶ = {fmt(nl_valor, 6)}.",
            f"NI = NG×AI×CI×CE×CT×10⁻⁶ = {fmt(ni_valor, 6)}.",
        ],
    )

    cld, cli = tabelas.cld_cli(trecho.categoria_blindagem)
    pld = tabelas.valor_por_uw("anexo_b_tabela_b8_pld", trecho.categoria_pld, linha.tensao_suportavel_kv)
    pli_chave = "linhas_energia" if linha.tipo == "energia" else "linhas_sinal"
    pli = tabelas.valor_por_uw("anexo_b_tabela_b9_pli", pli_chave, linha.tensao_suportavel_kv)

    pu = probabilidades.pu(probs["ptu"], probs["peb"], pld, cld)
    pv = probabilidades.pv(probs["peb"], pld, cld)
    pw = probabilidades.pw(probs["pspd"], pld, cld)
    pz = probabilidades.pz(probs["pspd"], pli, cli)
    mem.registrar(
        f'PU, PV, PW, PZ — trecho "{linha.tag}" (UW = {linha.tensao_suportavel_kv} kV)',
        [
            f"CLD = {fmt(cld)}, CLI = {fmt(cli)} (Tabela B.4).",
            f"PLD = {fmt(pld)} (Tabela B.8, UW = {linha.tensao_suportavel_kv} kV).",
            f"PLI = {fmt(pli)} (Tabela B.9, UW = {linha.tensao_suportavel_kv} kV).",
            f"PU = PTU×PEB×PLD×CLD = {fmt(pu)}.",
            f"PV = PEB×PLD×CLD = {fmt(pv)}.",
            f"PW = PSPD×PLD×CLD = {fmt(pw)}.",
            f"PZ = PSPD×PLI×CLI = {fmt(pz)}.",
        ],
    )
    return {"nl": nl_valor, "ni": ni_valor, "pu": pu, "pv": pv, "pw": pw, "pz": pz}


def _perdas_zona_r1(estrutura, zona, mem: MemoriaCalculo):
    rt_info = tabelas.info("anexo_c_tabela_c3_rt_piso", zona.tipo_piso)
    rp_info = tabelas.info("anexo_c_tabela_c4_rp", zona.providencias_incendio)
    rf_info = tabelas.info("anexo_c_tabela_c5_rf", zona.risco_incendio)
    hz_info = tabelas.info("anexo_c_tabela_c6_hz", zona.perigo_especial)
    rs_info = tabelas.info("anexo_c_tabela_c7_rs", estrutura.tipo_construcao)
    lt = tabelas.valor_grupo("anexo_c_tabela_c2_perdas_r1", "LT", "todos_os_tipos")
    lf = tabelas.valor_grupo("anexo_c_tabela_c2_perdas_r1", "LF", zona.categoria_dano_fisico_lf)
    lo = tabelas.valor_grupo("anexo_c_tabela_c2_perdas_r1", "LO", zona.categoria_falha_sistema_lo)

    rt, rp, rf, hz, rs = rt_info["valor"], rp_info["valor"], rf_info["valor"], hz_info["valor"], rs_info["valor"]
    nz, nt, tz = zona.num_pessoas_zona, estrutura.num_pessoas_total, zona.tempo_pessoas_horas_ano

    la_lu = perdas.perda_choque_r1(rt, lt, nz, nt, tz, rs)
    lb_lv = perdas.perda_fisica_r1(rp, rf, hz, lf, nz, nt, tz, rs)
    lc = perdas.perda_sistema_interno_r1(lo, nz, nt, tz, rs)

    mem.registrar(
        f'Perdas L (R1) — zona "{zona.nome}"',
        [
            f"rt ({rt_info['descricao']}) = {fmt(rt)}; rp ({rp_info['descricao']}) = {fmt(rp)}; "
            f"rf ({rf_info['descricao']}) = {fmt(rf)}; hz ({hz_info['descricao']}) = {fmt(hz)}; rs ({rs_info['descricao']}) = {fmt(rs)}.",
            f"LT = {fmt(lt)}, LF ({zona.categoria_dano_fisico_lf}) = {fmt(lf)}, LO ({zona.categoria_falha_sistema_lo}) = {fmt(lo)}.",
            f"nz/nt = {nz}/{nt}; tz/8760 = {tz}/8760.",
            f"LA = LU = rt×LT×(nz/nt)×(tz/8760)×rs = {fmt(la_lu, 6)}.",
            f"LB = LV = rp×rf×hz×LF×(nz/nt)×(tz/8760)×rs = {fmt(lb_lv, 6)}.",
            f"LC = LM = LW = LZ = LO×(nz/nt)×(tz/8760)×rs = {fmt(lc, 6)}.",
        ],
    )
    return {"la_lu": la_lu, "lb_lv": lb_lv, "lc": lc}


def calcular(estrutura, zonas: list, linhas: list, medidas, ng: float, rt1: float, rt3: float, ft_valor: float) -> tuple[dict, MemoriaCalculo]:
    """Calcula R1, R3 e F para uma análise. `linhas` é uma lista de objetos
    LinhaEletrica já carregados com `.trechos`. Retorna (resultado_dict, memória).
    """
    mem = MemoriaCalculo()
    mem.registrar("Densidade de descargas atmosféricas NG", [f"NG = {ng} raios/km²·ano (ver snapshot da análise)."], ng)

    nd_valor, nm_valor = _n_estrutura(ng, estrutura, mem)
    probs = _probabilidades_estrutura(medidas, mem)

    # PC depende de CLD da linha à qual o sistema interno está conectado (B.4.2).
    # Simplificação: usa o pior caso (maior CLD) entre todas as linhas — 6.4.5/6.5.5
    # já mandam usar a linha de piores características quando há mais de uma.
    cld_pc = 0.0
    if linhas:
        clds = [tabelas.cld_cli(t.categoria_blindagem)[0] for l in linhas for t in l.trechos]
        cld_pc = max(clds) if clds else 0.0
    pc = probabilidades.pc(probs["pspd"], cld_pc)
    mem.registrar(
        "PC — falha de sistema interno por descarga na estrutura (Equação B.2)",
        [f"CLD (pior caso entre as linhas conectadas) = {fmt(cld_pc)}.",
         f"PC = PSPD × CLD = {fmt(probs['pspd'])} × {fmt(cld_pc)} = {fmt(pc)}."],
        pc,
    )

    contrib_trechos = []
    for linha in linhas:
        for trecho in linha.trechos:
            r = _n_e_p_trecho(ng, linha, trecho, probs, mem)
            contrib_trechos.append(r)

    nl_pu_soma = sum(t["nl"] * t["pu"] for t in contrib_trechos)
    nl_pv_soma = sum(t["nl"] * t["pv"] for t in contrib_trechos)
    nl_pw_soma = sum(t["nl"] * t["pw"] for t in contrib_trechos)
    ni_pz_soma = sum(t["ni"] * t["pz"] for t in contrib_trechos)
    nl_peb_soma = sum(t["nl"] * probs["peb"] for t in contrib_trechos)

    aplica_falha_sistema = estrutura.risco_explosao or estrutura.falha_sistema_interno_risco_vida

    r1_total = 0.0
    r3_total = 0.0
    ct_patrimonio = sum(z.valor_patrimonio_cultural for z in zonas if z.valor_patrimonio_cultural) or None
    lf_r3 = None
    if ct_patrimonio:
        lf_r3 = tabelas.valor("anexo_c_tabela_c9_perdas_r3", "museus_galerias")

    for zona in zonas:
        lp = _perdas_zona_r1(estrutura, zona, mem)
        ra = nd_valor * probs["pa"] * lp["la_lu"]
        rb = nd_valor * probs["pb"] * lp["lb_lv"]
        rc = nd_valor * pc * lp["lc"] if aplica_falha_sistema else 0.0
        rm = nm_valor * probs["pm"] * lp["lc"] if aplica_falha_sistema else 0.0
        ru = nl_pu_soma * lp["la_lu"]
        rv = nl_pv_soma * lp["lb_lv"]
        rw = nl_pw_soma * lp["lc"] if aplica_falha_sistema else 0.0
        rz = ni_pz_soma * lp["lc"] if aplica_falha_sistema else 0.0
        r1_zona = ra + rb + rc + rm + ru + rv + rw + rz
        r1_total += r1_zona
        mem.registrar(
            f'Componentes de risco R1 — zona "{zona.nome}" (Equações 4 a 11)',
            [
                f"RA = ND×PA×LA = {fmt(nd_valor,6)}×{fmt(probs['pa'])}×{fmt(lp['la_lu'],6)} = {fmt(ra,8)}.",
                f"RB = ND×PB×LB = {fmt(rb,8)}.",
                f"RC = ND×PC×LC = {fmt(rc,8)}" + ("." if aplica_falha_sistema else " (estrutura sem risco de explosão/vida — RC1 não se aplica, Eq. 1 nota)."),
                f"RM = NM×PM×LM = {fmt(rm,8)}" + ("." if aplica_falha_sistema else " (idem, RM1 não se aplica)."),
                f"RU = Σ(NL×PU) × LU = {fmt(ru,8)}.",
                f"RV = Σ(NL×PV) × LV = {fmt(rv,8)}.",
                f"RW = Σ(NL×PW) × LW = {fmt(rw,8)}" + ("." if aplica_falha_sistema else " (idem, RW1 não se aplica)."),
                f"RZ = Σ(NI×PZ) × LZ = {fmt(rz,8)}" + ("." if aplica_falha_sistema else " (idem, RZ1 não se aplica)."),
            ],
            f"R1 desta zona = {fmt(r1_zona, 8)}",
        )

        if ct_patrimonio and zona.valor_patrimonio_cultural:
            rp_info = tabelas.info("anexo_c_tabela_c4_rp", zona.providencias_incendio)
            rf_info = tabelas.info("anexo_c_tabela_c5_rf", zona.risco_incendio)
            lb3 = perdas.perda_fisica_r3(rp_info["valor"], rf_info["valor"], lf_r3, zona.valor_patrimonio_cultural, ct_patrimonio)
            rb3 = nd_valor * probs["pb"] * lb3
            rv3 = nl_pv_soma * lb3
            r3_zona = rb3 + rv3
            r3_total += r3_zona
            mem.registrar(
                f'Componentes de risco R3 — zona "{zona.nome}" (Equação 2, Tabela C.9)',
                [
                    f"LF (Tabela C.9, museus/galerias) = {fmt(lf_r3)}; cz = {zona.valor_patrimonio_cultural}; ct = {ct_patrimonio}.",
                    f"LB3 = LV3 = rp×rf×LF×(cz/ct) = {fmt(lb3, 6)}.",
                    f"RB3 = ND×PB×LB3 = {fmt(rb3, 8)}.",
                    f"RV3 = Σ(NL×PV) × LV3 = {fmt(rv3, 8)}.",
                ],
                f"R3 desta zona = {fmt(r3_zona, 8)}",
            )

    r1_atende = r1_total <= rt1
    mem.registrar("R1 total e comparação com o risco tolerável (5.4)", [f"R1 = Σ(zonas) = {fmt(r1_total, 8)}.", f"RT1 = {fmt(rt1)}.", f"R1 {'≤' if r1_atende else '>'} RT1 → {'atende' if r1_atende else 'NÃO atende — medidas de proteção adicionais são necessárias (5.4.4)'}."], r1_total)

    resultado_r3 = None
    r3_atende = None
    if ct_patrimonio:
        r3_atende = r3_total <= rt3
        mem.registrar("R3 total e comparação com o risco tolerável (5.4)", [f"R3 = Σ(zonas) = {fmt(r3_total, 8)}.", f"RT3 = {fmt(rt3)}.", f"R3 {'≤' if r3_atende else '>'} RT3 → {'atende' if r3_atende else 'NÃO atende'}."], r3_total)
        resultado_r3 = r3_total

    # Frequência de danos F (Seção 7) — estrutura como zona única (7.4.2).
    fb = nd_valor * probs["pb"]
    fc = nd_valor * pc
    fm = nm_valor * probs["pm"]
    fv = nl_peb_soma
    fw = nl_pw_soma
    fz = ni_pz_soma
    f_total = fb + fc + fm + fv + fw + fz
    f_atende = f_total <= ft_valor
    mem.registrar(
        "Frequência de danos F (Seção 7, Equações 14-15, Tabela 7)",
        [
            f"FB = ND×PB = {fmt(fb, 8)} (nota a: só computa se houver equipamentos em ZPR0A — considerado aqui).",
            f"FC = ND×PC = {fmt(fc, 8)}.",
            f"FM = NM×PM = {fmt(fm, 8)}.",
            f"FV = Σ(NL×PEB) = {fmt(fv, 8)}.",
            f"FW = Σ(NL×PW) = {fmt(fw, 8)}.",
            f"FZ = Σ(NI×PZ) = {fmt(fz, 8)}.",
            f"F = FB+FC+FM+FV+FW+FZ = {fmt(f_total, 8)}.",
            f"FT = {fmt(ft_valor)} (§7.3.4). F {'≤' if f_atende else '>'} FT → {'atende' if f_atende else 'NÃO atende'}.",
        ],
        f_total,
    )

    resultado = {
        "r1": r1_total, "rt1": rt1, "r1_atende": r1_atende,
        "r3": resultado_r3, "rt3": rt3 if ct_patrimonio else None, "r3_atende": r3_atende,
        "f_total": f_total, "ft": ft_valor, "f_atende": f_atende,
    }
    return resultado, mem
