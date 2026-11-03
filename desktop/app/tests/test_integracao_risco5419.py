"""
Teste de integração de ponta a ponta do módulo de risco NBR 5419-2: sobe o
app FastAPI completo e refaz, via HTTP, o mesmo caso de referência de
`app/risco5419/tests/test_motor.py` (TestRiscosCasoResolvido) — projeto,
análise (NG manual), estrutura, zona, linha com trecho, medidas de
proteção, cálculo e exportação do memorial em .docx.

Depende de `httpx` (só para o TestClient — ver requirements-dev.txt).
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import criar_app  # noqa: E402


class TestFluxoCompletoRisco5419(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="pe_desktop_risco5419_")
        app = criar_app(pasta_dados=Path(self._tmp))
        self.client = TestClient(app)

    def test_fluxo_analise_completa_bate_com_caso_de_referencia(self):
        c = self.client

        projeto = c.post("/api/projetos", json={
            "numero_projeto": "2026-01-0003", "nome_projeto": "Galpao de testes",
        }).json()
        pid = projeto["id"]

        analise = c.post(f"/api/projetos/{pid}/risco5419/analises", json={
            "tag": "EST-01", "ng_modo": "manual", "ng_valor_manual": 10, "ng_fonte_manual": "teste",
        }).json()
        aid = analise["id"]
        self.assertEqual(analise["ng_valor"], 10)
        self.assertEqual(analise["ng_modo"], "manual")

        estrutura = c.put(f"/api/projetos/{pid}/risco5419/analises/{aid}/estrutura", json={
            "comprimento_m": 20, "largura_m": 10, "altura_m": 6,
            "fator_localizacao": "isolada", "tipo_construcao": "robusta_metalica_concreto_armado",
            "localizacao": "Rua Teste, 123", "risco_explosao": False,
            "falha_sistema_interno_risco_vida": False, "sistema_critico": False,
            "num_pessoas_total": 50,
        }).json()
        self.assertEqual(estrutura["comprimento_m"], 20)

        zona = c.post(f"/api/projetos/{pid}/risco5419/analises/{aid}/zonas", json={
            "nome": "Zona única", "num_pessoas_zona": 50, "tempo_pessoas_horas_ano": 8760,
            "tipo_piso": "terra_concreto", "providencias_incendio": "nenhuma_ou_risco_explosao",
            "risco_incendio": "incendio_normal", "perigo_especial": "sem_perigo_especial",
            "categoria_dano_fisico_lf": "outros", "categoria_falha_sistema_lo": "outras_partes_hospital",
        }).json()
        self.assertEqual(zona["nome"], "Zona única")

        linha = c.post(f"/api/projetos/{pid}/risco5419/analises/{aid}/linhas", json={
            "tag": "L1", "tipo": "energia", "tem_transformador_at_bt": False, "tensao_suportavel_kv": 1.5,
            "trechos": [{
                "comprimento_m": 500, "tipo_instalacao": "aereo", "ambiente": "rural",
                "categoria_blindagem": "aerea_nao_blindada_sem_ligacao",
                "categoria_pld": "nao_blindada_ou_blindagem_nao_interligada",
            }],
        }).json()
        self.assertEqual(len(linha["trechos"]), 1)

        medidas = c.put(f"/api/projetos/{pid}/risco5419/analises/{aid}/medidas-protecao", json={
            "classe_spda": "spda_np_ii", "medidas_pta": ["avisos_de_alerta"],
            "dps_coordenado": "nenhum_sistema_coordenado_dps", "dps_classe_i": "sem_dps_classe_i",
            "medida_ptu": "nenhuma_medida", "fiacao_interna": "blindado_ou_em_conduto_metalico",
            "tensao_suportavel_sistema_interno_kv": 1.5,
        }).json()
        self.assertEqual(medidas["medidas_pta"], ["avisos_de_alerta"])

        resultado = c.post(f"/api/projetos/{pid}/risco5419/analises/{aid}/calcular").json()
        # Mesmos valores de referência de TestRiscosCasoResolvido (test_motor.py)
        self.assertAlmostEqual(resultado["r1"], 4.012638e-5, delta=4.012638e-5 * 1e-4)
        self.assertFalse(resultado["r1_atende"])
        self.assertIsNone(resultado["r3"])
        self.assertAlmostEqual(resultado["f_total"], 12.424128, delta=1e-3)

        memoria = c.get(f"/api/projetos/{pid}/risco5419/analises/{aid}/memoria-calculo").json()
        self.assertTrue(memoria["passos"])

        pendencias = c.get(f"/api/projetos/{pid}/risco5419/analises/{aid}/pendencias-exportacao").json()
        self.assertEqual(pendencias, [])

        resp_docx = c.get(f"/api/projetos/{pid}/risco5419/analises/{aid}/exportar-docx")
        self.assertEqual(resp_docx.status_code, 200)
        self.assertTrue(resp_docx.content.startswith(b"PK"), "memorial exportado não parece um .docx válido")

    def test_ng_por_municipio_usa_tabela_semeada_do_anexo_f(self):
        c = self.client
        ufs = c.get("/api/risco5419/ng/ufs").json()
        self.assertTrue(ufs, "tabela de municípios (Anexo F) deveria vir semeada do CSV")

        municipios = c.get(f"/api/risco5419/ng/municipios?uf={ufs[0]}").json()
        self.assertTrue(municipios)

        projeto = c.post("/api/projetos", json={
            "numero_projeto": "2026-01-0004", "nome_projeto": "Projeto NG por municipio",
        }).json()
        analise = c.post(f"/api/projetos/{projeto['id']}/risco5419/analises", json={
            "tag": "EST-02", "ng_modo": "municipio",
            "ng_municipio": municipios[0]["municipio"], "ng_uf": municipios[0]["uf"],
        }).json()
        self.assertEqual(analise["ng_modo"], "municipio")
        self.assertAlmostEqual(analise["ng_valor"], municipios[0]["ng"])


if __name__ == "__main__":
    unittest.main()
