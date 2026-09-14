#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste headless (sem abrir a interface gráfica) das 8 ferramentas de marcação.

Cria um PDF de teste, adiciona uma marcação de cada tipo usando exatamente as
mesmas funções auxiliares e chamadas do PyMuPDF usadas em `exportar_pdf` no
revisor_pdf.py, salva o PDF em disco, reabre e confere que cada anotação foi
gravada com o tipo correto.

Rodar com:
    python test_marcacoes.py
ou com pytest:
    pytest test_marcacoes.py
"""

import os
import tempfile

import fitz

from revisor_pdf import hex_para_rgb01, rect_de_marcacao, rect_texto_livre


def _criar_pdf_teste(caminho):
    doc = fitz.open()
    pagina = doc.new_page(width=595, height=842)  # A4
    pagina.insert_text((72, 100), "Texto de exemplo para sublinhar e tachar.")
    doc.save(caminho)
    doc.close()


def _aplicar_marcacoes(caminho_entrada, caminho_saida):
    """Reproduz o dispatch por tipo de exportar_pdf() do revisor_pdf.py."""
    doc = fitz.open(caminho_entrada)
    pagina = doc[0]

    marcacoes = [
        {"tipo": "comentario", "x": 100, "y": 150, "texto": "Comentário simples",
         "classificacao": "ERRO DE PORTUGUÊS"},
        {"tipo": "texto_livre", "x": 100, "y": 200, "texto": "Texto livre na página",
         "classificacao": "ERRO DE PORTUGUÊS", "fontsize": 14, "cor": "#0000FF"},
        {"tipo": "retangulo", "x0": 100, "y0": 250, "x1": 200, "y1": 300,
         "texto": "Retângulo de marcação", "classificacao": "ERRO DE PORTUGUÊS",
         "cor": "#FF0000"},
        {"tipo": "elipse", "x0": 100, "y0": 320, "x1": 200, "y1": 370,
         "texto": "Elipse de marcação", "classificacao": "ERRO DE PORTUGUÊS"},
        {"tipo": "linha", "x0": 100, "y0": 400, "x1": 200, "y1": 400,
         "texto": "Linha com seta", "classificacao": "ERRO DE PORTUGUÊS", "seta": True},
        {"tipo": "sublinhado", "x0": 72, "y0": 95, "x1": 300, "y1": 110,
         "texto": "Sublinhado no texto", "classificacao": "ERRO DE PORTUGUÊS"},
        {"tipo": "tachado", "x0": 72, "y0": 95, "x1": 300, "y1": 110,
         "texto": "Tachado no texto", "classificacao": "ERRO DE PORTUGUÊS"},
        {"tipo": "realce", "x0": 72, "y0": 95, "x1": 300, "y1": 110,
         "texto": "Realce no texto", "classificacao": "ERRO DE PORTUGUÊS", "cor": "#FFFF00"},
    ]

    for idx, c in enumerate(marcacoes, start=1):
        tipo = c["tipo"]
        conteudo = f"[Nº {idx}] {c['classificacao']}\n\n{c['texto']}"
        annot = None

        if tipo == "comentario":
            annot = pagina.add_text_annot(fitz.Point(c["x"], c["y"]), conteudo, icon="Comment")
        elif tipo == "texto_livre":
            fontsize = c.get("fontsize", 12)
            rect = rect_texto_livre(c["x"], c["y"], c["texto"], fontsize)
            annot = pagina.add_freetext_annot(
                rect, c["texto"], fontsize=fontsize,
                text_color=hex_para_rgb01(c.get("cor", "#000000")),
            )
        elif tipo == "retangulo":
            annot = pagina.add_rect_annot(rect_de_marcacao(c))
            annot.set_colors(stroke=hex_para_rgb01(c.get("cor", "#FF0000")))
        elif tipo == "elipse":
            annot = pagina.add_circle_annot(rect_de_marcacao(c))
        elif tipo == "linha":
            annot = pagina.add_line_annot(
                fitz.Point(c["x0"], c["y0"]), fitz.Point(c["x1"], c["y1"])
            )
            if c.get("seta"):
                annot.set_line_ends(fitz.PDF_ANNOT_LE_NONE, fitz.PDF_ANNOT_LE_OPEN_ARROW)
        elif tipo == "sublinhado":
            annot = pagina.add_underline_annot(rect_de_marcacao(c).quad)
        elif tipo == "tachado":
            annot = pagina.add_strikeout_annot(rect_de_marcacao(c).quad)
        elif tipo == "realce":
            annot = pagina.add_highlight_annot(rect_de_marcacao(c).quad)
            annot.set_colors(stroke=hex_para_rgb01(c.get("cor", "#FFFF00")))

        assert annot is not None, f"Tipo de marcação não tratado: {tipo}"
        annot.set_info(title="Revisor", subject=c["classificacao"], content=conteudo)
        annot.update()

    doc.save(caminho_saida)
    doc.close()
    return len(marcacoes)


def test_todas_as_marcacoes():
    with tempfile.TemporaryDirectory() as tmp:
        entrada = os.path.join(tmp, "teste_entrada.pdf")
        saida = os.path.join(tmp, "teste_saida.pdf")

        _criar_pdf_teste(entrada)
        total_criadas = _aplicar_marcacoes(entrada, saida)
        assert total_criadas == 8

        doc = fitz.open(saida)
        pagina = doc[0]
        annots = list(pagina.annots())

        contagem_por_tipo = {}
        for annot in annots:
            nome_tipo = annot.type[1]
            contagem_por_tipo[nome_tipo] = contagem_por_tipo.get(nome_tipo, 0) + 1

        esperado = {
            "Text": 1,        # comentario
            "FreeText": 1,    # texto_livre
            "Square": 1,      # retangulo
            "Circle": 1,      # elipse
            "Line": 1,        # linha
            "Underline": 1,   # sublinhado
            "StrikeOut": 1,   # tachado
            "Highlight": 1,   # realce
        }

        assert contagem_por_tipo == esperado, (
            f"Contagem de anotações por tipo não bate.\n"
            f"Esperado: {esperado}\nObtido:   {contagem_por_tipo}"
        )
        assert len(annots) == 8

        # confere que a classificação/texto foram gravados no conteúdo (popup)
        # de pelo menos uma anotação geométrica (realce)
        realce = next(a for a in annots if a.type[1] == "Highlight")
        info = realce.info
        assert "ERRO DE PORTUGUÊS" in info.get("content", "")
        assert "Realce no texto" in info.get("content", "")

        doc.close()


if __name__ == "__main__":
    test_todas_as_marcacoes()
    print("OK: todas as 8 marcações foram gravadas e lidas corretamente.")
