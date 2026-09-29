"""
Exporta o resultado de uma Análise de Risco (NBR 5419-2) como memorial de
cálculo em Word (.docx), usando templates/memorial_5419-2.docx como modelo.

O modelo foi escrito para a metodologia antiga (R1/R2/R3/R4, edição
2015/2018). Nosso motor calcula R1, R3 e a frequência de danos F, porque a
edição 2026 substituiu R2 por F. Por instrução do engenheiro responsável,
adaptamos os textos e o segundo gráfico do modelo para usar F em vez de R2,
mantendo a estrutura (título, colunas, dois gráficos) como está.

Limitação assumida (documentada, não escondida): o sistema não modela o
dimensionamento físico do SPDA (captação natural/não natural, malha,
comprimento de anel de aterramento — isso é objeto da NBR 5419-3, fora do
escopo desta v1). A Seção 7 do memorial é gerada de forma genérica a partir
da classe de SPDA considerada no cálculo, sem inventar detalhes de projeto
que o sistema não coletou.
"""
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.shared import Inches

from . import tabelas

TEMPLATE_PATH = Path(__file__).parent / "templates" / "memorial_5419-2.docx"

COR_TOLERAVEL = "#5b8fc4"
COR_CALCULADO = "#c0392b"
COR_CALCULADO_OK = "#2e7d32"


# --------------------------------------------------------------------------
# Helpers genéricos de manipulação do .docx (baixo nível, sem dependência
# de nenhum dado da análise — reutilizáveis em qualquer exportação futura)
# --------------------------------------------------------------------------

def _tag(elemento):
    return elemento.tag.split("}")[-1]


def _substituir_em_paragrafo(paragrafo, de, para):
    if de not in paragrafo.text:
        return False
    texto = paragrafo.text.replace(de, para)
    for run in list(paragrafo.runs)[1:]:
        run.text = ""
    if paragrafo.runs:
        paragrafo.runs[0].text = texto
    else:
        paragrafo.add_run(texto)
    return True


def _substituir_em_todo_documento(doc, mapa):
    """Substitui placeholders [X] -> valor em parágrafos, tabelas, cabeçalhos e rodapés."""
    alvos = list(doc.paragraphs)
    for t in doc.tables:
        for r in t.rows:
            for c in r.cells:
                alvos.extend(c.paragraphs)
    for sec in doc.sections:
        alvos.extend(sec.header.paragraphs)
        alvos.extend(sec.footer.paragraphs)
        for t in list(sec.header.tables) + list(sec.footer.tables):
            for r in t.rows:
                for c in r.cells:
                    alvos.extend(c.paragraphs)
    for paragrafo in alvos:
        for de, para in mapa.items():
            _substituir_em_paragrafo(paragrafo, de, str(para))


def _remover_elemento(elemento):
    elemento.getparent().remove(elemento)


def _remover_intervalo(inicio_elem, fim_elem_exclusivo):
    """Remove todos os elementos do corpo entre inicio (inclusive) e fim (exclusivo)."""
    atual = inicio_elem
    while atual is not None and atual is not fim_elem_exclusivo:
        proximo = atual.getnext()
        _remover_elemento(atual)
        atual = proximo


def _paragrafo_apos(ancora_elem, doc, texto="", style=None):
    novo = OxmlElement("w:p")
    ancora_elem.addnext(novo)
    p = Paragraph(novo, doc)
    if style:
        p.style = style
    if texto:
        p.add_run(texto)
    return p


def _tabela_apos(ancora_elem, doc, linhas, colunas, style=None):
    tabela_tmp = doc.add_table(rows=linhas, cols=colunas)
    if style:
        tabela_tmp.style = style
    tbl_elem = tabela_tmp._tbl
    tbl_elem.getparent().remove(tbl_elem)
    ancora_elem.addnext(tbl_elem)
    return Table(tbl_elem, doc)


def _encontrar_paragrafo(doc, contendo, estilo=None):
    for p in doc.paragraphs:
        if contendo in p.text and (estilo is None or p.style.name == estilo):
            return p
    raise ValueError(f'Parágrafo contendo "{contendo}" não encontrado no modelo.')


