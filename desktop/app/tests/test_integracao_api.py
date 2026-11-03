"""
Teste de integração de ponta a ponta da Fase 3: sobe o app FastAPI completo
(core + app + routers) contra um banco SQLite temporário e exercita o fluxo
real de um projeto — equipamento, painel automático, infraestrutura, cabo
com percurso, memória de cálculo, relatórios em Excel e os endpoints
exclusivos do desktop (pasta de dados, backup/restauração).

Depende de `httpx` (só para o TestClient — não é dependência de runtime do
app, por isso não entra em `desktop/requirements.txt`).
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import criar_app  # noqa: E402


class TestFluxoCompletoDoProjeto(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="pe_desktop_api_")
        app = criar_app(pasta_dados=Path(self._tmp))
        self.client = TestClient(app)

    def test_fluxo_equipamento_painel_infra_cabo_relatorios(self):
        c = self.client

        projeto = c.post("/api/projetos", json={
            "numero_projeto": "2026-01-0001", "nome_projeto": "Casa de Bombas",
        }).json()
        pid = projeto["id"]

        equip = c.post(f"/api/projetos/{pid}/equipamentos", json={
            "tag": "CB-406", "descricao": "Bomba jockey", "tipo_carga": "motor",
            "potencia_valor": 5.5, "potencia_unidade": "kW", "rendimento": 1.0,
            "tensao_v": 380, "num_fases": 3, "possui_neutro": False, "possui_terra": True,
            "fator_potencia": 0.92, "fator_demanda": 1.0,
            "painel_transformador_tag": "QD-3302-403",
        }).json()
        self.assertAlmostEqual(equip["potencia_ativa_calc_kw"], 5.5, places=3)
        self.assertAlmostEqual(equip["corrente_nominal_a"], 9.08, places=1)

        paineis = c.get(f"/api/projetos/{pid}/paineis").json()
        self.assertEqual(len(paineis), 1, "garantir_painel deveria ter criado o painel automaticamente")
        painel = paineis[0]
        self.assertEqual(painel["tag"], "QD-3302-403")
        self.assertAlmostEqual(painel["demanda_total_kw"], 5.5, places=3)

        catalogo_infra = c.get("/api/catalogos/infraestrutura?tipo=eletroduto").json()
        self.assertTrue(catalogo_infra, "catálogo de infraestrutura deveria vir semeado")
        item_eletroduto = next(i for i in catalogo_infra if i["diametro_nominal_mm"] == 15.0)

        infra = c.post(f"/api/projetos/{pid}/eletrodutos-bandejas", json={
            "tag": "YF-002", "tipo": "eletroduto",
            "catalogo_infraestrutura_id": item_eletroduto["id"],
            "no_origem": "QD-3302-403", "no_destino": "CB-406", "comprimento_m": 10,
        }).json()
        self.assertEqual(infra["area_util_mm2"], 271.7)

        cabo = c.post(f"/api/projetos/{pid}/cabos", json={
            "tag": "YF-002", "painel_de_id": painel["id"], "equipamento_para_id": equip["id"],
            "tipo_isolacao": "EPR", "metodo_instalacao": "B1",
            "trechos": [{"eletroduto_bandeja_id": infra["id"], "ordem": 1}],
        }).json()
        self.assertEqual(cabo["secao_mm2"], 1.5)
        self.assertAlmostEqual(cabo["corrente_projeto_a"], 9.08, places=1)
        self.assertLess(cabo["queda_tensao_calc_pct"], 3.0)
        self.assertFalse(cabo["alerta_secao_insuficiente"])

        memoria = c.get(f"/api/projetos/{pid}/cabos/{cabo['id']}/memoria-calculo").json()
        self.assertEqual(len(memoria["passos"]), 9)
        self.assertEqual(memoria["passos"][0]["titulo"], "1. Dados de entrada (herdados da carga)")

        ocupacao = c.get(f"/api/projetos/{pid}/eletrodutos-bandejas/{infra['id']}/ocupacao").json()
        self.assertEqual(ocupacao["num_cabos_fisicos"], 1)
        self.assertEqual(len(ocupacao["cabos"]), 1)
        self.assertEqual(ocupacao["cabos"][0]["tag"], "YF-002")

        for nome in ("equipamentos.xlsx", "cabos.xlsx", "infraestrutura.xlsx", "cargas-demanda.xlsx", "memoria-calculo.xlsx"):
            resp = c.get(f"/api/projetos/{pid}/relatorios/{nome}")
            self.assertEqual(resp.status_code, 200, nome)
            self.assertTrue(resp.content.startswith(b"PK"), f"{nome} não parece um .xlsx válido")

    def test_sistema_info_backup_e_restauracao(self):
        c = self.client
        c.post("/api/projetos", json={"numero_projeto": "2026-01-0002", "nome_projeto": "Projeto para backup"})

        info = c.get("/api/sistema/info").json()
        self.assertEqual(Path(info["pasta_dados"]), Path(self._tmp))

        resp_backup = c.get("/api/sistema/backup.zip")
        self.assertEqual(resp_backup.status_code, 200)
        self.assertTrue(resp_backup.content.startswith(b"PK"))

        files = {"arquivo": ("backup.zip", resp_backup.content, "application/zip")}
        resp_restaurar = c.post("/api/sistema/restaurar", files=files)
        self.assertEqual(resp_restaurar.status_code, 200)
        self.assertTrue(resp_restaurar.json()["ok"])

        # o projeto continua lá depois de "restaurar" o próprio backup que acabou de tirar
        projetos = c.get("/api/projetos").json()
        self.assertEqual(len(projetos), 1)
        self.assertEqual(projetos[0]["numero_projeto"], "2026-01-0002")


if __name__ == "__main__":
    unittest.main()
