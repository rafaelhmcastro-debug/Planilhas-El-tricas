"""
Resolução da pasta de dados local (ADR 0001 §6) — requisito 2 (pasta
configurável) e requisito 8 (caminhos com espaço/acento funcionam).
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import database  # noqa: E402


class TestResolucaoPastaDados(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="pe_desktop_test_")
        self._env_originais = {}
        for var in ("APPDATA", "LOCALAPPDATA"):
            self._env_originais[var] = __import__("os").environ.get(var)
        import os
        os.environ["APPDATA"] = str(Path(self._tmp) / "Roaming")
        os.environ["LOCALAPPDATA"] = str(Path(self._tmp) / "Local")

    def tearDown(self):
        import os
        for var, valor in self._env_originais.items():
            if valor is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = valor
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_primeira_execucao_cria_ponteiro_apontando_para_pasta_padrao(self):
        self.assertFalse(database.caminho_config().exists())
        pasta = database.resolver_pasta_dados()
        self.assertEqual(pasta, database.pasta_dados_padrao())
        self.assertTrue(pasta.exists())
        self.assertTrue(database.caminho_config().exists())

    def test_segunda_chamada_le_o_mesmo_ponteiro(self):
        pasta1 = database.resolver_pasta_dados()
        pasta2 = database.resolver_pasta_dados()
        self.assertEqual(pasta1, pasta2)

    def test_trocar_pasta_de_dados_atualiza_o_ponteiro(self):
        nova_pasta = Path(self._tmp) / "Outro Local com Espaço"
        database.definir_pasta_dados(nova_pasta)
        self.assertEqual(database.resolver_pasta_dados(), nova_pasta)
        self.assertTrue(nova_pasta.exists())

    def test_caminho_com_espaco_e_acento_funciona(self):
        # Requisito 8: C:\Users\João\Documentos — simulado aqui com um nome
        # de pasta com espaço e acentuação.
        pasta = Path(self._tmp) / "Usuários" / "João da Silva" / "Meus Documentos"
        database.definir_pasta_dados(pasta)
        resolvida = database.resolver_pasta_dados()
        self.assertEqual(resolvida, pasta)
        self.assertTrue(resolvida.exists())

        engine = database.criar_engine(pasta)
        Fabrica = database.criar_fabrica_sessao(engine)
        from app.models import Base, Projeto
        Base.metadata.create_all(engine)
        db = Fabrica()
        db.add(Projeto(numero_projeto="2026-01-0001", nome_projeto="Teste caminho acentuado"))
        db.commit()
        self.assertEqual(db.query(Projeto).count(), 1)
        db.close()
        self.assertTrue(database.caminho_banco(pasta).exists())


if __name__ == "__main__":
    unittest.main()
