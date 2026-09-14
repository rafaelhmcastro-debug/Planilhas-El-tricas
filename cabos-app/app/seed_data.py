"""
Carga inicial das tabelas normativas (NBR 5410) e dos catálogos de cabos
(Prysmian) e infraestrutura (Elecon 2018).

IMPORTANTE: os valores de catálogo abaixo são valores de REFERÊNCIA para o
sistema funcionar de ponta a ponta. Antes de usar em projeto real, atualize-os
pela tela "Configurações" (importação de planilha Excel ou cadastro manual)
com os dados exatos extraídos dos datasheets/catálogos oficiais.
As tabelas de capacidade de condução (NBR 5410, tabelas 36 a 39) também devem
ser conferidas com a edição vigente da norma.
"""
from sqlalchemy.orm import Session
from . import models

SECOES = [0.5, 0.75, 1, 1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 500, 630, 800, 1000]


def seed_if_empty(db: Session):
    if db.query(models.TabCapacidadeConducao).count() == 0:
        _seed_capacidade_conducao(db)
    if db.query(models.TabFatorTemperatura).count() == 0:
        _seed_fator_temperatura(db)
    if db.query(models.TabFatorAgrupamento).count() == 0:
        _seed_fator_agrupamento(db)
    if db.query(models.TabResistividadeCondutor).count() == 0:
        _seed_resistividade(db)
    if db.query(models.TabLimiteOcupacaoEletroduto).count() == 0:
        _seed_limite_ocupacao_eletroduto(db)
    if db.query(models.TabLimiteOcupacaoBandeja).count() == 0:
        db.add(models.TabLimiteOcupacaoBandeja(criterio="camada_unica", folga_percentual=0, espacamento_minimo_mm=0))
    if db.query(models.CatalogoInfraestrutura).count() == 0:
        _seed_catalogo_infraestrutura(db)
    if db.query(models.CatalogoCabo).count() == 0:
        _seed_catalogo_cabos(db)
    db.commit()


def _tab(valores_2c, valores_3c):
    """Monta dicionários {seção: capacidade} a partir de listas na ordem de SECOES (None = não tabelado)."""
    d2 = {s: v for s, v in zip(SECOES, valores_2c) if v is not None}
    d3 = {s: v for s, v in zip(SECOES, valores_3c) if v is not None}
    return d2, d3


