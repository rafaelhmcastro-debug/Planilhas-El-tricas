"""
Requisitos 1 e 2 do ajuste de 2026-11 (potência opcional para equipamentos
tipo "painel/quadro" e fim da contagem duplicada de cargas em "Cargas e
Demanda"): reproduz, com dados sintéticos, a MESMA estrutura relatada no
painel "CCM-TOP" do usuário — um painel TOP alimentado por 3 cargas diretas,
sendo que uma delas é, ao mesmo tempo, um equipamento tipo "painel/quadro" e
um painel cadastrado a jusante do próprio TOP (porque essa carga também tem
cargas próprias por baixo dela).

Os valores usados aqui (79,70 / 6,15 / 9,2 kW) são sintéticos — não são os
dados reais do projeto do usuário (que este ambiente não tem acesso) — mas
reproduzem a MESMA estrutura de tags (uma carga que é, ao mesmo tempo,
equipamento e painel filho do mesmo pai) que causa o bug relatado. Sobe o app
FastAPI completo contra um banco SQLite temporário e exercita o fluxo real
via HTTP, como `test_integracao_api.py`.
"""
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

from app.main import criar_app  # noqa: E402


class TestCargasSemContagemDuplicada(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="pe_desktop_dedup_")
        app = criar_app(pasta_dados=Path(self._tmp))
        self.client = TestClient(app)

    def _montar_cenario_tipo_ccm_top(self):
        c = self.client
        pid = c.post("/api/projetos", json={
            "numero_projeto": "2026-01-0099", "nome_projeto": "Cenário CCM-TOP (sintético)",
        }).json()["id"]

        c.post(f"/api/projetos/{pid}/paineis", json={
            "tag": "CCM-TOP", "tipo": "CCM", "tensao_v": 380, "num_fases": 3,
            "fator_diversidade": 1.0, "painel_alimentador_tag": "",
        })
        c.post(f"/api/projetos/{pid}/paineis", json={
            "tag": "0D-3302-402", "tipo": "painel", "tensao_v": 380, "num_fases": 3,
            "fator_diversidade": 1.0, "painel_alimentador_tag": "CCM-TOP",
        })

        def _equip(tag, tipo_carga, potencia_valor, painel_tag):
            payload = {
                "tag": tag, "tipo_carga": tipo_carga, "potencia_unidade": "kW", "rendimento": 1.0,
                "tensao_v": 380, "num_fases": 3, "fator_potencia": 0.92, "fator_demanda": 1.0,
                "painel_transformador_tag": painel_tag,
            }
            if potencia_valor is not None:
                payload["potencia_valor"] = potencia_valor
            r = c.post(f"/api/projetos/{pid}/equipamentos", json=payload)
            self.assertEqual(r.status_code, 200, r.text)
            return r.json()

        _equip("0D-3302-401", "motor", 79.70, "CCM-TOP")
        _equip("0D-3302-403", "motor", 6.15, "CCM-TOP")
        # A carga "0D-3302-402" é um equipamento tipo "painel/quadro" SEM
        # potência informada — e tem a MESMA tag do painel cadastrado acima,
        # que por sua vez tem sua própria carga (feita a seguir).
        equip_402 = _equip("0D-3302-402", "painel/quadro", None, "CCM-TOP")
        _equip("0D-3302-402-CARGA1", "motor", 9.2, "0D-3302-402")

        return pid, equip_402

    def test_potencia_do_equipamento_tipo_painel_e_a_soma_das_cargas_a_jusante(self):
        """Requisito 1: sem potência informada, P/Q do equipamento
        "0D-3302-402" vêm da soma das cargas alimentadas por ele (aqui, só
        "0D-3302-402-CARGA1" = 9,2 kW)."""
        pid, equip_402 = self._montar_cenario_tipo_ccm_top()
        c = self.client

        equip_atualizado = next(
            e for e in c.get(f"/api/projetos/{pid}/equipamentos").json() if e["tag"] == "0D-3302-402"
        )
        self.assertIsNone(equip_atualizado["potencia_valor"])
        self.assertAlmostEqual(equip_atualizado["potencia_ativa_calc_kw"], 9.2, places=3)

        painel_402 = next(p for p in c.get(f"/api/projetos/{pid}/paineis").json() if p["tag"] == "0D-3302-402")
        # Fonte única: o equipamento espelha exatamente o agregado do painel
        # de mesma tag — não duas contas divergentes para a mesma carga.
        self.assertAlmostEqual(equip_atualizado["potencia_ativa_calc_kw"], painel_402["potencia_instalada_kw"], places=6)

    def test_painel_top_nao_soma_a_carga_painel_duas_vezes(self):
        """Requisito 2: P instalada do CCM-TOP é a soma das 3 cargas diretas
        (79,70 + 6,15 + 9,2 = 95,05 kW) — não 79,70 + 6,15 + 9,2 + 9,2 =
        104,25 kW, que é o que o bug relatado produziria (a carga
        "0D-3302-402" contada uma vez como direta e outra como "painel a
        jusante" do mesmo pai)."""
        pid, _ = self._montar_cenario_tipo_ccm_top()
        c = self.client

        painel_top = next(p for p in c.get(f"/api/projetos/{pid}/paineis").json() if p["tag"] == "CCM-TOP")
        self.assertAlmostEqual(painel_top["potencia_instalada_kw"], 95.05, places=3)
        self.assertNotAlmostEqual(painel_top["potencia_instalada_kw"], 104.25, places=3)

        # fator_diversidade = 1.0 em todos os níveis deste cenário → demanda
        # com fator de diversidade = própria P instalada.
        self.assertAlmostEqual(painel_top["demanda_total_kw"], 95.05, places=3)

    def test_relatorio_cargas_demanda_bate_com_a_tela(self):
        """Requisito 3 (consistência do relatório com a tela, considerando a
        correção do requisito 2): a planilha "Cargas e Demanda" não deve
        mostrar, na linha TOTAL do CCM-TOP, um valor diferente do que a API
        (e portanto a tela) mostra para o mesmo painel."""
        pid, _ = self._montar_cenario_tipo_ccm_top()
        c = self.client

        painel_top = next(p for p in c.get(f"/api/projetos/{pid}/paineis").json() if p["tag"] == "CCM-TOP")

        resp = c.get(f"/api/projetos/{pid}/relatorios/cargas-demanda.xlsx")
        self.assertEqual(resp.status_code, 200)
        wb = load_workbook(io.BytesIO(resp.content))
        ws = wb["Cargas e Demanda"]
        linha_total = next(
            row for row in ws.iter_rows(min_row=2, values_only=True)
            if row[1] and str(row[1]).strip().startswith("TOTAL CCM-TOP")
        )
        p_inst_na_planilha = linha_total[6]  # coluna "P inst. (kW)"
        self.assertAlmostEqual(p_inst_na_planilha, painel_top["potencia_instalada_kw"], places=2)
        self.assertAlmostEqual(p_inst_na_planilha, 95.05, places=2)


if __name__ == "__main__":
    unittest.main()
