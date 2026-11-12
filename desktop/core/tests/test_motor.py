"""
Testes do núcleo de cálculo (desktop/core/) com casos de referência calculados
à mão (independentemente da implementação), no mesmo padrão já usado em
`cabos-app/app/risco5419/tests/test_motor.py`. Complementa
`test_paridade_com_web.py` (que confere contra a implementação web real) com
uma segunda linha de evidência independente, para o caso de a própria
implementação original compartilhar algum defeito latente.

Sem pytest — roda com `python -m unittest`.
"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core import equipamentos as core_equip  # noqa: E402
from core import paineis as core_paineis  # noqa: E402
from core import tabelas_normativas as core_tab  # noqa: E402
from core.eletrica import corrente_por_aparente  # noqa: E402


class TestEquipamentoCasoResolvido(unittest.TestCase):
    """Motor trifásico 30 kW, η=0,9, cos φ=0,86, 380 V, FD=1 — resolvido à mão:
    P = Pn/η = 30/0,9 = 33,3333 kW
    S = P/cosφ = 33,3333/0,86 = 38,7597 kVA
    Q = √(S²−P²) = √(38,7597² − 33,3333²) = 19,7788 kvar
    I = S×1000/(√3×V) = 38759,7/(1,7320508×380) = 58,8893 A
    """

    def test_motor_trifasico_kw(self):
        entrada = core_equip.EntradaEquipamento(
            potencia_valor=30, potencia_unidade="kW", rendimento=0.9,
            fator_potencia=0.86, tensao_v=380, num_fases=3, fator_demanda=1.0,
        )
        r = core_equip.calcular_equipamento(entrada)
        self.assertAlmostEqual(r.potencia_ativa_calc_kw, 33.333333, places=4)
        self.assertAlmostEqual(r.potencia_aparente_calc_kva, 38.759690, places=4)
        self.assertAlmostEqual(r.potencia_reativa_calc_kvar, 19.778838, places=4)
        self.assertAlmostEqual(r.corrente_nominal_a, 58.889256, places=4)
        self.assertAlmostEqual(r.potencia_demanda_kw, 33.333333, places=4)  # FD=1

    def test_informado_em_kva_nao_aplica_rendimento(self):
        # Carga informada direto em kVA: S é a própria potência absorvida da
        # rede; o rendimento não entra (não há "potência no eixo" a converter).
        entrada = core_equip.EntradaEquipamento(
            potencia_valor=10, potencia_unidade="kVA", rendimento=0.5,  # rendimento não deve afetar o resultado
            fator_potencia=0.9, tensao_v=220, num_fases=1, fator_demanda=1.0,
        )
        r = core_equip.calcular_equipamento(entrada)
        self.assertAlmostEqual(r.potencia_aparente_calc_kva, 10.0, places=6)
        self.assertAlmostEqual(r.potencia_ativa_calc_kw, 9.0, places=6)  # P = S×cosφ
        self.assertAlmostEqual(r.corrente_nominal_a, 10 * 1000 / 220, places=4)  # monofásico: I = S×1000/V

    def test_sem_potencia_informada_tudo_none(self):
        entrada = core_equip.EntradaEquipamento(potencia_valor=None)
        r = core_equip.calcular_equipamento(entrada)
        self.assertIsNone(r.potencia_ativa_calc_kw)
        self.assertIsNone(r.corrente_nominal_a)


class TestEquipamentoTipoPainel(unittest.TestCase):
    """Requisito 1 (potência opcional para equipamentos tipo "painel/quadro"):
    P/Q vêm de uma soma já agregada (não de uma potência nominal digitada) —
    P=80 kW, Q=40 kvar, 380 V trifásico, FD=0,8:
    S = √(80² + 40²) = 89,442719 kVA
    I = S×1000/(√3×380) = 135,928871 A
    Pd = P×FD = 64 kW ; Qd = Q×FD = 32 kvar
    """

    def test_deriva_s_e_in_da_soma_agregada_sem_rendimento_nem_cosfi(self):
        r = core_equip.calcular_equipamento_tipo_painel(
            potencia_ativa_kw=80.0, potencia_reativa_kvar=40.0,
            tensao_v=380, num_fases=3, fator_demanda=0.8,
        )
        s_esperado = math.sqrt(80.0 ** 2 + 40.0 ** 2)
        self.assertIsNone(r.potencia_nominal_kw)
        self.assertAlmostEqual(r.potencia_ativa_calc_kw, 80.0, places=6)
        self.assertAlmostEqual(r.potencia_reativa_calc_kvar, 40.0, places=6)
        self.assertAlmostEqual(r.potencia_aparente_calc_kva, s_esperado, places=6)
        self.assertAlmostEqual(r.corrente_nominal_a, corrente_por_aparente(s_esperado, 380, 3), places=6)
        self.assertAlmostEqual(r.potencia_demanda_kw, 64.0, places=6)
        self.assertAlmostEqual(r.potencia_demanda_reativa_kvar, 32.0, places=6)

    def test_sem_cargas_a_jusante_resulta_em_zero_nao_em_erro(self):
        # S=0 → `corrente_por_aparente` devolve None (mesma convenção do
        # resto do núcleo para "não há corrente a calcular", não 0.0).
        r = core_equip.calcular_equipamento_tipo_painel(
            potencia_ativa_kw=0.0, potencia_reativa_kvar=0.0, tensao_v=380, num_fases=3,
        )
        self.assertEqual(r.potencia_ativa_calc_kw, 0.0)
        self.assertIsNone(r.corrente_nominal_a)


class TestPaineisSemContagemDuplicada(unittest.TestCase):
    """Requisito 2 (cargas duplicadas): reproduz a estrutura do bug relatado —
    um painel TOP alimentado por 3 cargas diretas, sendo que uma delas ("SUB")
    tem a MESMA tag de um painel cadastrado a jusante do próprio TOP (porque
    "SUB" também tem cargas próprias por baixo dele). Antes da correção,
    `calcular_paineis` somava a contribuição de "SUB" duas vezes no TOP: uma
    como carga direta (equip_por_painel) e outra como painel filho (filhos) —
    exatamente o padrão do CCM-TOP relatado (loads aparecendo em dobro)."""

    def test_carga_que_e_tambem_painel_filho_nao_e_somada_duas_vezes(self):
        paineis = [
            core_paineis.EntradaPainel(tag="TOP", painel_alimentador_tag="", fator_diversidade=1.0),
            core_paineis.EntradaPainel(tag="SUB", painel_alimentador_tag="TOP", fator_diversidade=1.0),
        ]
        equipamentos = [
            core_paineis.EntradaEquipamentoPainel(
                tag="A", painel_transformador_tag="TOP",
                potencia_ativa_calc_kw=50.0, potencia_reativa_calc_kvar=20.0,
                potencia_demanda_kw=50.0, potencia_demanda_reativa_kvar=20.0, corrente_nominal_a=10.0,
            ),
            # "SUB" aparece aqui como carga direta de TOP (já sincronizada com
            # o agregado do painel "SUB" — ver Requisito 1) e TAMBÉM como
            # painel filho de TOP, abaixo — é exatamente o caso que não pode
            # ser somado duas vezes.
            core_paineis.EntradaEquipamentoPainel(
                tag="SUB", painel_transformador_tag="TOP",
                potencia_ativa_calc_kw=9.2, potencia_reativa_calc_kvar=5.0,
                potencia_demanda_kw=9.2, potencia_demanda_reativa_kvar=5.0, corrente_nominal_a=14.0,
            ),
            core_paineis.EntradaEquipamentoPainel(
                tag="C", painel_transformador_tag="TOP",
                potencia_ativa_calc_kw=30.0, potencia_reativa_calc_kvar=10.0,
                potencia_demanda_kw=30.0, potencia_demanda_reativa_kvar=10.0, corrente_nominal_a=6.0,
            ),
            core_paineis.EntradaEquipamentoPainel(
                tag="SUB-CARGA1", painel_transformador_tag="SUB",
                potencia_ativa_calc_kw=9.2, potencia_reativa_calc_kvar=5.0,
                potencia_demanda_kw=9.2, potencia_demanda_reativa_kvar=5.0, corrente_nominal_a=14.0,
            ),
        ]
        resultados = core_paineis.calcular_paineis(paineis, equipamentos)

        # SUB: só a carga própria dele (SUB-CARGA1) — nada do que TOP recebe.
        self.assertAlmostEqual(resultados["SUB"].potencia_instalada_kw, 9.2, places=6)
        self.assertAlmostEqual(resultados["SUB"].potencia_reativa_instalada_kvar, 5.0, places=6)

        # TOP: A + C + (agregado de SUB) = 50 + 30 + 9,2 = 89,2 — NÃO
        # 50 + 9,2 + 30 + 9,2 = 98,4, que seria o resultado com o bug (carga
        # "SUB" contada como direta E como contribuição do painel filho).
        self.assertAlmostEqual(resultados["TOP"].potencia_instalada_kw, 89.2, places=6)
        self.assertAlmostEqual(resultados["TOP"].potencia_reativa_instalada_kvar, 35.0, places=6)


class TestCorrentePorAparente(unittest.TestCase):
    def test_trifasico(self):
        # I = S×1000/(√3×V) — 100 kVA a 380 V trifásico
        esperado = 100 * 1000 / (math.sqrt(3) * 380)
        self.assertAlmostEqual(corrente_por_aparente(100, 380, 3), esperado, places=6)

    def test_monofasico(self):
        # I = S×1000/V — 5 kVA a 127 V monofásico
        self.assertAlmostEqual(corrente_por_aparente(5, 127, 1), 5000 / 127, places=6)

    def test_sem_tensao_retorna_none(self):
        self.assertIsNone(corrente_por_aparente(10, 0, 3))
        self.assertIsNone(corrente_por_aparente(10, None, 3))


class TestTabelasNormativas(unittest.TestCase):
    def test_fator_temperatura_interpola_linear(self):
        linhas = [
            {"isolacao_grupo": "PVC", "temperatura_c": 25, "fator": 1.06},
            {"isolacao_grupo": "PVC", "temperatura_c": 30, "fator": 1.00},
        ]
        # 27,5°C é exatamente o meio do intervalo -> fator médio
        f = core_tab.fator_temperatura(linhas, "PVC", 27.5)
        self.assertAlmostEqual(f, (1.06 + 1.00) / 2, places=6)

    def test_fator_temperatura_fora_da_faixa_usa_extremo(self):
        linhas = [
            {"isolacao_grupo": "PVC", "temperatura_c": 25, "fator": 1.06},
            {"isolacao_grupo": "PVC", "temperatura_c": 30, "fator": 1.00},
        ]
        self.assertEqual(core_tab.fator_temperatura(linhas, "PVC", 50), 1.00)
        self.assertEqual(core_tab.fator_temperatura(linhas, "PVC", 0), 1.06)

    def test_fator_agrupamento_usa_proximo_valor_para_cima(self):
        linhas = [{"num_circuitos": 1, "fator": 1.0}, {"num_circuitos": 4, "fator": 0.65}, {"num_circuitos": 9, "fator": 0.5}]
        # 5 circuitos não tabelado -> usa o próximo tabelado para cima (9 -> mais conservador)
        self.assertEqual(core_tab.fator_agrupamento(linhas, 5), 0.5)

    def test_fator_agrupamento_exato(self):
        linhas = [{"num_circuitos": 1, "fator": 1.0}, {"num_circuitos": 4, "fator": 0.65}]
        self.assertEqual(core_tab.fator_agrupamento(linhas, 4), 0.65)

    def test_limite_ocupacao_eletroduto_por_faixa(self):
        linhas = [{"num_cabos": "1", "taxa_max_pct": 53}, {"num_cabos": "2", "taxa_max_pct": 31}, {"num_cabos": "3+", "taxa_max_pct": 40}]
        self.assertEqual(core_tab.limite_ocupacao_eletroduto(linhas, 1), 53)
        self.assertEqual(core_tab.limite_ocupacao_eletroduto(linhas, 2), 31)
        self.assertEqual(core_tab.limite_ocupacao_eletroduto(linhas, 3), 40)
        self.assertEqual(core_tab.limite_ocupacao_eletroduto(linhas, 10), 40)


if __name__ == "__main__":
    unittest.main()
