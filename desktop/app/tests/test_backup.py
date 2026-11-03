"""
Backup e restauração em .zip (requisito 4) — round-trip preserva os dados, e
restaurar nunca apaga o banco anterior sem guardar uma cópia antes.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import backup, models  # noqa: E402


class TestBackupRestauracao(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="pe_desktop_backup_"))
        self.caminho_banco = self._tmp / "dados.db"
        engine = create_engine(f"sqlite:///{self.caminho_banco}")
        models.Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        db.add(models.Projeto(numero_projeto="2026-01-0001", nome_projeto="Projeto do backup"))
        db.commit()
        db.close()
        engine.dispose()

    def test_round_trip_preserva_dados(self):
        destino_zip = self._tmp / "backup.zip"
        backup.criar_backup(self.caminho_banco, destino_zip)
        self.assertTrue(destino_zip.exists())

        outro_banco = self._tmp / "restaurado" / "dados.db"
        backup.restaurar_backup(destino_zip, outro_banco)

        engine = create_engine(f"sqlite:///{outro_banco}")
        db = sessionmaker(bind=engine)()
        projetos = db.query(models.Projeto).all()
        self.assertEqual(len(projetos), 1)
        self.assertEqual(projetos[0].nome_projeto, "Projeto do backup")

    def test_restaurar_guarda_copia_do_banco_anterior(self):
        destino_zip = self._tmp / "backup.zip"
        backup.criar_backup(self.caminho_banco, destino_zip)

        # Adiciona um projeto NOVO ao banco atual, depois restaura o backup antigo por cima.
        engine = create_engine(f"sqlite:///{self.caminho_banco}")
        db = sessionmaker(bind=engine)()
        db.add(models.Projeto(numero_projeto="2026-01-0002", nome_projeto="Criado depois do backup"))
        db.commit()
        db.close()
        engine.dispose()

        copia_seguranca = backup.restaurar_backup(destino_zip, self.caminho_banco)
        self.assertIsNotNone(copia_seguranca)
        self.assertTrue(copia_seguranca.exists())

        # O banco restaurado só tem o projeto original (do momento do backup).
        engine2 = create_engine(f"sqlite:///{self.caminho_banco}")
        db2 = sessionmaker(bind=engine2)()
        self.assertEqual(db2.query(models.Projeto).count(), 1)
        db2.close()
        engine2.dispose()

        # Mas o projeto criado depois do backup NÃO foi perdido — está na cópia de segurança.
        engine3 = create_engine(f"sqlite:///{copia_seguranca}")
        db3 = sessionmaker(bind=engine3)()
        tags = {p.numero_projeto for p in db3.query(models.Projeto).all()}
        self.assertIn("2026-01-0002", tags)
        db3.close()

    def test_restaurar_sem_banco_anterior_nao_gera_copia(self):
        destino_zip = self._tmp / "backup.zip"
        backup.criar_backup(self.caminho_banco, destino_zip)
        banco_novo = self._tmp / "nao_existia_ainda" / "dados.db"
        copia = backup.restaurar_backup(destino_zip, banco_novo)
        self.assertIsNone(copia)
        self.assertTrue(banco_novo.exists())

    def test_zip_invalido_levanta_erro_claro(self):
        zip_falso = self._tmp / "nao_e_um_backup.zip"
        import zipfile
        with zipfile.ZipFile(zip_falso, "w") as zf:
            zf.writestr("outra_coisa.txt", "não é um backup deste programa")
        with self.assertRaises(ValueError) as ctx:
            backup.validar_backup(zip_falso)
        self.assertIn("não parece ser um backup", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