def _grafico_barras(titulo, valor_toleravel, valor_calculado, atende):
    fig, ax = plt.subplots(figsize=(5, 2.6), dpi=150)
    cor_calc = COR_CALCULADO_OK if atende else COR_CALCULADO
    barras = ax.bar(
        ["Risco Tolerável\nsugerido pela NBR", "Risco\nCalculado"],
        [valor_toleravel, valor_calculado],
        color=[COR_TOLERAVEL, cor_calc], width=0.5,
    )
    ax.set_title(titulo, fontsize=11)
    ax.set_yscale("log")
    ax.spines[["top", "right"]].set_visible(False)
    for barra, valor in zip(barras, [valor_toleravel, valor_calculado]):
        ax.annotate(f"{valor:.2e}", (barra.get_x() + barra.get_width() / 2, valor),
                    textcoords="offset points", xytext=(0, 4), ha="center", fontsize=9)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def _forcar_atualizacao_campos(doc):
    """Marca o documento para que o Word recalcule TOC e numeração ao abrir
    (não dá para paginar programaticamente sem o layout engine do Word)."""
    settings = doc.settings.element
    upd = settings.find(qn("w:updateFields"))
    if upd is None:
        upd = OxmlElement("w:updateFields")
        settings.append(upd)
    upd.set(qn("w:val"), "true")


# --------------------------------------------------------------------------
# Construção do conteúdo a partir dos dados da análise
# --------------------------------------------------------------------------

def validar_pendencias(analise, estrutura, zonas, medidas, resultado):
    """Retorna a lista de pendências que impedem a exportação (nunca deixamos
    um placeholder sem preencher no documento final)."""
    pendencias = []
    if not estrutura:
        pendencias.append("Cadastre a estrutura antes de exportar.")
    elif not estrutura.localizacao:
        pendencias.append('Informe a "Localização" da estrutura (aba Estrutura) antes de exportar.')
    if not zonas:
        pendencias.append("Cadastre ao menos uma zona de estudo antes de exportar.")
    if not medidas:
        pendencias.append("Cadastre as medidas de proteção antes de exportar.")
    if not resultado or resultado.memoria_calculo_json is None:
        pendencias.append('Calcule a análise (aba Resultado → "Calcular") antes de exportar.')
    return pendencias


def _bullets_premissas(analise, estrutura, zonas, medidas):
    zona_desc = ", ".join(sorted({
        tabelas.info_grupo("anexo_c_tabela_c2_perdas_r1", "LF", z.categoria_dano_fisico_lf)["descricao"]
        for z in zonas
    }))
    explosao_txt = "com risco de explosão" if estrutura.risco_explosao else "sem risco de explosão"
    incendio_descs = ", ".join(sorted({
        tabelas.info("anexo_c_tabela_c5_rf", z.risco_incendio)["descricao"] for z in zonas
    }))
    providencia_descs = ", ".join(sorted({
        tabelas.info("anexo_c_tabela_c4_rp", z.providencias_incendio)["descricao"] for z in zonas
    }))
    spda_desc = tabelas.info("anexo_b_tabela_b2_pb", medidas.classe_spda)["descricao"]
    dps_desc = tabelas.info("anexo_b_tabela_b3_pspd", medidas.dps_coordenado)["descricao"]
    dps_classe_i_desc = tabelas.info("anexo_b_tabela_b7_peb", medidas.dps_classe_i)["descricao"]

    return [
        "Dados de entrada informados diretamente no sistema de cálculo de risco do projeto "
        "(dimensões da estrutura, linhas elétricas conectadas e medidas de proteção adotadas).",
        f"Densidade de descargas atmosféricas NG = {analise.ng_valor:g} raios/km²·ano "
        f"({analise.ng_referencia}).",
        f"Estrutura {explosao_txt}, com as seguintes zonas de estudo quanto ao tipo de "
        f"ocupação/dano físico considerado: {zona_desc}.",
        f"Risco de incêndio considerado: {incendio_descs}. Providências contra incêndio: {providencia_descs}.",
        f"Medidas de proteção consideradas no cálculo: {spda_desc}; sistema coordenado de DPS: "
        f"{dps_desc}; DPS classe I / ligação equipotencial: {dps_classe_i_desc}.",
    ]


