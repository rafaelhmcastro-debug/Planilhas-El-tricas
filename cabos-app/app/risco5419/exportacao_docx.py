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
# Item 8.1 — Dados de Entrada (Sigla | Significado | Denominação | Valor assumido)
#
# Cada linha reflete uma opção normativa (dados/*.json) ou um valor numérico
# informado pelo engenheiro REALMENTE usado nesta análise — nunca a lista
# completa de opções disponíveis de cada sigla, e nunca uma sigla que a
# análise não usa (ex.: R4/Anexo D, não implementado; estrutura adjacente,
# não modelada — 6.4.1 permite desprezar NDJ). Os pares (tabela, chave) abaixo
# espelham exatamente as chamadas que riscos.py faz para calcular R1/R3/F;
# nada aqui influencia o cálculo, que já rodou antes deste módulo ser chamado.
# --------------------------------------------------------------------------

# Significados por grupo (LT/LF/LO) — dados/*.json guarda só um "descricao" por
# tabela inteira, não por grupo; o texto abaixo vem da planilha de referência
# (coluna "Significado"), que distingue os três.
_SIGNIFICADO_GRUPO = {
    ("anexo_c_tabela_c2_perdas_r1", "LT"): "Número relativo médio típico de vítimas feridas por choque elétrico (D1)",
    ("anexo_c_tabela_c2_perdas_r1", "LF"): "Número relativo médio típico de vítimas por dano físico (D2)",
    ("anexo_c_tabela_c2_perdas_r1", "LO"): "Número relativo médio típico de vítimas por falha de sistemas internos (D3)",
}


def _linha(sigla, significado, info, contexto=None, valor_extra=None, denominacao_extra=None):
    valor = valor_extra if valor_extra is not None else info["valor"]
    denom = denominacao_extra if denominacao_extra is not None else info["descricao"]
    return {
        "sigla": sigla, "significado": significado, "denominacao": denom,
        "valor": valor, "referencia": info.get("referencia") or "", "contexto": contexto or "",
    }


def _linha_entrada_livre(sigla, significado, valor, referencia, contexto=None):
    return {
        "sigla": sigla, "significado": significado, "denominacao": "Valor informado pelo engenheiro para o projeto",
        "valor": valor, "referencia": referencia, "contexto": contexto or "",
    }


