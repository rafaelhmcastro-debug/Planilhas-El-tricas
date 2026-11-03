"""
Prova de paridade: roda a MESMA entrada pela implementação web atual
(`cabos-app/app/calculations.py`, com SQLite real) e pelo núcleo portado
(`desktop/core/`, puro) e confere que os resultados batem exatamente —
critério de aceite "resultados do núcleo idênticos aos da versão web em todos
os casos de teste".

Sem pytest — roda com `python -m unittest`, como o resto do projeto.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "cabos-app"))
sys.path.insert(0, str(REPO_ROOT / "desktop"))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base  # noqa: E402
from app import models  # noqa: E402
from app import calculations  # noqa: E402
from app import seed_data  # noqa: E402

from core import cabos as core_cabos  # noqa: E402
from core import equipamentos as core_equip  # noqa: E402
from core import infraestrutura as core_infra  # noqa: E402
from core import paineis as core_paineis  # noqa: E402
from core import tabelas_normativas as core_tab  # noqa: E402


def _nova_sessao():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    seed_data.seed_if_empty(db)
    return db


def _carregar_tabelas_como_dicts(db):
    """Espelha o que a camada `app/` do desktop faria: carrega as tabelas
    normativas do banco e devolve como listas de dicts, prontas para o core."""
    def linhas(modelo, campos):
        return [{c: getattr(r, c) for c in campos} for r in db.query(modelo).all()]

    return {
        "capacidade": linhas(models.TabCapacidadeConducao,
                              ["isolacao_grupo", "metodo_instalacao", "num_condutores_carregados", "secao_mm2", "capacidade_a"]),
        "temperatura": linhas(models.TabFatorTemperatura, ["isolacao_grupo", "temperatura_c", "fator"]),
        "agrupamento": linhas(models.TabFatorAgrupamento, ["num_circuitos", "fator"]),
        "resistividade": linhas(models.TabResistividadeCondutor, ["secao_mm2", "resistencia_ohm_km"]),
        "limite_eletroduto": linhas(models.TabLimiteOcupacaoEletroduto, ["num_cabos", "taxa_max_pct"]),
    }


def _catalogo_cabos_como_dataclass(db):
    return [
        core_cabos.ItemCatalogoCabo(
            id=c.id, fabricante=c.fabricante, linha_produto=c.linha_produto,
            construcao_basica=c.construcao_basica, tipo_isolacao=c.tipo_isolacao,
            num_condutores=c.num_condutores, secao_nominal_mm2=c.secao_nominal_mm2,
            diametro_externo_nominal_mm=c.diametro_externo_nominal_mm,
            resistencia_condutor_20c_ohm_km=c.resistencia_condutor_20c_ohm_km,
            reatancia_ohm_km=c.reatancia_ohm_km,
        )
        for c in db.query(models.CatalogoCabo).all()
    ]


def _catalogo_infra_como_dataclass(db):
    return [
        core_infra.ItemCatalogoInfra(
            id=i.id, linha_produto=i.linha_produto, tipo=i.tipo,
            diametro_nominal_mm=i.diametro_nominal_mm, diametro_nominal_pol=i.diametro_nominal_pol,
            area_util_mm2=i.area_util_mm2, largura_nominal_mm=i.largura_nominal_mm, largura_util_mm=i.largura_util_mm,
        )
        for i in db.query(models.CatalogoInfraestrutura).all()
    ]


class TestParidadeEquipamento(unittest.TestCase):
    def setUp(self):
        self.db = _nova_sessao()
        self.projeto = models.Projeto(numero_projeto="2026-01-0001", nome_projeto="Paridade")
        self.db.add(self.projeto)
        self.db.flush()

    def _comparar(self, potencia_valor, potencia_unidade, rendimento, fp, tensao_v, num_fases, fd):
        equip = models.Equipamento(
            projeto_id=self.projeto.id, tag="M-01", potencia_valor=potencia_valor, potencia_unidade=potencia_unidade,
            rendimento=rendimento, fator_potencia=fp, tensao_v=tensao_v, num_fases=num_fases, fator_demanda=fd,
        )
        self.db.add(equip)
        self.db.flush()
        calculations.recalcular_equipamento(self.db, equip, recalcular_paineis=False)

        entrada = core_equip.EntradaEquipamento(
            potencia_valor=potencia_valor, potencia_unidade=potencia_unidade, rendimento=rendimento,
            fator_potencia=fp, tensao_v=tensao_v, num_fases=num_fases, fator_demanda=fd,
        )
        novo = core_equip.calcular_equipamento(entrada)

        for campo in ["potencia_nominal_kw", "potencia_ativa_calc_kw", "potencia_aparente_calc_kva",
                      "potencia_reativa_calc_kvar", "corrente_nominal_a", "potencia_demanda_kw",
                      "potencia_demanda_reativa_kvar"]:
            with self.subTest(campo=campo):
                self.assertAlmostEqual(getattr(equip, campo), getattr(novo, campo), places=6)

    def test_motor_trifasico_kw(self):
        self._comparar(30, "kW", 0.9, 0.86, 380, 3, 1.0)

    def test_carga_monofasica_w(self):
        self._comparar(1500, "W", 1.0, 0.92, 220, 1, 0.8)

    def test_informado_em_kva(self):
        self._comparar(50, "kVA", 1.0, 0.85, 380, 3, 1.0)

    def test_motor_em_cv(self):
        self._comparar(10, "CV", 0.88, 0.89, 380, 3, 0.75)


class TestParidadePaineis(unittest.TestCase):
    def setUp(self):
        self.db = _nova_sessao()
        self.projeto = models.Projeto(numero_projeto="2026-01-0002", nome_projeto="Paridade painéis")
        self.db.add(self.projeto)
        self.db.flush()

    def test_hierarquia_dois_niveis(self):
        pid = self.projeto.id
        top = models.PainelTransformador(projeto_id=pid, tag="TOP", tensao_v=380, num_fases=3, fator_diversidade=0.9)
        sub = models.PainelTransformador(projeto_id=pid, tag="QGBT-01", tensao_v=380, num_fases=3,
                                          fator_diversidade=0.8, painel_alimentador_tag="TOP")
        self.db.add_all([top, sub])
        self.db.flush()
        for tag, painel_tag, pot, fp in [("M-01", "QGBT-01", 30, 0.86), ("M-02", "TOP", 15, 0.9)]:
            e = models.Equipamento(projeto_id=pid, tag=tag, potencia_valor=pot, potencia_unidade="kW",
                                    rendimento=0.9, fator_potencia=fp, tensao_v=380, num_fases=3, fator_demanda=0.9,
                                    painel_transformador_tag=painel_tag)
            self.db.add(e)
            self.db.flush()
            calculations.recalcular_equipamento(self.db, e, recalcular_paineis=False)
        calculations.recalcular_paineis_projeto(self.db, pid)
        self.db.flush()

        paineis_antigos = {p.tag: p for p in self.db.query(models.PainelTransformador).filter_by(projeto_id=pid).all()}
        equip_antigos = self.db.query(models.Equipamento).filter_by(projeto_id=pid).all()

        entrada_paineis = [
            core_paineis.EntradaPainel(tag=p.tag, painel_alimentador_tag=p.painel_alimentador_tag or "",
                                        fator_diversidade=p.fator_diversidade, tensao_v=p.tensao_v, num_fases=p.num_fases or 3)
            for p in paineis_antigos.values()
        ]
        entrada_equip = [
            core_paineis.EntradaEquipamentoPainel(
                painel_transformador_tag=e.painel_transformador_tag or "",
                potencia_ativa_calc_kw=e.potencia_ativa_calc_kw, potencia_reativa_calc_kvar=e.potencia_reativa_calc_kvar,
                potencia_demanda_kw=e.potencia_demanda_kw, potencia_demanda_reativa_kvar=e.potencia_demanda_reativa_kvar,
                corrente_nominal_a=e.corrente_nominal_a,
            )
            for e in equip_antigos
        ]
        novos = core_paineis.calcular_paineis(entrada_paineis, entrada_equip)

        for tag in ("TOP", "QGBT-01"):
            antigo = paineis_antigos[tag]
            novo = novos[tag]
            with self.subTest(painel=tag):
                self.assertAlmostEqual(antigo.potencia_instalada_kw, novo.potencia_instalada_kw, places=6)
                self.assertAlmostEqual(antigo.demanda_total_kw, novo.demanda_total_kw, places=6)
                self.assertAlmostEqual(antigo.demanda_aparente_kva, novo.demanda_aparente_kva, places=6)
                self.assertAlmostEqual(antigo.corrente_total_a, novo.corrente_total_a, places=6)
                self.assertAlmostEqual(antigo.corrente_instalada_a, novo.corrente_instalada_a, places=6)


class TestParidadeCaboEOcupacao(unittest.TestCase):
    def setUp(self):
        self.db = _nova_sessao()
        self.projeto = models.Projeto(numero_projeto="2026-01-0003", nome_projeto="Paridade cabos")
        self.db.add(self.projeto)
        self.db.flush()
        pid = self.projeto.id

        self.equip = models.Equipamento(projeto_id=pid, tag="M-01", potencia_valor=30, potencia_unidade="kW",
                                         rendimento=0.9, fator_potencia=0.86, tensao_v=380, num_fases=3, fator_demanda=1.0,
                                         possui_neutro=False, possui_terra=True)
        self.db.add(self.equip)
        self.db.flush()
        calculations.recalcular_equipamento(self.db, self.equip, recalcular_paineis=False)

        item_eletroduto = self.db.query(models.CatalogoInfraestrutura).filter_by(
            tipo="eletroduto", linha_produto="Eletroduto Rígido Médio Eletrolítico/Pré-Zincado"
        ).order_by(models.CatalogoInfraestrutura.diametro_nominal_mm.desc()).first()
        self.infra = models.EletrodutoBandeja(projeto_id=pid, tag="ED-01", tipo="eletroduto",
                                               catalogo_infraestrutura_id=item_eletroduto.id, comprimento_m=45)
        self.infra.diametro_nominal_mm = item_eletroduto.diametro_nominal_mm
        self.infra.area_util_mm2 = item_eletroduto.area_util_mm2
        self.db.add(self.infra)
        self.db.flush()

        self.cabo = models.Cabo(projeto_id=pid, tag="C-01", equipamento_de_id=self.equip.id,
                                 equipamento_para_id=self.equip.id, tipo_isolacao="PVC", metodo_instalacao="B1",
                                 temperatura_ambiente_c=30, queda_tensao_admissivel_pct=3.0, num_cabos_paralelo=1)
        self.db.add(self.cabo)
        self.db.flush()
        self.db.add(models.CaboTrecho(cabo_id=self.cabo.id, eletroduto_bandeja_id=self.infra.id, ordem=0))
        self.db.flush()
        self.db.expire(self.cabo, ["trechos"])

    def test_dimensionamento_do_cabo_bate_com_o_web(self):
        calculations.recalcular_cabo(self.db, self.cabo)
        self.db.flush()

        tabs = _carregar_tabelas_como_dicts(self.db)
        catalogo = _catalogo_cabos_como_dataclass(self.db)

        e = self.equip
        carga = core_cabos.DadosCarga(
            tipo="equipamento", tag=e.tag, descricao=e.descricao or "", tensao_v=e.tensao_v, num_fases=e.num_fases,
            possui_neutro=bool(e.possui_neutro), possui_terra=bool(e.possui_terra), fp=e.fator_potencia,
            potencia_kw=e.potencia_ativa_calc_kw, potencia_kva=e.potencia_aparente_calc_kva,
            potencia_kvar=e.potencia_reativa_calc_kvar, rendimento=e.rendimento, potencia_valor=e.potencia_valor,
            potencia_unidade=e.potencia_unidade, corrente_a=e.corrente_nominal_a,
            origem_corrente="corrente nominal do equipamento",
        )
        entrada = core_cabos.EntradaCabo(
            tag=self.cabo.tag, tipo_isolacao=self.cabo.tipo_isolacao, metodo_instalacao=self.cabo.metodo_instalacao,
            temperatura_ambiente_c=self.cabo.temperatura_ambiente_c, queda_tensao_admissivel_pct=self.cabo.queda_tensao_admissivel_pct,
            num_cabos_paralelo=self.cabo.num_cabos_paralelo,
        )
        trechos = [core_cabos.TrechoPercurso(tag=self.infra.tag, tipo=self.infra.tipo, comprimento_m=self.infra.comprimento_m,
                                              ordem=0, num_circuitos=1)]

        novo, _mem = core_cabos.calcular_cabo(
            entrada, carga, trechos,
            tab_capacidade=tabs["capacidade"], tab_fator_temperatura=tabs["temperatura"],
            tab_fator_agrupamento=tabs["agrupamento"], tab_resistividade=tabs["resistividade"],
            catalogo_cabos=catalogo, de_tag=self.cabo.de_tag, para_tag=self.cabo.para_tag,
        )

        self.assertAlmostEqual(self.cabo.corrente_projeto_a, novo.corrente_projeto_a, places=6)
        self.assertEqual(self.cabo.secao_por_capacidade_mm2, novo.secao_por_capacidade_mm2)
        self.assertEqual(self.cabo.secao_por_queda_mm2, novo.secao_por_queda_mm2)
        self.assertEqual(self.cabo.secao_sugerida_mm2, novo.secao_sugerida_mm2)
        self.assertEqual(self.cabo.secao_mm2, novo.secao_mm2)
        self.assertAlmostEqual(self.cabo.queda_tensao_calc_pct, novo.queda_tensao_calc_pct, places=6)
        self.assertEqual(self.cabo.num_cabos_fisicos, novo.num_cabos_fisicos)
        self.assertEqual(self.cabo.alerta_secao_insuficiente, novo.alerta_secao_insuficiente)

    def test_ocupacao_do_eletroduto_bate_com_o_web(self):
        calculations.recalcular_cabo(self.db, self.cabo)
        self.db.flush()
        antigo = calculations.calcular_ocupacao(self.db, self.infra)

        tabs = _carregar_tabelas_como_dicts(self.db)
        catalogo_infra = _catalogo_infra_como_dataclass(self.db)
        item_escolhido = next((i for i in catalogo_infra if i.id == self.infra.catalogo_infraestrutura_id), None)

        entrada_infra = core_infra.EntradaInfra(
            id=self.infra.id, tag=self.infra.tag, tipo=self.infra.tipo,
            area_util_mm2=self.infra.area_util_mm2, largura_util_mm=self.infra.largura_util_mm,
            item_escolhido=item_escolhido,
        )
        cabos_no_trecho = [core_infra.CaboNoTrecho(
            tag=self.cabo.tag, de=self.cabo.de_tag, para=self.cabo.para_tag, secao_mm2=self.cabo.secao_mm2,
            diametro_externo_mm=self.cabo.diametro_externo_mm, area_secao_transversal_mm2=self.cabo.area_secao_transversal_mm2,
            tipo_construcao=self.cabo.tipo_construcao, num_cabos_paralelo=self.cabo.num_cabos_paralelo,
            num_cabos_fisicos=self.cabo.num_cabos_fisicos,
        )]

        novo = core_infra.calcular_ocupacao(
            entrada_infra, cabos_no_trecho,
            tab_limite_ocupacao_eletroduto=tabs["limite_eletroduto"], catalogo_infraestrutura=catalogo_infra,
        )

        self.assertAlmostEqual(antigo["area_ocupada_mm2"], novo.area_ocupada_mm2, places=6)
        self.assertAlmostEqual(antigo["ocupacao_pct"], novo.ocupacao_pct, places=6)
        self.assertEqual(antigo["limite_pct"], novo.limite_pct)
        self.assertEqual(antigo["alerta"], novo.alerta)
        self.assertEqual(antigo["dimensao_sugerida_id"], novo.dimensao_sugerida.id if novo.dimensao_sugerida else None)


if __name__ == "__main__":
    unittest.main()