# NBR 5410 — Tabelas 36/37 (PVC 70 °C, cobre) e 38/39 (EPR/XLPE 90 °C, cobre), em Ampères.
# Ordem das colunas: 0.5 | 0.75 | 1 | 1.5 | 2.5 | 4 | 6 | 10 | 16 | 25 | 35 | 50 | 70 | 95 | 120 | 150 | 185 | 240 | 300 | 400 | 500 | 630 | 800 | 1000
CAPACIDADE = {
    "PVC": {
        "A1": _tab([7, 9, 11, 14.5, 19.5, 26, 34, 46, 61, 80, 99, 119, 151, 182, 210, 240, 273, 321, 367, 438, 502, 578, 669, 767],
                   [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "A2": _tab([7, 9, 11, 14, 18.5, 25, 32, 43, 57, 75, 92, 110, 139, 167, 192, 219, 248, 291, 334, 398, 456, 526, 609, 698],
                   [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "B1": _tab([9, 11, 14, 17.5, 24, 32, 41, 57, 76, 101, 125, 151, 192, 232, 269, 309, 353, 415, 477, 571, 656, 758, 881, 1012],
                   [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "B2": _tab([9, 11, 13, 16.5, 23, 30, 38, 52, 69, 90, 111, 133, 168, 201, 232, 265, 300, 351, 401, 477, 545, 626, 723, 827],
                   [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "C": _tab([10, 13, 15, 19.5, 27, 36, 46, 63, 85, 112, 138, 168, 213, 258, 299, 344, 392, 461, 530, 634, 729, 843, 978, 1125],
                  [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "D": _tab([12, 15, 18, 22, 29, 38, 47, 63, 81, 104, 125, 148, 183, 216, 246, 278, 312, 361, 408, 478, 540, 614, 700, 792],
                  [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "E": _tab([11, 14, 17, 22, 30, 40, 51, 70, 94, 119, 148, 180, 232, 282, 328, 379, 434, 514, 593, 715, 826, 958, 1118, 1292],
                  [9, 12, 14, 18.5, 25, 34, 43, 60, 80, 101, 126, 153, 196, 238, 276, 319, 364, 430, 497, 597, 689, 798, 930, 1073]),
        "F": _tab([11, 14, 17, 22, 31, 41, 53, 73, 99, 131, 162, 196, 251, 304, 352, 406, 463, 546, 629, 754, 868, 1005, 1169, 1346],
                  [8, 9, 11, 11, 13, 14, 17, 18, 24, 25, 33, 34, 43, 45, 60, 63, 82, 85, 110, 114, 137, 143, 167, 174, 216, 225, 264, 275, 308, 321, 356, 372, 409, 427, 485, 507, 561, 587, 656, 689, 749, 789, 855, 905, 971, 1119, 1079, 1296]),
        "G": _tab([None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
                  [12, 10, 16, 13, 19, 16, 24, 21, 34, 29, 45, 39, 59, 51, 81, 71, 110, 97, 146, 130, 181, 162, 219, 197, 281, 254, 341, 311, 396, 362, 456, 419, 521, 480, 615, 569, 709, 659, 852, 795, 982, 920, 1138, 1070, 1325, 1251, 1528, 1448]),
    },
    "EPR_XLPE": {
        "A1": _tab([10, 12, 15, 19, 26, 35, 45, 61, 81, 106, 131, 158, 200, 241, 278, 318, 362, 424, 486, 579, 664, 765, 885, 1014],
                   [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "A2": _tab([10, 12, 14, 18.5, 25, 33, 42, 57, 76, 99, 121, 145, 183, 220, 253, 290, 329, 386, 442, 527, 604, 696, 805, 923],
                   [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "B1": _tab([12, 15, 18, 23, 31, 42, 54, 75, 100, 133, 164, 198, 253, 306, 354, 407, 464, 546, 628, 751, 864, 998, 1158, 1332],
                   [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "B2": _tab([11, 15, 17, 22, 30, 40, 51, 69, 91, 119, 146, 175, 221, 265, 305, 349, 395, 462, 529, 628, 718, 825, 952, 1088],
                   [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "C": _tab([12, 16, 19, 24, 33, 45, 58, 80, 107, 138, 171, 209, 269, 328, 382, 441, 506, 599, 693, 835, 966, 1122, 1311, 1515],
                  [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "D": _tab([14, 18, 21, 26, 34, 44, 56, 73, 95, 121, 146, 173, 213, 252, 287, 324, 363, 419, 474, 555, 627, 711, 811, 916],
                  [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        "E": _tab([13, 17, 21, 26, 36, 49, 63, 86, 115, 149, 185, 225, 289, 352, 410, 473, 542, 641, 741, 892, 1030, 1196, 1396, 1613],
                  [12, 15, 18, 23, 32, 42, 54, 75, 100, 127, 158, 192, 246, 298, 346, 399, 456, 538, 621, 745, 859, 995, 1159, 1336]),
        "F": _tab([13, 17, 21, 27, 37, 50, 65, 90, 121, 161, 200, 242, 310, 377, 437, 504, 575, 679, 783, 940, 1083, 1254, 1460, 1683],
                  [10, 10, 13, 14, 16, 17, 21, 22, 29, 30, 40, 42, 53, 55, 74, 77, 101, 105, 135, 141, 169, 176, 207, 216, 268, 279, 328, 342, 383, 400, 444, 464, 510, 533, 607, 634, 703, 736, 823, 868, 946, 998, 1088, 1151, 1252, 1328, 1420, 1511]),
        "G": _tab([None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
                  [15, 12, 19, 16, 23, 19, 30, 25, 41, 35, 56, 48, 73, 63, 101, 88, 137, 120, 182, 161, 226, 201, 275, 246, 353, 318, 430, 389, 500, 454, 577, 527, 661, 605, 781, 719, 902, 833, 1085, 1008, 1253, 1169, 1454, 1362, 1696, 1595, 1958, 1849]),
    },
}


def _seed_capacidade_conducao(db):
    for grupo, metodos in CAPACIDADE.items():
        for metodo, (d2, d3) in metodos.items():
            for secao, cap in d2.items():
                db.add(models.TabCapacidadeConducao(isolacao_grupo=grupo, metodo_instalacao=metodo,
                                                    num_condutores_carregados=2, secao_mm2=secao, capacidade_a=cap))
            for secao, cap in d3.items():
                db.add(models.TabCapacidadeConducao(isolacao_grupo=grupo, metodo_instalacao=metodo,
                                                    num_condutores_carregados=3, secao_mm2=secao, capacidade_a=cap))


def _seed_fator_temperatura(db):
    # NBR 5410 Tabela 40 — ambiente (ar) — cobre
    pvc = {10: 1.22, 15: 1.17, 20: 1.12, 25: 1.06, 30: 1.00, 35: 0.94, 40: 0.87, 45: 0.79, 50: 0.71, 55: 0.61, 60: 0.50}
    xlpe = {10: 1.15, 15: 1.12, 20: 1.08, 25: 1.04, 30: 1.00, 35: 0.96, 40: 0.91, 45: 0.87, 50: 0.82,
            55: 0.76, 60: 0.71, 65: 0.65, 70: 0.58, 75: 0.50, 80: 0.41}
    for temp, fator in pvc.items():
        db.add(models.TabFatorTemperatura(isolacao_grupo="PVC", temperatura_c=temp, fator=fator))
    for temp, fator in xlpe.items():
        db.add(models.TabFatorTemperatura(isolacao_grupo="EPR_XLPE", temperatura_c=temp, fator=fator))


def _seed_fator_agrupamento(db):
    # NBR 5410 Tabela 42 — circuitos agrupados em feixe / camada única
    valores = {1: 1.00, 2: 0.80, 3: 0.70, 4: 0.65, 5: 0.60, 6: 0.57, 7: 0.54, 8: 0.52,
               9: 0.50, 12: 0.45, 16: 0.41, 20: 0.38}
    for n, f in valores.items():
        db.add(models.TabFatorAgrupamento(num_circuitos=n, fator=f))


RESISTENCIA_COBRE = {1.5: 12.1, 2.5: 7.41, 4: 4.61, 6: 3.08, 10: 1.83, 16: 1.15, 25: 0.727,
                     35: 0.524, 50: 0.387, 70: 0.268, 95: 0.193, 120: 0.153, 150: 0.124,
                     185: 0.0991, 240: 0.0754, 300: 0.0601, 400: 0.047, 500: 0.0366}


def _seed_resistividade(db):
    for secao, r in RESISTENCIA_COBRE.items():
        db.add(models.TabResistividadeCondutor(secao_mm2=secao, resistencia_ohm_km=r))


def _seed_limite_ocupacao_eletroduto(db):
    db.add(models.TabLimiteOcupacaoEletroduto(num_cabos="1", taxa_max_pct=53))
    db.add(models.TabLimiteOcupacaoEletroduto(num_cabos="2", taxa_max_pct=31))
    db.add(models.TabLimiteOcupacaoEletroduto(num_cabos="3+", taxa_max_pct=40))


def _add_eletroduto(db, linha, dn_mm, dn_pol, parede, ext, interno_direto=None):
    interno = interno_direto if interno_direto is not None else (ext - 2 * parede)
    area = 3.14159265 * (interno / 2) ** 2
    db.add(models.CatalogoInfraestrutura(
        fabricante="Elecon", linha_produto=linha, tipo="eletroduto",
        diametro_nominal_pol=dn_pol, diametro_nominal_mm=dn_mm, parede_mm=parede,
        diametro_externo_mm=ext, diametro_interno_mm=round(interno, 2), area_util_mm2=round(area, 1),
        fonte_datasheet="Catálogo Elecon 2018",
    ))


def _add_bandeja(db, linha, tipo, largura, altura, largura_util, fonte="Catálogo Elecon 2018", customizado=False):
    db.add(models.CatalogoInfraestrutura(
        fabricante="Elecon", linha_produto=linha, tipo=tipo,
        largura_nominal_mm=largura, altura_nominal_mm=altura, largura_util_mm=largura_util,
        fonte_datasheet=fonte, customizado=customizado,
    ))


def _seed_catalogo_infraestrutura(db):
    medio = [
        (15, '1/2"', 0.90, 20.40), (20, '3/4"', 0.90, 25.40), (25, '1"', 0.90, 31.90),
        (32, '1.1/4"', 0.90, 38.10), (40, '1.1/2"', 1.00, 44.50), (50, '2"', 0.90, 59.00),
        (65, '2.1/2"', 1.20, 75.00), (80, '3"', 1.35, 88.50), (100, '4"', 1.50, 114.30),
    ]
    for dn, pol, parede, ext in medio:
        _add_eletroduto(db, "Eletroduto Rígido Médio Eletrolítico/Pré-Zincado", dn, pol, parede, ext)

    pesado = [
        (25, '1"', 1.50, 31.90), (32, '1.1/4"', 1.60, 38.10), (40, '1.1/2"', 1.80, 44.50),
        (50, '2"', 2.25, 59.00), (65, '2.1/2"', 2.65, 75.00), (80, '3"', 3.05, 88.50), (100, '4"', 3.40, 114.30),
    ]
    for dn, pol, parede, ext in pesado:
        _add_eletroduto(db, "Eletroduto Rígido Pesado NBR 13057", dn, pol, parede, ext)

    galvanizado = [
        (25, '1"', 2.65, 33.70), (32, '1.1/4"', 2.65, 42.40), (40, '1.1/2"', 2.65, 48.30),
        (50, '2"', 2.65, 60.30), (65, '2.1/2"', 3.35, 73.00), (80, '3"', 3.35, 88.90), (100, '4"', 3.35, 114.30),
    ]
    for dn, pol, parede, ext in galvanizado:
        _add_eletroduto(db, "Eletroduto Galvanizado à Fogo (RIR) NBR 5597", dn, pol, parede, ext)

    aluminio = [
        (25, '1"', 3.38, 33.40, 26.64), (32, '1.1/4"', 3.56, 42.20, 35.08),
        (40, '1.1/2"', 3.68, 48.30, 40.94), (50, '2"', 3.91, 60.30, 52.48),
    ]
    for dn, pol, parede, ext, interno in aluminio:
        _add_eletroduto(db, "Eletroduto Alumínio SCH-40", dn, pol, parede, ext, interno_direto=interno)

    pvc = [
        (20, '3/4"', 1.50, 25.00), (25, '1"', 1.60, 32.00), (32, '1.1/4"', 1.80, 40.00),
        (40, '1.1/2"', 2.00, 46.00), (50, '2"', 2.20, 58.00), (60, '2.1/2"', 2.50, 73.00),
    ]
    for dn, pol, parede, ext in pvc:
        _add_eletroduto(db, "Eletroduto PVC NBR 15465", dn, pol, parede, ext)

    _add_bandeja(db, "Perfilado 38x19", "perfilado", 38, 19, 38)
    _add_bandeja(db, "Perfilado 38x38", "perfilado", 38, 38, 38)
    _add_bandeja(db, "Perfilado 76x38", "perfilado", 76, 38, 76)

    _add_bandeja(db, "Leito para cabo 250mm", "leito", 250, 100, 250)
    _add_bandeja(db, "Leito para cabo 500mm", "leito", 500, 100, 500)

    for largura in [50, 75, 100, 150, 200, 300, 400, 500, 600]:
        _add_bandeja(db, f"Eletrocalha Perfurada {largura}mm", "eletrocalha", largura, 50, largura)


# Diâmetros externos típicos (mm) — valores de referência a substituir pelo datasheet real
DIAM_UNIPOLAR = {1.5: 3.4, 2.5: 3.9, 4: 4.4, 6: 4.9, 10: 6.2, 16: 7.3, 25: 8.7,
                 35: 9.9, 50: 11.4, 70: 13.3, 95: 15.3, 120: 16.9, 150: 18.7,
                 185: 20.8, 240: 23.7, 300: 26.2}
# Multipolares (2, 3, 4 e 5 vias) — só até 35 mm² (acima disso usam-se singelos)
DIAM_MULTIPOLAR = {
    2: {1.5: 8.6, 2.5: 9.6, 4: 10.8, 6: 12.0, 10: 14.4, 16: 16.6, 25: 20.6, 35: 22.6},
    3: {1.5: 9.0, 2.5: 10.1, 4: 11.4, 6: 12.7, 10: 15.3, 16: 17.7, 25: 21.9, 35: 24.2},
    4: {1.5: 9.8, 2.5: 11.0, 4: 12.5, 6: 13.9, 10: 16.9, 16: 19.6, 25: 24.4, 35: 27.0},
    5: {1.5: 10.6, 2.5: 12.0, 4: 13.7, 6: 15.3, 10: 18.6, 16: 21.7, 25: 27.2, 35: 30.1},
}
PESO_UNIPOLAR = {1.5: 20, 2.5: 28, 4: 40, 6: 55, 10: 85, 16: 130, 25: 195, 35: 260, 50: 350,
                 70: 480, 95: 630, 120: 780, 150: 950, 185: 1150, 240: 1480, 300: 1830}


def _seed_catalogo_cabos(db):
    linhas = [
        ("Afumex Green 1kV", "energia BT", "XLPE", "0,6/1 kV", False, "NBR 13248", True),
        ("Afumex Green 750V", "energia BT", "HEPR", "450/750 V", False, "NBR 13248", True),
        ("Sintenax Flex 1kV", "energia BT", "PVC", "0,6/1 kV", False, "NBR 7288", True),
        ("Multiplex", "energia BT aérea", "PVC", "0,6/1 kV", False, "NBR 8182", False),
        ("Sintenax CTL BFC Flex", "controle blindado", "EPR", "0,6/1 kV", True, "NBR 7289", True),
    ]
    fonte = "SEED - valores de referência; substituir pelo datasheet real"
    for linha, aplicacao, isolacao, tensao, blindagem, norma, tem_multipolar in linhas:
        for secao, diam in DIAM_UNIPOLAR.items():
            db.add(models.CatalogoCabo(
                fabricante="Prysmian", linha_produto=linha, aplicacao=aplicacao, material_condutor="cobre",
                tipo_isolacao=isolacao, possui_blindagem=blindagem, tensao_isolamento=tensao,
                construcao_basica=f"1x{secao:g}", num_condutores=1, secao_nominal_mm2=secao,
                diametro_externo_nominal_mm=diam, peso_kg_km=PESO_UNIPOLAR.get(secao),
                resistencia_condutor_20c_ohm_km=RESISTENCIA_COBRE.get(secao),
                norma_referencia=norma, fonte_datasheet=fonte,
            ))
        if not tem_multipolar:
            continue
        for vias, tabela in DIAM_MULTIPOLAR.items():
            for secao, diam in tabela.items():
                db.add(models.CatalogoCabo(
                    fabricante="Prysmian", linha_produto=linha, aplicacao=aplicacao, material_condutor="cobre",
                    tipo_isolacao=isolacao, possui_blindagem=blindagem, tensao_isolamento=tensao,
                    construcao_basica=f"{vias}x{secao:g}", num_condutores=vias, secao_nominal_mm2=secao,
                    diametro_externo_nominal_mm=diam,
                    peso_kg_km=(PESO_UNIPOLAR.get(secao) or 0) * vias * 1.15,
                    resistencia_condutor_20c_ohm_km=RESISTENCIA_COBRE.get(secao),
                    norma_referencia=norma, fonte_datasheet=fonte,
                ))
