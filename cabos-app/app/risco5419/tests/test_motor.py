"""
Testes do motor de cálculo de risco (NBR 5419-2). Sem pytest — o projeto não
usa esse framework; roda com `python -m unittest` (stdlib).
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.risco5419 import tabelas, eventos, probabilidades, perdas, riscos  # noqa: E402


class TestTabelas(unittest.TestCase):
    def test_valor_existente(self):
        self.assertEqual(tabelas.valor("anexo_b_tabela_b2_pb", "spda_np_i"), 0.02)

    def test_valor_nulo_levanta_erro_claro(self):
        with self.assertRaises(tabelas.ValorNaoDisponivel) as ctx:
            tabelas.valor("anexo_b_tabela_b3_pspd", "melhor_que_np_i")
        msg = str(ctx.exception)
        self.assertIn("anexo_b_tabela_b3_pspd", msg)
        self.assertIn("melhor_que_np_i", msg)

    def test_chave_inexistente_levanta_erro(self):
        with self.assertRaises(tabelas.ValorNaoDisponivel):
            tabelas.valor("anexo_b_tabela_b2_pb", "chave_que_nao_existe")

    def test_valor_por_uw_coluna_exata(self):
        self.assertEqual(tabelas.valor_por_uw("anexo_b_tabela_b9_pli", "linhas_energia", 6), 0.1)

    def test_valor_por_uw_usa_coluna_inferior_conservadora(self):
        # UW=1.2 entre as colunas 1 e 1.5 -> usa a coluna 1 (mais conservadora)
        v_120 = tabelas.valor_por_uw("anexo_b_tabela_b9_pli", "linhas_energia", 1.2)
        v_100 = tabelas.valor_por_uw("anexo_b_tabela_b9_pli", "linhas_energia", 1.0)
        self.assertEqual(v_120, v_100)

    def test_valor_por_uw_abaixo_da_menor_coluna_levanta_erro(self):
        with self.assertRaises(tabelas.ValorNaoDisponivel):
            tabelas.valor_por_uw("anexo_b_tabela_b8_pld", "nao_blindada_ou_blindagem_nao_interligada", 0.1)


class TestEventos(unittest.TestCase):
    def test_area_ad_equacao_a1(self):
        # AD = L×W + 2×(3H)×(L+W) + π×(3H)²  (L=20,W=10,H=6)
        esperado = 20 * 10 + 2 * 18 * 30 + 3.14159265358979 * 18 ** 2
        self.assertAlmostEqual(eventos.area_ad(20, 10, 6), esperado, places=3)

    def test_nd_equacao_a3(self):
        self.assertAlmostEqual(eventos.nd(ng=10, ad_m2=2297.876, cd=1), 10 * 2297.876 * 1 * 1e-6, places=9)


class TestProbabilidades(unittest.TestCase):
    def test_pa_equacao_b1(self):
        self.assertAlmostEqual(probabilidades.pa(pta=0.1, pb=0.05), 0.005)

    def test_ks1_sem_blindagem_e_1(self):
        self.assertEqual(probabilidades.ks1_ks2(None), 1.0)

    def test_ks4_limitado_a_1(self):
        self.assertEqual(probabilidades.ks4(0.5), 1.0)  # 1/0.5=2, mas o máximo é 1


class TestPerdas(unittest.TestCase):
    def test_perda_choque_r1(self):
        # LA = LU = rt×LT×(nz/nt)×(tz/8760)×rs
        v = perdas.perda_choque_r1(rt=1e-2, lt=1e-2, nz=50, nt=50, tz=8760, rs=1)
        self.assertAlmostEqual(v, 1e-4)

    def test_perda_choque_r1_nt_zero_levanta_erro(self):
        with self.assertRaises(ValueError):
            perdas.perda_choque_r1(rt=1e-2, lt=1e-2, nz=0, nt=0, tz=8760, rs=1)


class TestRiscosCasoResolvido(unittest.TestCase):
    """Caso de referência resolvido manualmente (ver docstring de cada etapa)."""

    def setUp(self):
        self.estrutura = SimpleNamespace(
            comprimento_m=20, largura_m=10, altura_m=6, fator_localizacao="isolada",
            tipo_construcao="robusta_metalica_concreto_armado", risco_explosao=False,
            falha_sistema_interno_risco_vida=False, num_pessoas_total=50,
        )
        self.zona = SimpleNamespace(
            nome="Zona única", num_pessoas_zona=50, tempo_pessoas_horas_ano=8760,
            tipo_piso="terra_concreto", providencias_incendio="nenhuma_ou_risco_explosao",
            risco_incendio="incendio_normal", perigo_especial="sem_perigo_especial",
            categoria_dano_fisico_lf="outros", categoria_falha_sistema_lo="outras_partes_hospital",
            valor_patrimonio_cultural=None,
        )
        trecho = SimpleNamespace(
            comprimento_m=500, tipo_instalacao="aereo", ambiente="rural",
            categoria_blindagem="aerea_nao_blindada_sem_ligacao",
            categoria_pld="nao_blindada_ou_blindagem_nao_interligada",
        )
        self.linha = SimpleNamespace(tag="L1", tipo="energia", tem_transformador_at_bt=False,
                                      tensao_suportavel_kv=1.5, trechos=[trecho])
        self.medidas = SimpleNamespace(
            classe_spda="spda_np_ii", medidas_pta_json='["avisos_de_alerta"]',
            dps_coordenado="nenhum_sistema_coordenado_dps", dps_classe_i="sem_dps_classe_i",
            medida_ptu="nenhuma_medida", fiacao_interna="blindado_ou_em_conduto_metalico",
            largura_malha_externa_m=None, largura_malha_interna_m=None,
            tensao_suportavel_sistema_interno_kv=1.5,
        )
        self.rt1 = tabelas.valor("tabela_04_risco_toleravel", "rt_r1")
        self.rt3 = tabelas.valor("tabela_04_risco_toleravel", "rt_r3")
        self.ft = tabelas.valor("tabela_07_frequencia_toleravel", "sistema_nao_critico")

    def test_r1_bate_com_calculo_manual(self):
        resultado, _mem = riscos.calcular(
            self.estrutura, [self.zona], [self.linha], self.medidas,
            ng=10, rt1=self.rt1, rt3=self.rt3, ft_valor=self.ft,
        )
        # RA+RB+RU+RV calculados manualmente (RC/RM/RW/RZ=0, sem risco de explosão)
        self.assertAlmostEqual(resultado["r1"], 4.012638e-5, delta=4.012638e-5 * 1e-4)
        self.assertFalse(resultado["r1_atende"])  # R1 > RT1 = 1e-5
        self.assertIsNone(resultado["r3"])  # nenhuma zona com valor de patrimônio cultural

    def test_f_bate_com_calculo_manual(self):
        resultado, _mem = riscos.calcular(
            self.estrutura, [self.zona], [self.linha], self.medidas,
            ng=10, rt1=self.rt1, rt3=self.rt3, ft_valor=self.ft,
        )
        self.assertAlmostEqual(resultado["f_total"], 12.424128, delta=1e-3)

    def test_risco_explosao_ativa_rc_rm_rw_rz(self):
        self.estrutura.risco_explosao = True
        resultado, _mem = riscos.calcular(
            self.estrutura, [self.zona], [self.linha], self.medidas,
            ng=10, rt1=self.rt1, rt3=self.rt3, ft_valor=self.ft,
        )
        self.assertGreater(resultado["r1"], 4.012638e-5 * 10)  # cresce bastante com RC/RM/RW/RZ

    def test_zona_com_patrimonio_cultural_calcula_r3(self):
        self.zona.valor_patrimonio_cultural = 50000
        resultado, _mem = riscos.calcular(
            self.estrutura, [self.zona], [self.linha], self.medidas,
            ng=10, rt1=self.rt1, rt3=self.rt3, ft_valor=self.ft,
        )
        self.assertAlmostEqual(resultado["r3"], 0.00020114894, delta=1e-9)


if __name__ == "__main__":
    unittest.main()
