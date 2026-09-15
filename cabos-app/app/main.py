import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base, SessionLocal
from . import models  # noqa: F401
from . import models_auth  # noqa: F401
from .migrate import migrate
from .seed_data import seed_if_empty
from .routers import projetos, equipamentos, infraestrutura, cabos, paineis, catalogos, relatorios, auth, admin
from .utils_auth import obter_usuario_por_username, criar_usuario

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _criar_admin_padrao(db):
    admin_existente = obter_usuario_por_username(db, "admin")
    if admin_existente:
        return

    print("Criando usuário admin padrão...")
    criar_usuario(
        db=db,
        username="admin",
        email="admin@example.com",
        empresa="Administração",
        senha="admin123",
        role="admin",
        ativo=True,
        aprovado=True
    )
    print("✓ Usuário admin criado com sucesso")
    print("  Username: admin")
    print("  Senha: admin123")
    print("  ⚠️ IMPORTANTE: Mude a senha após o primeiro login!")


migrate(engine)
Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_if_empty(db)
    _criar_admin_padrao(db)

app = FastAPI(title="Sistema de Cálculo de Cabos, Eletrodutos, Bandejas e Demanda")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)

app.include_router(projetos.router)
app.include_router(equipamentos.router)
app.include_router(infraestrutura.router)
app.include_router(cabos.router)
app.include_router(paineis.router)
app.include_router(catalogos.router)
app.include_router(relatorios.router)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
