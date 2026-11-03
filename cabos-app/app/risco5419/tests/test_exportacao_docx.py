"""
Testes do item 8.1 (Dados de Entrada) do memorial de cálculo exportado em
.docx. Sem pytest — roda com `python -m unittest` (stdlib), como o resto do
projeto. Usa SimpleNamespace nos mesmos moldes de test_motor.py: não depende
de banco de dados.
"""
import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.risco5419 import tabelas, riscos, exportacao_docx as exp  # noqa: E402
import unittest  # noqa: E402


def _estrutura(**over):
    base = dict(
        comprimento_m=20, largura_m=10, altura_m=6, fator_localizacao="isolada",
        tipo_construcao="robusta_metalica_concreto_armado", risco_explosao=False,
        falha_sistema_interno_risco_vida=False, num_pessoas_total=50,
        localizacao="Rua Teste, 123 — Cidade/UF",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _zona(**over):
    base = dict(
        nome="Zona única", num_pessoas_zona=50, tempo_pessoas_horas_ano=8760,
        tipo_piso="terra_concreto", providencias_incendio="nenhuma_ou_risco_explosao",
        risco_incendio="incendio_normal", perigo_especial="sem_perigo_especial",
        categoria_dano_fisico_lf="outros", categoria_falha_sistema_lo="outras_partes_hospital",
        valor_patrimonio_cultural=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _linha(**over):
    trecho = SimpleNamespace(
        ordem=0, comprimento_m=500, tipo_instalacao="aereo", ambiente="rural",
        categoria_blindagem="aerea_nao_blindada_sem_ligacao",
        categoria_pld="nao_blindada_ou_blindagem_nao_interligada",
    )
    base = dict(tag="L1", tipo="energia", tem_transformador_at_bt=False,
                tensao_suportavel_kv=1.5, trechos=[trecho])
    base.update(over)
    return SimpleNamespace(**base)


def _medidas(**over):
    base = dict(
        classe_spda="spda_np_ii", medidas_pta_json='["avisos_de_alerta"]',
        dps_coordenado="nenhum_sistema_coordenado_dps", dps_classe_i="sem_dps_classe_i",
        medida_ptu="nenhuma_medida", fiacao_interna="blindado_ou_em_conduto_metalico",
        largura_malha_externa_m=None, largura_malha_interna_m=None,
        tensao_suportavel_sistema_interno_kv=1.5,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _analise(**over):
    base = dict(tag="AR-01", ng_valor=10.0, ng_referencia="Anexo F, município de teste")
    base.update(over)
    return SimpleNamespace(**base)


def _resultado_de(resultado_dict, mem):
    return SimpleNamespace(
        r1=resultado_dict["r1"], rt1=resultado_dict["rt1"], r1_atende=resultado_dict["r1_atende"],
        r3=resultado_dict["r3"], rt3=resultado_dict["rt3"], r3_atende=resultado_dict["r3_atende"],
        f_total=resultado_dict["f_total"], ft=resultado_dict["ft"], f_atende=resultado_dict["f_atende"],
        memoria_calculo_json=mem.to_json(),
    )


RT1 = tabelas.valor("tabela_04_risco_toleravel", "rt_r1")
RT3 = tabelas.valor("tabela_04_risco_toleravel", "rt_r3")
FT = tabelas.valor("tabela_07_frequencia_toleravel", "sistema_nao_critico")


class TestDadosEntradaUsados(unittest.TestCase):
    """Item 8.1: só a opção selecionada de cada sigla efetivamente usada."""

    def setUp(self):
        self.estrutura = _estrutura()
        self.zona = _zona()
        self.linha = _linha()
        self.medidas = _medidas()
        self.analise = _analise()
        resultado_dict, self.mem = riscos.calcular(
            self.estrutura, [self.zona], [self.linha], self.medidas,
            ng=10, rt1=RT1, rt3=RT3, ft_valor=FT,
        )
        self.resultado = _resultado_de(resultado_dict, self.mem)

    def _linhas(self, estrutura=None, zonas=None, linhas=None, medidas=None, resultado=None):
        return exp._dados_entrada_usados(
            self.analise, estrutura or self.estrutura, zonas or [self.zona],
            linhas or [self.linha], medidas or self.medidas, resultado or self.resultado,
        )

    def test_sigla_com_opcao_unica_aparece_uma_vez(self):
        # CD (fator_localizacao) só tem uma seleção possível por estrutura.
        linhas = self._linhas()
        cds = [l for l in linhas if l["sigla"] == "CD"]
        self.assertEqual(len(cds), 1)
        self.assertEqual(cds[0]["denominacao"],
                          tabelas.info("anexo_a_tabela_a1_cd", "isolada")["descricao"])

    def test_sigla_com_varias_opcoes_selecionadas_pta(self):
        medidas = _medidas(medidas_pta_json='["avisos_de_alerta", "isolacao_eletrica"]')
        linhas = self._linhas(medidas=medidas)
        ptas = [l["denominacao"] for l in linhas if l["sigla"] == "PTA"]
        self.assertEqual(len(ptas), 2)
        self.assertIn(tabelas.info("anexo_b_tabela_b1_pta", "avisos_de_alerta")["descricao"], ptas)
        self.assertIn(tabelas.info("anexo_b_tabela_b1_pta", "isolacao_eletrica")["descricao"], ptas)
        # opções NÃO escolhidas (ex. "restrições físicas fixas") não aparecem
        nao_escolhida = tabelas.info("anexo_b_tabela_b1_pta", "restricoes_fisicas_fixas")["descricao"]
        self.assertNotIn(nao_escolhida, ptas)

    def test_pta_vazia_nao_gera_linha(self):
        medidas = _medidas(medidas_pta_json="[]")
        linhas = self._linhas(medidas=medidas)
        self.assertFalse(any(l["sigla"] == "PTA" for l in linhas))

    def test_entrada_em_branco_wm1_wm2_omitida_quando_nao_informada(self):
        linhas = self._linhas()  # wm1/wm2 = None no fixture padrão
        self.assertFalse(any(l["sigla"] == "wm1" for l in linhas))
        self.assertFalse(any(l["sigla"] == "wm2" for l in linhas))

    def test_entrada_em_branco_wm1_aparece_quando_informada(self):
        medidas = _medidas(largura_malha_externa_m=4.5)
        linhas = self._linhas(medidas=medidas)
        wm1 = [l for l in linhas if l["sigla"] == "wm1"]
        self.assertEqual(len(wm1), 1)
        self.assertIn("4.5", wm1[0]["valor"])

    def test_r3_oculto_quando_analise_nao_calcula_r3(self):
        # zona com valor de patrimônio cultural só é relevante se resultado.r3 não é None
        zona_com_cz = _zona(valor_patrimonio_cultural=50000)
        linhas = self._linhas(zonas=[zona_com_cz])  # self.resultado.r3 é None neste fixture
        self.assertIsNone(self.resultado.r3)
        self.assertFalse(any(l["sigla"] == "cz" for l in linhas))
        self.assertFalse(any(l["sigla"] == "ct" for l in linhas))
        self.assertFalse(any(l["sigla"] == "LF" and "C.9" in (l["referencia"] or "") for l in linhas))

    def test_r3_aparece_quando_analise_calcula_r3(self):
        zona_com_cz = _zona(valor_patrimonio_cultural=50000)
        resultado_dict, mem = riscos.calcular(
            self.estrutura, [zona_com_cz], [self.linha], self.medidas,
            ng=10, rt1=RT1, rt3=RT3, ft_valor=FT,
        )
        resultado = _resultado_de(resultado_dict, mem)
        self.assertIsNotNone(resultado.r3)
        linhas = self._linhas(zonas=[zona_com_cz], resultado=resultado)
        self.assertTrue(any(l["sigla"] == "cz" for l in linhas))
        self.assertTrue(any(l["sigla"] == "ct" for l in linhas))

    def test_r4_nunca_aparece(self):
        # R4 (Anexo D) não está implementado no motor — nenhuma linha deve citá-lo.
        linhas = self._linhas()
        for l in linhas:
            self.assertNotIn("Tabela D.2", l["referencia"] or "")

    def test_siglas_nao_modeladas_nunca_aparecem(self):
        # ADJ/CDJ (estrutura adjacente) e LFE/te (perdas fora da estrutura) — 6.4.1
        # permite desprezar NDJ nesta v1; não há campo algum que os alimente.
        linhas = self._linhas()
        siglas = {l["sigla"] for l in linhas}
        self.assertFalse(siglas & {"ADJ", "CDJ", "LFE", "te"})

    def test_zona_repete_sigla_com_contexto_por_zona(self):
        zona2 = _zona(nome="Zona 2", tipo_piso="brita_tapete_carpete")
        linhas = self._linhas(zonas=[self.zona, zona2])
        rts = [l for l in linhas if l["sigla"] == "rt"]
        self.assertEqual(len(rts), 2)
        contextos = {l["contexto"] for l in rts}
        self.assertIn('Zona "Zona única"', contextos)
        self.assertIn('Zona "Zona 2"', contextos)


class TestMemorialGeradoItem81(unittest.TestCase):
    """Fim a fim: o .docx exportado tem a tabela de Dados de Entrada em 8.1,
    só com o que foi selecionado, e o cálculo permanece idêntico ao anterior."""

    def setUp(self):
        self.estrutura = _estrutura()
        self.zona = _zona()
        self.linha = _linha()
        self.medidas = _medidas()
        self.analise = _analise()
        self.projeto = SimpleNamespace(numero_projeto="2026-01-0001", nome_projeto="Projeto Teste",
                                        cliente="Cliente Teste", revisao="Rev. 0")
        resultado_dict, mem = riscos.calcular(
            self.estrutura, [self.zona], [self.linha], self.medidas,
            ng=10, rt1=RT1, rt3=RT3, ft_valor=FT,
        )
        self.resultado_dict = resultado_dict
        self.resultado = _resultado_de(resultado_dict, mem)

    def test_calculo_identico_ao_caso_de_referencia_de_test_motor(self):
        # Mesmos números já verificados manualmente em TestRiscosCasoResolvido
        # (test_motor.py) — confirma que a mudança no exportador não afetou o cálculo.
        self.assertAlmostEqual(self.resultado_dict["r1"], 4.012638e-5, delta=4.012638e-5 * 1e-4)
        self.assertAlmostEqual(self.resultado_dict["f_total"], 12.424128, delta=1e-3)

    def _gerar(self):
        return exp.gerar_memorial(self.projeto, self.analise, self.estrutura, [self.zona],
                                   [self.linha], self.medidas, self.resultado)

    def test_docx_gerado_e_bem_formado(self):
        conteudo = self._gerar()
        buf = BytesIO(conteudo)
        with zipfile.ZipFile(buf) as z:
            self.assertIsNone(z.testzip())
            for nome in z.namelist():
                if nome.endswith(".xml") or nome.endswith(".rels"):
                    etree.fromstring(z.read(nome))

    def test_secao_dados_de_entrada_presente_antes_da_memoria_consolidada(self):
        from docx import Document
        conteudo = self._gerar()
        doc = Document(BytesIO(conteudo))
        titulos = [p.text.strip() for p in doc.paragraphs if p.style.name == "Heading 2"]
        self.assertIn("Dados de Entrada", titulos)
        self.assertIn("Memória de Cálculo Consolidada", titulos)
        self.assertLess(titulos.index("Dados de Entrada"), titulos.index("Memória de Cálculo Consolidada"))

    def test_placeholder_antigo_nao_aparece_mais(self):
        from docx import Document
        conteudo = self._gerar()
        doc = Document(BytesIO(conteudo))
        texto_completo = "\n".join(p.text for p in doc.paragraphs)
        for t in doc.tables:
            for row in t.rows:
                for cell in row.cells:
                    texto_completo += "\n" + cell.text
        self.assertNotIn("[Descrever a hipótese/premissa adotada para este projeto]", texto_completo)
        self.assertNotIn("Comentário", texto_completo)  # coluna do template antigo, substituída

    def test_tabela_8_1_tem_colunas_esperadas_e_so_opcoes_selecionadas(self):
        from docx import Document
        conteudo = self._gerar()
        doc = Document(BytesIO(conteudo))
        # localiza a tabela de Dados de Entrada pelo cabeçalho
        tabela_entrada = None
        for t in doc.tables:
            if t.rows and [c.text.strip() for c in t.rows[0].cells][:4] == ["Sigla", "Significado", "Denominação", "Valor assumido"]:
                tabela_entrada = t
                break
        self.assertIsNotNone(tabela_entrada, "Tabela de Dados de Entrada não encontrada no .docx gerado")

        siglas = {row.cells[0].text for row in tabela_entrada.rows[1:]}
        self.assertIn("CD", siglas)
        self.assertIn("PB", siglas)
        # PTA com uma medida selecionada no fixture -> aparece; a opção não
        # escolhida ("restrições físicas fixas") não deve aparecer em nenhuma linha
        denominacoes = {row.cells[2].text for row in tabela_entrada.rows[1:]}
        nao_escolhida = tabelas.info("anexo_b_tabela_b1_pta", "restricoes_fisicas_fixas")["descricao"]
        self.assertNotIn(nao_escolhida, denominacoes)
        # R3 não foi calculado neste fixture -> "cz"/"ct" não devem aparecer
        self.assertNotIn("cz", siglas)
        self.assertNotIn("ct", siglas)


if __name__ == "__main__":
    unittest.main()