def _texto_conclusao_zona(r1, rt1, r3, rt3, f_total, ft):
    riscos = [("R1", r1, rt1, r1 <= rt1)]
    if r3 is not None:
        riscos.append(("R3", r3, rt3, r3 <= rt3))
    riscos.append(("F", f_total, ft, f_total <= ft))

    if all(ok for _, _, _, ok in riscos):
        partes = " e ".join(f"{nome} ≤ {'FT' if nome == 'F' else 'RT'}" for nome, *_ in riscos)
        return f"Portanto {partes}, não há necessidade de medidas adicionais de proteção contra descargas atmosféricas para esta zona."

    excedentes = [nome for nome, valor, limite, ok in riscos if not ok]
    return (
        f"Os seguintes riscos/frequências excederam o valor tolerável nesta zona: {', '.join(excedentes)}. "
        "São necessárias medidas de proteção adicionais para reduzir o(s) risco(s) a um nível tolerável, "
        "conforme o procedimento de decisão da NBR 5419-2 (Figura 1)."
    )


def _linhas_memoria_para_tabela(memoria_passos):
    """Achata os passos da memória de cálculo (memoria.py) em linhas (rótulo, valor, referência)."""
    linhas = []
    for passo in memoria_passos:
        linhas.append((passo["titulo"], passo.get("resultado"), passo.get("referencia") or ""))
    return linhas


# --------------------------------------------------------------------------
# Orquestração principal
# --------------------------------------------------------------------------

