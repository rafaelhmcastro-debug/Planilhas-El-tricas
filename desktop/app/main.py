"""
App FastAPI do porte desktop. Portado de `cabos-app/app/main.py`, removendo
login/administração (`routers/auth.py`, `routers/admin.py` — decisão de
produto confirmada em 2026-11-03: app de usuário único).

O módulo de risco NBR 5419-2 (`risco5419/`, `routers/risco5419.py`) entrou
depois das Fases 1-5, como definido desde o início do porte.

Duas diferenças deliberadas do app web, pelo requisito de app 100% offline
(ADR 0001 §3):
- CORS restrito a `127.0.0.1`/`localhost` (o app web usa `allow_origins=["*"]`,
  aceitável só porque é servido por HTTPS num host fixo).
- Sem usuário admin padrão — não existe aqui (login removido).
"""
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from . import database, migracoes, models, seed  # noqa: F401
from .risco5419 import modelos as models_risco5419  # noqa: F401
from .risco5419 import ng
from .risco5419.modelos import MunicipioNG
from .routers import projetos, equipamentos, infraestrutura, cabos, paineis, catalogos, relatorios, sistema, risco5419

NG_MUNICIPIOS_CSV = database.pasta_recursos_empacotados() / "app" / "risco5419" / "dados" / "municipios_ng_anexo_f.csv"
NG_MUNICIPIOS_REFERENCIA = "Projeto de Revisão ABNT NBR 5419-2, JUL/2025, Anexo F, Tabela F.1"


def _seed_municipios_ng(db):
    if db.query(MunicipioNG).count() > 0:
        return
    if not os.path.exists(NG_MUNICIPIOS_CSV):
        return
    ng.importar_csv(db, str(NG_MUNICIPIOS_CSV), NG_MUNICIPIOS_REFERENCIA)


def criar_app(pasta_dados=None, static_dir=None) -> FastAPI:
    """Monta o app FastAPI contra uma pasta de dados já resolvida (ou a
    pasta padrão, se `pasta_dados` for None). Separado em função para os
    testes de integração poderem apontar para uma pasta temporária."""
    engine = database.inicializar(pasta_dados)
    caminho_banco = database.caminho_banco(pasta_dados)
    migracoes.aplicar_migracoes(caminho_banco)

    Sessao = database.criar_fabrica_sessao(engine)
    with Sessao() as db:
        seed.seed_if_empty(db)
        _seed_municipios_ng(db)

    app = FastAPI(title="Calc 54")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1", "http://localhost"],
        allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+",
        allow_methods=["*"], allow_headers=["*"],
    )

    app.include_router(projetos.router)
    app.include_router(equipamentos.router)
    app.include_router(infraestrutura.router)
    app.include_router(cabos.router)
    app.include_router(paineis.router)
    app.include_router(catalogos.router)
    app.include_router(relatorios.router)
    app.include_router(sistema.router)
    app.include_router(risco5419.router)

    if static_dir:
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