def _dados_entrada_usados(analise, estrutura, zonas, linhas_eletricas, medidas, resultado):
    """Monta as linhas do item 8.1 a partir dos mesmos campos (chave selecionada
    ou número informado) que riscos.py já usa para calcular — nunca a lista
    completa de opções de cada sigla."""
    linhas = []

    linhas.append(_linha_entrada_livre("NG", "Densidade de descargas atmosféricas para a terra",
                                        f"{analise.ng_valor:g} raios/km²·ano", analise.ng_referencia))

    cd_cab = tabelas.cabecalho("anexo_a_tabela_a1_cd")
    linhas.append(_linha("CD", cd_cab["descricao"], tabelas.info("anexo_a_tabela_a1_cd", estrutura.fator_localizacao)))
    rs_cab = tabelas.cabecalho("anexo_c_tabela_c7_rs")
    linhas.append(_linha("rs", rs_cab["descricao"], tabelas.info("anexo_c_tabela_c7_rs", estrutura.tipo_construcao)))
    linhas.append(_linha_entrada_livre("nt", "Número total de pessoas na estrutura", estrutura.num_pessoas_total, ""))

    # ---- Medidas de proteção (nível da análise) ----
    pb_cab = tabelas.cabecalho("anexo_b_tabela_b2_pb")
    linhas.append(_linha("PB", pb_cab["descricao"], tabelas.info("anexo_b_tabela_b2_pb", medidas.classe_spda)))

    pta_cab = tabelas.cabecalho("anexo_b_tabela_b1_pta")
    for chave in json.loads(medidas.medidas_pta_json or "[]"):
        linhas.append(_linha("PTA", pta_cab["descricao"], tabelas.info("anexo_b_tabela_b1_pta", chave)))

    pspd_cab = tabelas.cabecalho("anexo_b_tabela_b3_pspd")
    linhas.append(_linha("PSPD", pspd_cab["descricao"], tabelas.info("anexo_b_tabela_b3_pspd", medidas.dps_coordenado)))
    peb_cab = tabelas.cabecalho("anexo_b_tabela_b7_peb")
    linhas.append(_linha("PEB", peb_cab["descricao"], tabelas.info("anexo_b_tabela_b7_peb", medidas.dps_classe_i)))
    ptu_cab = tabelas.cabecalho("anexo_b_tabela_b6_ptu")
    linhas.append(_linha("PTU", ptu_cab["descricao"], tabelas.info("anexo_b_tabela_b6_ptu", medidas.medida_ptu)))
    ks3_cab = tabelas.cabecalho("anexo_b_tabela_b5_ks3")
    linhas.append(_linha("KS3", ks3_cab["descricao"], tabelas.info("anexo_b_tabela_b5_ks3", medidas.fiacao_interna)))

    if medidas.largura_malha_externa_m is not None:
        linhas.append(_linha_entrada_livre("wm1", "Largura da malha para KS1", f"{medidas.largura_malha_externa_m:g} m", ""))
    if medidas.largura_malha_interna_m is not None:
        linhas.append(_linha_entrada_livre("wm2", "Largura da malha para KS2", f"{medidas.largura_malha_interna_m:g} m", ""))
    linhas.append(_linha_entrada_livre("UW", "Tensão suportável nominal de impulso do sistema interno",
                                        f"{medidas.tensao_suportavel_sistema_interno_kv:g} kV", ""))

    # ---- Zonas de estudo ----
    lt_info = tabelas.info_grupo("anexo_c_tabela_c2_perdas_r1", "LT", "todos_os_tipos")
    linhas.append(_linha("LT", _SIGNIFICADO_GRUPO[("anexo_c_tabela_c2_perdas_r1", "LT")], lt_info))

    rt_cab = tabelas.cabecalho("anexo_c_tabela_c3_rt_piso")
    rp_cab = tabelas.cabecalho("anexo_c_tabela_c4_rp")
    rf_cab = tabelas.cabecalho("anexo_c_tabela_c5_rf")
    hz_cab = tabelas.cabecalho("anexo_c_tabela_c6_hz")
    for zona in zonas:
        ctx = f'Zona "{zona.nome}"'
        linhas.append(_linha("rt", rt_cab["descricao"], tabelas.info("anexo_c_tabela_c3_rt_piso", zona.tipo_piso), ctx))
        linhas.append(_linha("rp", rp_cab["descricao"], tabelas.info("anexo_c_tabela_c4_rp", zona.providencias_incendio), ctx))
        linhas.append(_linha("rf", rf_cab["descricao"], tabelas.info("anexo_c_tabela_c5_rf", zona.risco_incendio), ctx))
        linhas.append(_linha("hz", hz_cab["descricao"], tabelas.info("anexo_c_tabela_c6_hz", zona.perigo_especial), ctx))
        linhas.append(_linha("LF", _SIGNIFICADO_GRUPO[("anexo_c_tabela_c2_perdas_r1", "LF")],
                              tabelas.info_grupo("anexo_c_tabela_c2_perdas_r1", "LF", zona.categoria_dano_fisico_lf), ctx))
        linhas.append(_linha("LO", _SIGNIFICADO_GRUPO[("anexo_c_tabela_c2_perdas_r1", "LO")],
                              tabelas.info_grupo("anexo_c_tabela_c2_perdas_r1", "LO", zona.categoria_falha_sistema_lo), ctx))
        linhas.append(_linha_entrada_livre("nz", "Número de pessoas na zona de estudo", zona.num_pessoas_zona, "", ctx))
        linhas.append(_linha_entrada_livre("tz", "Tempo de presença de pessoas na zona de estudo",
                                            f"{zona.tempo_pessoas_horas_ano:g} h/ano", "", ctx))
        if resultado.r3 is not None and zona.valor_patrimonio_cultural:
            linhas.append(_linha_entrada_livre("cz", "Valor do patrimônio cultural na zona",
                                                f"{zona.valor_patrimonio_cultural:g}", "", ctx))

    # ---- R3 (só se a análise computou perda de patrimônio cultural) ----
    if resultado.r3 is not None:
        ct_total = sum(z.valor_patrimonio_cultural for z in zonas if z.valor_patrimonio_cultural)
        linhas.append(_linha_entrada_livre("ct", "Valor total da edificação e conteúdo da estrutura (soma das zonas)",
                                            f"{ct_total:g}", ""))
        lf_r3_info = tabelas.info("anexo_c_tabela_c9_perdas_r3", "museus_galerias")
        lf_r3_cab = tabelas.cabecalho("anexo_c_tabela_c9_perdas_r3")
        linhas.append(_linha("LF", lf_r3_cab["descricao"], lf_r3_info))

    # ---- Linhas elétricas e trechos ----
    ci_cab = tabelas.cabecalho("anexo_a_tabela_a2_ci")
    ce_cab = tabelas.cabecalho("anexo_a_tabela_a4_ce")
    ct_cab = tabelas.cabecalho("anexo_a_tabela_a3_ct")
    cld_cli_cab = tabelas.cabecalho("anexo_b_tabela_b4_cld_cli")
    pld_cab = tabelas.cabecalho("anexo_b_tabela_b8_pld")
    pli_cab = tabelas.cabecalho("anexo_b_tabela_b9_pli")
    for linha_eletrica in linhas_eletricas:
        ctx_linha = f'Linha "{linha_eletrica.tag}"'
        ct_chave = "at_com_transformador_at_bt" if linha_eletrica.tem_transformador_at_bt else "bt_ou_sinal"
        linhas.append(_linha("CT", ct_cab["descricao"], tabelas.info("anexo_a_tabela_a3_ct", ct_chave), ctx_linha))
        linhas.append(_linha_entrada_livre("UW", "Tensão suportável nominal de impulso do equipamento conectado",
                                            f"{linha_eletrica.tensao_suportavel_kv:g} kV", "", ctx_linha))
        pli_chave = "linhas_energia" if linha_eletrica.tipo == "energia" else "linhas_sinal"
        pli_valor = tabelas.valor_por_uw("anexo_b_tabela_b9_pli", pli_chave, linha_eletrica.tensao_suportavel_kv)
        pli_info = tabelas.info("anexo_b_tabela_b9_pli", pli_chave)
        linhas.append(_linha("PLI", pli_cab["descricao"], pli_info, ctx_linha, valor_extra=pli_valor,
                              denominacao_extra=f"{pli_info['descricao']} (UW = {linha_eletrica.tensao_suportavel_kv:g} kV)"))

        for trecho in linha_eletrica.trechos:
            ctx = f'{ctx_linha} — trecho {trecho.ordem + 1}' if len(linha_eletrica.trechos) > 1 else ctx_linha
            linhas.append(_linha("CI", ci_cab["descricao"], tabelas.info("anexo_a_tabela_a2_ci", trecho.tipo_instalacao), ctx))
            linhas.append(_linha("CE", ce_cab["descricao"], tabelas.info("anexo_a_tabela_a4_ce", trecho.ambiente), ctx))
            linhas.append(_linha_entrada_livre("LL", "Comprimento do trecho da linha elétrica",
                                                f"{trecho.comprimento_m:g} m", "", ctx))

            cld_cli_info = tabelas.info("anexo_b_tabela_b4_cld_cli", trecho.categoria_blindagem)
            linhas.append(_linha("CLD", cld_cli_cab["descricao"], cld_cli_info, ctx, valor_extra=cld_cli_info["cld"]))
            linhas.append(_linha("CLI", cld_cli_cab["descricao"], cld_cli_info, ctx, valor_extra=cld_cli_info["cli"]))

            pld_valor = tabelas.valor_por_uw("anexo_b_tabela_b8_pld", trecho.categoria_pld, linha_eletrica.tensao_suportavel_kv)
            pld_info = tabelas.info("anexo_b_tabela_b8_pld", trecho.categoria_pld)
            linhas.append(_linha("PLD", pld_cab["descricao"], pld_info, ctx, valor_extra=pld_valor,
                                  denominacao_extra=f"{pld_info['descricao']} (UW = {linha_eletrica.tensao_suportavel_kv:g} kV)"))

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
    _gerar_secao_6(doc, analise, estrutura, zonas, linhas, medidas, resultado, memoria)

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


