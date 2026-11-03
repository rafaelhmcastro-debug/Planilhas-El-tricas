"""
Carga inicial das tabelas normativas/catálogos a partir de seed/*.json.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import models, seed  # noqa: E402


class TestSeed(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def test_semeia_todas_as_tabelas(self):
        seed.seed_if_empty(self.db)
        self.assertEqual(self.db.query(models.TabCapacidadeConducao).count(), 528)
        self.assertEqual(self.db.query(models.TabFatorTemperatura).count(), 26)
        self.assertEqual(self.db.query(models.TabFatorAgrupamento).count(), 12)
        self.assertEqual(self.db.query(models.TabResistividadeCondutor).count(), 18)
        self.assertEqual(self.db.query(models.TabLimiteOcupacaoEletroduto).count(), 3)
        self.assertEqual(self.db.query(models.TabLimiteOcupacaoBandeja).count(), 1)
        self.assertEqual(self.db.query(models.CatalogoInfraestrutura).count(), 47)
        self.assertEqual(self.db.query(models.CatalogoCabo).count(), 208)

    def test_rodar_duas_vezes_nao_duplica(self):
        seed.seed_if_empty(self.db)
        total_antes = self.db.query(models.CatalogoCabo).count()
        seed.seed_if_empty(self.db)
        total_depois = self.db.query(models.CatalogoCabo).count()
        self.assertEqual(total_antes, total_depois)

    def test_nao_sobrescreve_dado_que_o_usuario_ja_importou(self):
        # Simula o usuário já tendo importado seu próprio catálogo de cabos
        # antes do seed rodar (ex.: banco restaurado de um backup antigo).
        self.db.add(models.CatalogoCabo(
            fabricante="Fabricante Próprio", linha_produto="Linha X", tipo_isolacao="PVC",
            num_condutores=1, secao_nominal_mm2=2.5, diametro_externo_nominal_mm=4.0,
        ))
        self.db.commit()
        seed.seed_if_empty(self.db)
        # A tabela catalogo_cabos já não estava vazia -> seed não mexe nela.
        self.assertEqual(self.db.query(models.CatalogoCabo).count(), 1)
        # As outras tabelas (vazias) continuam sendo semeadas normalmente.
        self.assertEqual(self.db.query(models.TabCapacidadeConducao).count(), 528)


if __name__ == "__main__":
    unittest.main()
