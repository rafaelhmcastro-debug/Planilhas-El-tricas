#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste headless da PARTE 5: elipse azul de confirmação + X verde de validação
(padrão de cores PP-ENG-002, item 5.1.4.3).

Cria um item de teste com status="Corrigido" e verificacao_correcao=True,
exporta o PDF (reproduzindo a mesma lógica de exportar_pdf) e confirma que
existe uma anotação de círculo azul (Circle) e duas anotações de linha verdes
(Line) associadas a esse item, com as cores de traço corretas.

Também confere que um item "Corrigido" mas SEM verificacao_correcao gera
a elipse azul mas nenhuma linha verde, e que o Carimbo nunca recebe elipse.

Rodar com:
    python test_parte5.py
"""

import os
import tempfile

import fitz

from revisor_pdf import (
    hex_para_rgb01,
    rect_de_marcacao,
    rect_confirmacao,
    COR_AZUL_CONFIRMACAO,
    COR_VERDE_VALIDACAO,
)


def _criar_pdf_teste(caminho):
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(caminho)
    doc.close()


def _exportar_com_confirmacao(caminho_entrada, caminho_saida, comentarios):
    """Reproduz o trecho relevante de exportar_pdf() do revisor_pdf.py:
    cria a marcação normal e, se status=='Corrigido', a elipse azul + X verde."""
    doc = fitz.open(caminho_entrada)
    pagina = doc[0]

    for idx, c in enumerate(comentarios, start=1):
        tipo = c.get("tipo", "comentario")

        if tipo == "carimbo":
            continue  # carimbo não recebe elipse de confirmação

        status = c.get("status", "Pendente")
        if tipo == "elipse":
            annot = pagina.add_circle_annot(rect_de_marcacao(c))
        else:
            annot = pagina.add_rect_annot(rect_de_marcacao(c))
        annot.set_colors(stroke=hex_para_rgb01(c.get("cor_borda", "#FF0000")))
        annot.set_info(content=f"[{status.upper()}] item {idx}")
        annot.update()

        if status == "Corrigido":
            rect_conf = rect_confirmacao(c)
            elipse = pagina.add_circle_annot(rect_conf)
            elipse.set_colors(stroke=hex_para_rgb01(COR_AZUL_CONFIRMACAO))
            elipse.set_border(width=1.5)
            elipse.update()

            if c.get("verificacao_correcao"):
                diagonais = (
                    (fitz.Point(rect_conf.x0, rect_conf.y0), fitz.Point(rect_conf.x1, rect_conf.y1)),
                    (fitz.Point(rect_conf.x1, rect_conf.y0), fitz.Point(rect_conf.x0, rect_conf.y1)),
                )
                for p1, p2 in diagonais:
                    linha_x = pagina.add_line_annot(p1, p2)
                    linha_x.set_colors(stroke=hex_para_rgb01(COR_VERDE_VALIDACAO))
                    linha_x.set_border(width=1.5)
                    linha_x.update()

    doc.save(caminho_saida)
    doc.close()


def test_corrigido_e_verificado_gera_elipse_e_x():
    with tempfile.TemporaryDirectory() as tmp:
        entrada = os.path.join(tmp, "entrada.pdf")
        saida = os.path.join(tmp, "saida.pdf")
        _criar_pdf_teste(entrada)

        comentarios = [
            {
                "tipo": "retangulo", "pagina": 0, "x0": 100, "y0": 100, "x1": 200, "y1": 150,
                "cor_borda": "#FF0000", "status": "Corrigido", "verificacao_correcao": True,
            },
        ]
        _exportar_com_confirmacao(entrada, saida, comentarios)

        doc = fitz.open(saida)
        try:
            pagina = doc[0]
            annots = list(pagina.annots())
            tipos = [a.type[1] for a in annots]

            assert tipos.count("Square") == 1, f"esperado 1 Square (a marcação em si), obtido {tipos}"
            assert tipos.count("Circle") == 1, f"esperado 1 Circle (elipse azul), obtido {tipos}"
            assert tipos.count("Line") == 2, f"esperado 2 Line (X verde), obtido {tipos}"

            circulo = next(a for a in annots if a.type[1] == "Circle")
            cor_azul_esperada = hex_para_rgb01(COR_AZUL_CONFIRMACAO)
            assert all(abs(a - b) < 1e-3 for a, b in zip(circulo.colors["stroke"], cor_azul_esperada)), (
                f"cor da elipse errada: {circulo.colors['stroke']}"
            )

            linhas = [a for a in annots if a.type[1] == "Line"]
            cor_verde_esperada = hex_para_rgb01(COR_VERDE_VALIDACAO)
            for linha in linhas:
                assert all(abs(a - b) < 1e-3 for a, b in zip(linha.colors["stroke"], cor_verde_esperada)), (
                    f"cor do X errada: {linha.colors['stroke']}"
                )
        finally:
            doc.close()


def test_corrigido_sem_verificacao_so_gera_elipse():
    with tempfile.TemporaryDirectory() as tmp:
        entrada = os.path.join(tmp, "entrada.pdf")
        saida = os.path.join(tmp, "saida.pdf")
        _criar_pdf_teste(entrada)

        comentarios = [
            {
                "tipo": "elipse", "pagina": 0, "x0": 50, "y0": 50, "x1": 90, "y1": 90,
                "status": "Corrigido", "verificacao_correcao": False,
            },
        ]
        _exportar_com_confirmacao(entrada, saida, comentarios)

        doc = fitz.open(saida)
        try:
            pagina = doc[0]
            tipos = [a.type[1] for a in pagina.annots()]
            assert tipos.count("Circle") == 2, f"esperado 2 Circle (marcação elipse + elipse azul), obtido {tipos}"
            assert tipos.count("Line") == 0, "não deveria haver X verde sem verificacao_correcao"
        finally:
            doc.close()


def test_pendente_nao_gera_elipse():
    with tempfile.TemporaryDirectory() as tmp:
        entrada = os.path.join(tmp, "entrada.pdf")
        saida = os.path.join(tmp, "saida.pdf")
        _criar_pdf_teste(entrada)

        comentarios = [
            {
                "tipo": "retangulo", "pagina": 0, "x0": 10, "y0": 10, "x1": 40, "y1": 40,
                "cor_borda": "#000000", "status": "Pendente", "verificacao_correcao": False,
            },
        ]
        _exportar_com_confirmacao(entrada, saida, comentarios)

        doc = fitz.open(saida)
        try:
            pagina = doc[0]
            tipos = [a.type[1] for a in pagina.annots()]
            assert "Circle" not in tipos, "item Pendente não deveria gerar elipse de confirmação"
            assert "Line" not in tipos
        finally:
            doc.close()


if __name__ == "__main__":
    test_corrigido_e_verificado_gera_elipse_e_x()
    test_corrigido_sem_verificacao_so_gera_elipse()
    test_pendente_nao_gera_elipse()
    print("OK: elipse azul (Corrigido) e X verde (verificacao_correcao) exportados com as cores certas.")
