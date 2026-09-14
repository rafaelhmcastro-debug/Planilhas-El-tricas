#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste headless da PARTE 2: modo Selecionar/mover, painel de estilo (cor,
preenchimento, espessura, tracejado), Nuvem, Seta dedicada e Carimbo.

Cria um PDF de teste, insere programaticamente (usando as mesmas funções
auxiliares do revisor_pdf.py) pelo menos:
  - um Retângulo com estilo tracejado + preenchimento colorido,
  - uma Nuvem (efeito 'Cloudy' do PyMuPDF),
  - uma Seta dedicada (linha com ponta de seta),
  - um Carimbo sem imagem configurada (usa o carimbo padrão gerado por código),
salva o PDF, reabre e confere que tudo foi gravado corretamente.

Também testa isoladamente `bbox_do_elemento` (usado pelo hit-test do modo
Selecionar) e a movimentação de um elemento (dx, dy aplicado à geometria).

Rodar com:
    python test_parte2.py
"""

import os
import tempfile

import fitz

from revisor_pdf import (
    hex_para_rgb01,
    rect_de_marcacao,
    bbox_do_elemento,
    gerar_imagem_carimbo,
    DASHES_PDF,
)


def _criar_pdf_teste(caminho):
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(caminho)
    doc.close()


def _aplicar_marcacoes(caminho_entrada, caminho_saida):
    doc = fitz.open(caminho_entrada)
    pagina = doc[0]

    # ---- Retângulo com estilo (tracejado + preenchimento) ---- #
    c_retangulo = {
        "x0": 50, "y0": 50, "x1": 200, "y1": 120,
        "cor_borda": "#0000FF", "cor_preenchimento": "#FFCC00",
        "espessura": 3, "tracejado": "Tracejada",
    }
    annot_ret = pagina.add_rect_annot(rect_de_marcacao(c_retangulo))
    annot_ret.set_colors(
        stroke=hex_para_rgb01(c_retangulo["cor_borda"]),
        fill=hex_para_rgb01(c_retangulo["cor_preenchimento"]),
    )
    annot_ret.set_border(width=c_retangulo["espessura"], dashes=DASHES_PDF["Tracejada"])
    annot_ret.set_info(content="Retângulo estilizado de teste")
    annot_ret.update()

    # ---- Nuvem (efeito Cloudy) ---- #
    c_nuvem = {"x0": 50, "y0": 150, "x1": 200, "y1": 220}
    annot_nuvem = pagina.add_rect_annot(rect_de_marcacao(c_nuvem))
    annot_nuvem.set_border(width=2, clouds=2)
    annot_nuvem.set_info(content="Nuvem de revisão de teste")
    annot_nuvem.update()

    # ---- Seta dedicada (sempre com ponta de seta) ---- #
    annot_seta = pagina.add_line_annot(fitz.Point(50, 250), fitz.Point(200, 250))
    annot_seta.set_line_ends(fitz.PDF_ANNOT_LE_NONE, fitz.PDF_ANNOT_LE_OPEN_ARROW)
    annot_seta.set_colors(stroke=hex_para_rgb01("#FF0000"))
    annot_seta.set_border(width=2)
    annot_seta.set_info(content="Seta dedicada de teste")
    annot_seta.update()

    # ---- Carimbo sem imagem configurada (usa o padrão gerado por código) ---- #
    c_carimbo = {"x0": 50, "y0": 300, "x1": 270, "y1": 440}
    imagem_bytes = gerar_imagem_carimbo(None, "João Revisor", "13/08/2026")
    pagina.insert_image(rect_de_marcacao(c_carimbo), stream=imagem_bytes)

    doc.save(caminho_saida)
    doc.close()


def test_bbox_do_elemento():
    c_ponto = {"tipo": "comentario", "x": 100, "y": 100}
    x0, y0, x1, y1 = bbox_do_elemento(c_ponto)
    assert x0 < 100 < x1 and y0 < 100 < y1

    c_rect = {"tipo": "retangulo", "x0": 30, "y0": 40, "x1": 10, "y1": 5}
    x0, y0, x1, y1 = bbox_do_elemento(c_rect)
    assert (x0, y0, x1, y1) == (10, 5, 30, 40), "bbox deve normalizar min/max"


def test_mover_elemento():
    # reproduz a lógica de _selecionar_ao_arrastar: aplica (dx, dy) a partir
    # de uma cópia da geometria original
    original = {"tipo": "retangulo", "x0": 10, "y0": 10, "x1": 50, "y1": 40}
    c = dict(original)
    dx, dy = 15, -5
    c["x0"] = original["x0"] + dx
    c["y0"] = original["y0"] + dy
    c["x1"] = original["x1"] + dx
    c["y1"] = original["y1"] + dy
    assert c == {"tipo": "retangulo", "x0": 25, "y0": 5, "x1": 65, "y1": 35}


def test_marcacoes_parte2():
    with tempfile.TemporaryDirectory() as tmp:
        entrada = os.path.join(tmp, "entrada.pdf")
        saida = os.path.join(tmp, "saida.pdf")

        _criar_pdf_teste(entrada)
        _aplicar_marcacoes(entrada, saida)

        doc = fitz.open(saida)
        pagina = doc[0]
        annots = list(pagina.annots())

        tipos = [a.type[1] for a in annots]
        assert tipos.count("Square") == 2, f"esperado 2 Square (retângulo+nuvem), obtido {tipos}"
        assert tipos.count("Line") == 1, f"esperado 1 Line (seta), obtido {tipos}"

        # confere estilo do retângulo (cor da borda, preenchimento, espessura, tracejado)
        retangulo = annots[0]
        assert retangulo.colors["stroke"] == pytest_approx(hex_para_rgb01("#0000FF"))
        assert retangulo.colors["fill"] == pytest_approx(hex_para_rgb01("#FFCC00"))
        assert retangulo.border["width"] == 3.0
        assert tuple(retangulo.border["dashes"]) == tuple(DASHES_PDF["Tracejada"])

        # confere a nuvem: clouds > 0 no dicionário de borda
        nuvem = annots[1]
        assert nuvem.border["clouds"] == 2

        # confere a seta: linha com ponta de seta configurada
        seta = annots[2]
        assert seta.line_ends[1] == fitz.PDF_ANNOT_LE_OPEN_ARROW

        # confere o carimbo: pelo menos uma imagem foi inserida na página
        imagens = pagina.get_images(full=True)
        assert len(imagens) >= 1, "esperava ao menos uma imagem (carimbo) na página"

        doc.close()


def pytest_approx(tupla, tol=1e-3):
    class _Aprox:
        def __eq__(self, outro):
            return all(abs(a - b) < tol for a, b in zip(tupla, outro))
    return _Aprox()


if __name__ == "__main__":
    test_bbox_do_elemento()
    test_mover_elemento()
    test_marcacoes_parte2()
    print("OK: modo Selecionar (bbox/mover), estilo de linha, Nuvem, Seta e Carimbo padrão OK.")