def _gerar_secao_6(doc, analise, estrutura, zonas, linhas_eletricas, medidas, resultado, memoria_passos):
    inicio = _encontrar_paragrafo(doc, "ZONA Z1", estilo="Heading 2")
    fim = _encontrar_paragrafo(doc, "Sistema de Proteção", estilo="Título I_VALE_")
    estilo_tabela = doc.tables[3].style  # "Tabela 40" do modelo

    ancora = inicio._p.getprevious()
    _remover_intervalo(inicio._p, fim._p)

    # ---- 8.1 Dados de Entrada: sigla/significado/denominação/valor efetivamente usados ----
    p = _paragrafo_apos(ancora, doc, "Dados de Entrada", style="Heading 2"); ancora = p._p
    p = _paragrafo_apos(
        ancora, doc,
        "Apresenta-se a seguir cada sigla normativa (ABNT NBR 5419-2, Anexos A, B e C) e cada valor "
        "informado pelo engenheiro efetivamente utilizados no cálculo desta análise — somente a opção "
        "selecionada para cada sigla, não as demais opções disponíveis na norma.",
        style="Normal",
    )
    ancora = p._p

    dados_entrada = _dados_entrada_usados(analise, estrutura, zonas, linhas_eletricas, medidas, resultado)
    t_entrada = _tabela_apos(ancora, doc, linhas=1, colunas=5, style=estilo_tabela)
    ancora = t_entrada._tbl
    for j, texto in enumerate(["Sigla", "Significado", "Denominação", "Valor assumido", "Contexto"]):
        t_entrada.cell(0, j).text = texto
    for linha_dados in dados_entrada:
        linha = t_entrada.add_row()
        linha.cells[0].text = linha_dados["sigla"]
        linha.cells[1].text = linha_dados["significado"] or ""
        linha.cells[2].text = linha_dados["denominacao"] or ""
        valor = linha_dados["valor"]
        linha.cells[3].text = f"{valor:g}" if isinstance(valor, (int, float)) else str(valor)
        linha.cells[4].text = linha_dados["contexto"] or ""

    # ---- 8.2 Memória de Cálculo Consolidada (inalterada: etapas, fórmulas e resultados) ----
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
