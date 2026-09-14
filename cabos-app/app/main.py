import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base, SessionLocal
from . import models  # noqa: F401 -- garante que os modelos sejam registrados
from .migrate import migrate
from .seed_data import seed_if_empty
from .routers import projetos, equipamentos, infraestrutura, cabos, paineis, catalogos, relatorios

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

migrate(engine)
Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_if_empty(db)

app = FastAPI(title="Sistema de Cálculo de Cabos, Eletrodutos, Bandejas e Demanda")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.include_router(projetos.router)
app.include_router(equipamentos.router)
app.include_router(infraestrutura.router)
app.include_router(cabos.router)
app.include_router(paineis.router)
app.include_router(catalogos.router)
app.include_router(relatorios.router)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
