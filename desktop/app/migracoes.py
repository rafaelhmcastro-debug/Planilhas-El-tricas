"""
Aplica as migrações do Alembic programaticamente (API do Alembic, não a CLI)
— é assim que o app empacotado atualiza o esquema do banco local ao iniciar,
sem depender de o executável `alembic` estar disponível no PATH do usuário.

Requisito 3: migrações versionadas, nunca apagando dados do usuário em
silêncio. O Alembic, por natureza, só roda as migrações pendentes (registradas
em `alembic_version`) — uma migração que precisar remover dados teria que
fazer isso explicitamente dentro do próprio script de migração, o que este
módulo não faz por conta própria.
"""
from pathlib import Path

from alembic import command
from alembic.config import Config

DESKTOP_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = DESKTOP_DIR / "alembic.ini"
MIGRATIONS_DIR = DESKTOP_DIR / "app" / "migrations"


def _config(db_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def aplicar_migracoes(caminho_banco: Path) -> None:
    """Cria o banco do zero já na revisão mais recente (primeira execução) ou
    aplica só as migrações pendentes (execuções seguintes) — o Alembic decide
    isso sozinho a partir da tabela `alembic_version`."""
    url = f"sqlite:///{caminho_banco}"
    command.upgrade(_config(url), "head")


def revisao_atual(caminho_banco: Path) -> str | None:
    """Útil para diagnóstico/log: qual revisão o banco está, ou None se o
    banco ainda não tem a tabela alembic_version (nunca migrado)."""
    import sqlite3

    if not Path(caminho_banco).exists():
        return None
    conn = sqlite3.connect(str(caminho_banco))
    try:
        cur = conn.execute("SELECT version_num FROM alembic_version")
        row = cur.fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None  # tabela alembic_version não existe ainda
    finally:
        conn.close()