def gerar_memorial(projeto, analise, estrutura, zonas, linhas, medidas, resultado) -> bytes:
    pendencias = validar_pendencias(analise, estrutura, zonas, medidas, resultado)
    if pendencias:
        raise ValueError("Exportação bloqueada — pendências: " + "; ".join(pendencias))

    doc = Document(str(TEMPLATE_PATH))
    memoria = json.loads(resultado.memoria_calculo_json)["passos"]

    # ---- Cabeçalho ----
    numero_doc_contratada = f"{projeto.numero_projeto} / {projeto.revisao or 'Rev. 0'}"
    _substituir_em_todo_documento(doc, {
        "[LOGO DO CLIENTE]": "",
        "[NOME DO PROJETO / CLIENTE]": f"{projeto.nome_projeto} — {projeto.cliente or ''}".strip(" —"),
        "[Nº DO DOCUMENTO DO CLIENTE]": "",
        "[Nº DO DOCUMENTO DA CONTRATADA]": numero_doc_contratada,
    })

    # ---- Seção 1 (OBJETIVO) ----
    _substituir_em_todo_documento(doc, {
        "[NOME DA ESTRUTURA]": analise.tag,
        "[NOME DO CLIENTE]": projeto.cliente or projeto.nome_projeto,
        "[LOCALIZAÇÃO DA ESTRUTURA]": estrutura.localizacao,
    })
    # O parágrafo de objetivo do modelo cita "R2" (metodologia antiga) como o que este
    # relatório mede — troca pelo que o sistema realmente calcula (R1, R3 quando houver, e F).
    p_objetivo = _encontrar_paragrafo(doc, "Registrar a avaliação e o cálculo dos riscos")
    texto_objetivo = p_objetivo.text.replace(
        "de perda de vida humana (R1) e de perda de serviço ao público (R2)",
        "de perda de vida humana (R1)"
        + (", de perda de patrimônio cultural (R3)" if resultado.r3 is not None else "")
        + " e a frequência de danos (F)",
    )
    _substituir_em_paragrafo(p_objetivo, p_objetivo.text, texto_objetivo)

    # ---- Seção 2 (referências adicionais) — sem cadastro de docs extras no sistema: remove o marcador ----
    p_ref_extra = _encontrar_paragrafo(doc, "[Incluir aqui normas")
    _remover_elemento(p_ref_extra._p)

    # ---- Seção 3 (PREMISSAS) ----
    bullets = _bullets_premissas(analise, estrutura, zonas, medidas)
    marcadores = [p for p in doc.paragraphs if p.text.strip().startswith("[Descrever") or p.text.strip().startswith("[Indicar")]
    for p, texto in zip(marcadores, bullets):
        for run in list(p.runs)[1:]:
            run.text = ""
        if p.runs:
            p.runs[0].text = texto
        else:
            p.add_run(texto)

    # ---- Seção 5 (RISCOS CALCULADOS por zona) ----
    _gerar_secao_5(doc, zonas, resultado)

    # ---- Seção 6 (MEMORIAL DE CÁLCULO DOS VALORES) ----
    _gerar_secao_6(doc, memoria)

    # ---- Seção 7 (SISTEMA DE PROTEÇÃO) — genérico a partir da classe de SPDA considerada ----
    _gerar_secao_7(doc, medidas)

    # ---- Seção 8 (CONCLUSÃO) ----
    _gerar_secao_8(doc, resultado)

    _forcar_atualizacao_campos(doc)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _gerar_secao_5(doc, zonas, resultado):
    inicio = _encontrar_paragrafo(doc, "[NOME DA ESTRUTURA / ZONA]")
    fim = _encontrar_paragrafo(doc, "MEMORIAL DE CÁLCULO DOS VALORES DE RISCO OBTIDOS", estilo="Título I_VALE_")
    estilo_tabela = doc.tables[2].style  # "Tabela 02" do modelo

    ancora = inicio._p.getprevious()
    _remover_intervalo(inicio._p, fim._p)

    for zona in zonas:
        p = _paragrafo_apos(ancora, doc, zona.nome, style="Heading 2"); ancora = p._p
        p = _paragrafo_apos(ancora, doc, "SITUAÇÃO DE CÁLCULO", style="Heading 3"); ancora = p._p
        p = _paragrafo_apos(ancora, doc,
            "Foram calculados os valores de risco de perda de vida humana (R1)"
            + (", de perda de patrimônio cultural (R3)" if resultado.r3 is not None else "")
            + " e a frequência de danos (F) para esta zona.", style="Normal")
        ancora = p._p
        p = _paragrafo_apos(ancora, doc, "VALORES CALCULADOS", style="Heading 3"); ancora = p._p

        colunas = ["Situação", "Risco de Vida Humana (R1)"]
        if resultado.r3 is not None:
            colunas.append("Patrimônio Cultural (R3)")
        colunas.append("Frequência de Danos (F)")
        t = _tabela_apos(ancora, doc, linhas=2, colunas=len(colunas), style=estilo_tabela)
        ancora = t._tbl
        for j, texto in enumerate(colunas):
            t.cell(0, j).text = texto
        linha_rt = ["Limite (RT/FT)", f"RT1 = {resultado.rt1:.2e}"]
        linha_calc = ["Calculado", f"R1 = {resultado.r1:.2e}"]
        if resultado.r3 is not None:
            linha_rt.append(f"RT3 = {resultado.rt3:.2e}")
            linha_calc.append(f"R3 = {resultado.r3:.2e}")
        linha_rt.append(f"FT = {resultado.ft:.2e}")
        linha_calc.append(f"F = {resultado.f_total:.2e}")
        for j, texto in enumerate(linha_rt):
            t.cell(1, j).text = texto
        # A tabela nasceu com 2 linhas (cabeçalho + 1); adicionamos a linha "Calculado":
        linha_extra = t.add_row()
        for j, texto in enumerate(linha_calc):
            linha_extra.cells[j].text = texto

        for titulo, valor_tol, valor_calc, atende in [
            (f"Comparação de Risco R1 — {zona.nome}", resultado.rt1, resultado.r1, resultado.r1_atende),
        ] + ([(f"Comparação de Risco R3 — {zona.nome}", resultado.rt3, resultado.r3, resultado.r3_atende)] if resultado.r3 is not None else []) + [
            (f"Comparação de Frequência de Danos F — {zona.nome}", resultado.ft, resultado.f_total, resultado.f_atende),
        ]:
            img = _grafico_barras(titulo, valor_tol, valor_calc, atende)
            p = _paragrafo_apos(ancora, doc); ancora = p._p
            p.add_run().add_picture(img, width=Inches(4.5))

        texto_conclusao = _texto_conclusao_zona(resultado.r1, resultado.rt1, resultado.r3, resultado.rt3, resultado.f_total, resultado.ft)
        p = _paragrafo_apos(ancora, doc, texto_conclusao, style="Normal"); ancora = p._p


