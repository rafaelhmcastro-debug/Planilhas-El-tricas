"""
Migrações versionadas (Alembic) — requisito 3: nunca apagar dados do usuário
em silêncio. Confere que a primeira execução cria o esquema do zero, que
rodar de novo não duplica nada (idempotente) e que os dados sobrevivem.
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import migracoes  # noqa: E402
from app.models import Projeto  # noqa: E402


class TestMigracoes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="pe_desktop_migracoes_")
        self.caminho_banco = Path(self._tmp) / "dados.db"

    def test_primeira_execucao_cria_todas_as_tabelas(self):
        migracoes.aplicar_migracoes(self.caminho_banco)
        conn = sqlite3.connect(str(self.caminho_banco))
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        esperadas = {
            "projetos", "equipamentos", "eletrodutos_bandejas", "cabos", "cabo_trechos",
            "paineis_transformadores", "catalogo_cabos", "catalogo_infraestrutura_eletrica",
            "tab_capacidade_conducao", "tab_fator_temperatura", "tab_fator_agrupamento",
            "tab_resistividade_condutor", "tab_limite_ocupacao_eletroduto", "tab_limite_ocupacao_bandeja",
            "alembic_version",
        }
        self.assertTrue(esperadas.issubset(tabelas), f"Faltando: {esperadas - tabelas}")

    def test_rodar_duas_vezes_nao_apaga_dados(self):
        migracoes.aplicar_migracoes(self.caminho_banco)
        engine = create_engine(f"sqlite:///{self.caminho_banco}")
        Sessao = sessionmaker(bind=engine)
        db = Sessao()
        db.add(Projeto(numero_projeto="2026-01-0001", nome_projeto="Sobrevive à remigração"))
        db.commit()
        db.close()
        engine.dispose()

        # Roda de novo (simula o app abrindo uma segunda vez) — não deve recriar nem apagar nada.
        migracoes.aplicar_migracoes(self.caminho_banco)

        engine2 = create_engine(f"sqlite:///{self.caminho_banco}")
        Sessao2 = sessionmaker(bind=engine2)
        db2 = Sessao2()
        self.assertEqual(db2.query(Projeto).count(), 1)
        self.assertEqual(db2.query(Projeto).first().nome_projeto, "Sobrevive à remigração")
        db2.close()

    def test_revisao_atual(self):
        self.assertIsNone(migracoes.revisao_atual(self.caminho_banco))  # banco ainda não existe
        migracoes.aplicar_migracoes(self.caminho_banco)
        self.assertIsNotNone(migracoes.revisao_atual(self.caminho_banco))

    def test_evolucao_de_esquema_preserva_dados_existentes(self):
        """Requisito 3: nunca apagar dados do usuário silenciosamente numa
        migração. Simula uma futura migração que adiciona uma coluna (caso
        comum de evolução de esquema) usando o mesmo mecanismo de batch mode
        configurado em app/migrations/env.py (render_as_batch=True,
        necessário no SQLite) e confere que os dados sobrevivem."""
        migracoes.aplicar_migracoes(self.caminho_banco)
        engine = create_engine(f"sqlite:///{self.caminho_banco}")
        Sessao = sessionmaker(bind=engine)
        db = Sessao()
        db.add(Projeto(numero_projeto="2026-01-0001", nome_projeto="Antes da evolução de esquema"))
        db.commit()
        db.close()

        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        import sqlalchemy as sa

        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn)
            ops = Operations(ctx)
            with ops.batch_alter_table("projetos") as batch_op:
                batch_op.add_column(sa.Column("campo_novo_hipotetico", sa.String(), nullable=True))

        db2 = Sessao()
        projeto = db2.query(Projeto).filter_by(numero_projeto="2026-01-0001").first()
        self.assertIsNotNone(projeto, "Projeto cadastrado antes da evolução de esquema desapareceu!")
        self.assertEqual(projeto.nome_projeto, "Antes da evolução de esquema")
        db2.close()

        conn2 = sqlite3.connect(str(self.caminho_banco))
        colunas = {r[1] for r in conn2.execute("PRAGMA table_info(projetos)")}
        conn2.close()
        self.assertIn("campo_novo_hipotetico", colunas)


if __name__ == "__main__":
    unittest.main()
