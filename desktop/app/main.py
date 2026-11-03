"""
App FastAPI do porte desktop (Fase 3). Portado de `cabos-app/app/main.py`,
removendo login/administração (`routers/auth.py`, `routers/admin.py` — decisão
de produto confirmada em 2026-11-03: app de usuário único) e o módulo de
risco NBR 5419-2 (`routers/risco5419.py` — entra só depois da Fase 5, como já
definido).

Duas diferenças deliberadas do app web, pelo requisito de app 100% offline
(ADR 0001 §3):
- CORS restrito a `127.0.0.1`/`localhost` (o app web usa `allow_origins=["*"]`,
  aceitável só porque é servido por HTTPS num host fixo).
- Sem seed de município (NG) nem usuário admin padrão — não existem aqui.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from . import database, migracoes, models, seed  # noqa: F401
from .routers import projetos, equipamentos, infraestrutura, cabos, paineis, catalogos, relatorios, sistema


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

    if static_dir:
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
