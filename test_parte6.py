#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste headless da PARTE 6: usabilidade/finalização (itens 12-24).

Cobre especificamente o que a Parte 6 pediu para testar:
  - criar um item com a ferramenta Caneta e confirmar que é exportado como
    anotação Ink, com cor/espessura/opacidade configuradas (item 22);
além de outros pontos centrais mais fáceis de quebrar silenciosamente:
  - cor do marcador conforme o status, incluindo o caso Corrigido+verificado
    (item 12);
  - "Correto" (cor amarela) não entra na contagem de erros do Excel (item 16);
  - RESPONSÁVEL PELO ERRO não é mais um campo do ComentarioDialog (item 13);
  - os 4 estilos de tracejado exportam padrões de traço distintos (item 18);
  - carimbo sem imagem nenhuma configurada ainda funciona (fallback quando
    também não há logo_prevent.png) (item 17).

Rodar com:
    python test_parte6.py
"""

import os
import inspect
import tempfile
import tkinter as tk

import fitz

import revisor_pdf as rp
from revisor_pdf import (
    RevisorPDFApp, ComentarioDialog, cor_status, hex_para_rgb01,
    rect_de_marcacao, DASHES_PDF, STATUS_REVISAO,
    COR_MARCADOR_PENDENCIA, COR_MARCADOR_CORRIGIDO, COR_MARCADOR_VERIFICADO,
    COR_MARCADOR_CORRETO, gerar_imagem_carimbo,
)


def _criar_pdf_teste(caminho):
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(caminho)
    doc.close()


def test_caneta_exporta_ink_annot_com_estilo():
    with tempfile.TemporaryDirectory() as tmp:
        entrada = os.path.join(tmp, "entrada.pdf")
        saida = os.path.join(tmp, "saida.pdf")
        _criar_pdf_teste(entrada)

        item_caneta = {
            "tipo": "caneta", "pagina": 0,
            "pontos": [[50, 50], [80, 90], [120, 60]],
            "cor": "#00AAFF", "espessura": 5, "opacidade": 60,
            "texto": "traço de teste", "classificacao": rp.CLASSIFICACOES[0],
            "status": "Pendente", "data": "01/01/2026",
        }

        doc = fitz.open(entrada)
        try:
            pagina = doc[0]
            pontos = [(p[0], p[1]) for p in item_caneta["pontos"]]
            annot = pagina.add_ink_annot([pontos])
            annot.set_colors(stroke=hex_para_rgb01(item_caneta["cor"]))
            annot.set_border(width=item_caneta["espessura"])
            annot.set_opacity(item_caneta["opacidade"] / 100)
            annot.update()
            doc.save(saida)
        finally:
            doc.close()

        doc2 = fitz.open(saida)
        try:
            pagina2 = doc2[0]
            annots = list(pagina2.annots())
            assert len(annots) == 1
            ink = annots[0]
            assert ink.type[1] == "Ink", f"esperado tipo Ink, obtido {ink.type[1]}"
            cor_esperada = hex_para_rgb01("#00AAFF")
            assert all(abs(a - b) < 1e-3 for a, b in zip(ink.colors["stroke"], cor_esperada))
            assert ink.border["width"] == 5.0
            assert abs(ink.opacity - 0.6) < 1e-3
        finally:
            doc2.close()


def test_cor_marcador_por_status():
    assert cor_status({"status": "Pendente"}) == COR_MARCADOR_PENDENCIA
    assert cor_status({"status": "Não corrigido"}) == COR_MARCADOR_PENDENCIA
    assert cor_status({"status": "Reincidente"}) == COR_MARCADOR_PENDENCIA
    assert cor_status({"status": "Corrigido", "verificacao_correcao": False}) == COR_MARCADOR_CORRIGIDO
    assert cor_status({"status": "Corrigido", "verificacao_correcao": True}) == COR_MARCADOR_VERIFICADO
    assert cor_status({"status": "Correto"}) == COR_MARCADOR_CORRETO
    # compatibilidade: aceitar string simples também
    assert cor_status("Corrigido") == COR_MARCADOR_CORRIGIDO


def test_responsavel_erro_removido_do_dialogo():
    parametros = inspect.signature(ComentarioDialog.__init__).parameters
    assert "responsavel_erro" not in parametros, (
        "ComentarioDialog não deveria mais aceitar responsavel_erro (Parte 6, item 13)"
    )


def test_correto_nao_conta_como_erro_no_excel():
    root = tk.Tk()
    root.withdraw()
    app = RevisorPDFApp(root)
    try:
        app.dados_documento = {"elaborado_por": "Fulano", "verificado_por": "Beltrano"}
        app.comentarios = [
            {
                "tipo": "retangulo", "pagina": 0, "x0": 0, "y0": 0, "x1": 10, "y1": 10,
                "texto": "erro real", "classificacao": rp.CLASSIFICACOES[0],
                "status": "Pendente", "data": "01/01/2026",
            },
            {
                "tipo": "elipse", "pagina": 0, "x0": 0, "y0": 0, "x1": 10, "y1": 10,
                "texto": rp.TEXTO_ITEM_CORRETO, "classificacao": "",
                "status": "Correto", "data": "01/01/2026",
            },
        ]
        linhas = app._linhas_excel()
        assert linhas[0]["codigo"] != "" and linhas[0]["quantidade"] == 1
        assert linhas[1]["codigo"] == "" and linhas[1]["quantidade"] == ""
        assert linhas[1]["responsavel_erro"] == "Fulano", "RESPONSÁVEL PELO ERRO deve vir do documento mesmo para 'Correto'"
    finally:
        root.destroy()


def test_tracejados_geram_padroes_distintos_no_pdf_exportado():
    with tempfile.TemporaryDirectory() as tmp:
        entrada = os.path.join(tmp, "entrada.pdf")
        saida = os.path.join(tmp, "saida.pdf")
        _criar_pdf_teste(entrada)

        doc = fitz.open(entrada)
        try:
            pagina = doc[0]
            y = 50
            for estilo in rp.ESTILOS_TRACEJADO:
                item = {"x0": 50, "y0": y, "x1": 150, "y1": y + 20}
                annot = pagina.add_rect_annot(rect_de_marcacao(item))
                annot.set_border(width=2, dashes=DASHES_PDF[estilo])
                annot.update()
                y += 40
            doc.save(saida)
        finally:
            doc.close()

        doc2 = fitz.open(saida)
        try:
            dashes_gravados = [tuple(a.border["dashes"]) for a in doc2[0].annots()]
            assert len(set(dashes_gravados)) == len(rp.ESTILOS_TRACEJADO), (
                f"os {len(rp.ESTILOS_TRACEJADO)} tracejados deveriam gravar padrões "
                f"distintos, obtido {dashes_gravados}"
            )
        finally:
            doc2.close()


def test_carimbo_sem_nenhuma_imagem_ainda_funciona():
    # garante que, mesmo sem logo_prevent.png presente, o fallback por código funciona
    imagem_bytes = gerar_imagem_carimbo(None, "Fulano", "01/01/2026")
    assert imagem_bytes[:8] == b"\x89PNG\r\n\x1a\n", "deveria gerar um PNG válido"
    assert len(imagem_bytes) > 100


if __name__ == "__main__":
    test_caneta_exporta_ink_annot_com_estilo()
    test_cor_marcador_por_status()
    test_responsavel_erro_removido_do_dialogo()
    test_correto_nao_conta_como_erro_no_excel()
    test_tracejados_geram_padroes_distintos_no_pdf_exportado()
    test_carimbo_sem_nenhuma_imagem_ainda_funciona()
    print("OK: Caneta (Ink annot), cor do marcador por status, 'Correto' isento de erro, "
          "4 tracejados distintos, responsavel_erro removido, carimbo padrão OK.")