def _gerar_secao_6(doc, memoria_passos):
    inicio = _encontrar_paragrafo(doc, "ZONA Z1", estilo="Heading 2")
    fim = _encontrar_paragrafo(doc, "Sistema de Proteção", estilo="Título I_VALE_")
    estilo_tabela = doc.tables[3].style  # "Tabela 40" do modelo

    ancora = inicio._p.getprevious()
    _remover_intervalo(inicio._p, fim._p)

    p = _paragrafo_apos(ancora, doc, "Memória de Cálculo Consolidada", style="Heading 2"); ancora = p._p
    p = _paragrafo_apos(ancora, doc, "Tabela 40 - Etapas de Cálculo, Fórmulas e Valores Assumidos", style="Normal"); ancora = p._p

    linhas = _linhas_memoria_para_tabela(memoria_passos)
    t = _tabela_apos(ancora, doc, linhas=1, colunas=3, style=estilo_tabela)
    ancora = t._tbl
    for j, texto in enumerate(["Etapa / Grandeza", "Fórmula e valores substituídos", "Resultado"]):
        t.cell(0, j).text = texto
    for titulo, resultado_num, _ref in linhas:
        linha = t.add_row()
        linha.cells[0].text = titulo
        linha.cells[2].text = f"{resultado_num:.6g}" if isinstance(resultado_num, (int, float)) else (str(resultado_num) if resultado_num is not None else "-")

    # A coluna "fórmula/linhas" fica no passo original (memoria_passos[i]["linhas"]);
    # gravamos como texto multi-linha na própria célula 1 de cada linha adicionada.
    linhas_tabela = t.rows[1:]
    for row, passo in zip(linhas_tabela, memoria_passos):
        celula = row.cells[1]
        celula.text = ""
        for i, linha_texto in enumerate(passo["linhas"]):
            paragrafo = celula.paragraphs[0] if i == 0 else celula.add_paragraph()
            paragrafo.add_run(linha_texto)


def _gerar_secao_7(doc, medidas):
    spda_info = tabelas.info("anexo_b_tabela_b2_pb", medidas.classe_spda)
    dps_info = tabelas.info("anexo_b_tabela_b3_pspd", medidas.dps_coordenado)

    p_captacao = _encontrar_paragrafo(doc, "O método escolhido para o subsistema de captação")
    _substituir_em_paragrafo(
        p_captacao, p_captacao.text,
        f"A análise de risco considerou: {spda_info['descricao']}. O detalhamento físico do "
        "subsistema de captação (natural ou não natural, disposição dos captores) é objeto de "
        "projeto específico conforme a ABNT NBR 5419-3, não coberto por esta análise de risco.",
    )
    p_descida = _encontrar_paragrafo(doc, "O método escolhido para o subsistema de descida")
    _substituir_em_paragrafo(
        p_descida, p_descida.text,
        "O detalhamento físico do subsistema de descida (natural ou não natural, espaçamento entre "
        "descidas) é objeto de projeto específico conforme a ABNT NBR 5419-3, não coberto por esta "
        "análise de risco.",
    )
    p_aterramento = _encontrar_paragrafo(doc, "O comprimento mínimo do anel de aterramento")
    _substituir_em_paragrafo(
        p_aterramento, p_aterramento.text,
        f"Sistema coordenado de DPS considerado no cálculo: {dps_info['descricao']}. O detalhamento "
        "físico do subsistema de aterramento é objeto de projeto específico conforme a ABNT NBR 5419-3, "
        "não coberto por esta análise de risco.",
    )


def _gerar_secao_8(doc, resultado):
    p_conclusao = _encontrar_paragrafo(doc, "Conforme demostrado nos cálculos")
    atende_tudo = resultado.r1_atende and (resultado.r3_atende is None or resultado.r3_atende) and resultado.f_atende
    if atende_tudo:
        texto = (
            "Conforme demonstrado nos cálculos apresentados, os riscos calculados (R1"
            + (", R3" if resultado.r3 is not None else "")
            + ") e a frequência de danos (F) estão dentro dos limites toleráveis estabelecidos pela "
            "ABNT NBR 5419-2, não havendo necessidade de medidas de proteção adicionais além das já "
            "consideradas no cálculo."
        )
    else:
        pendentes = []
        if not resultado.r1_atende:
            pendentes.append("R1")
        if resultado.r3_atende is False:
            pendentes.append("R3")
        if not resultado.f_atende:
            pendentes.append("F")
        texto = (
            f"Conforme demonstrado nos cálculos apresentados, o(s) valor(es) de {', '.join(pendentes)} "
            "excede(m) o limite tolerável estabelecido pela ABNT NBR 5419-2. São necessárias medidas de "
            "proteção adicionais (SPDA, DPS coordenado, blindagens ou equipotencialização, conforme "
            "aplicável) para reduzir o(s) risco(s) a um nível tolerável, devendo a análise ser refeita "
            "após a definição dessas medidas."
        )
    _substituir_em_paragrafo(p_conclusao, p_conclusao.text, texto)
