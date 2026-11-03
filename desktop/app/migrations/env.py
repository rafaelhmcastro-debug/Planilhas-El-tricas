import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Garante que "app" seja importável independente de onde o alembic for
# chamado (CLI local ou empacotado via PyInstaller).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import models  # noqa: E402
from app.database import caminho_banco  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = models.Base.metadata

# URL do banco: por padrão, resolve a pasta de dados local real (mesma lógica
# que o app usa em tempo de execução — %LOCALAPPDATA%\<Programa>\dados.db no
# Windows). Testes/empacotamento podem sobrescrever via `-x db_url=sqlite:///...`
# (ex.: alembic -x db_url=sqlite:////caminho/de/teste.db upgrade head).
x_args = context.get_x_argument(as_dictionary=True)
if "db_url" in x_args:
    config.set_main_option("sqlalchemy.url", x_args["db_url"])
elif not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", f"sqlite:///{caminho_banco()}")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite: ALTER TABLE é limitado, batch recria a tabela quando precisa
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            render_as_batch=True,  # SQLite: ALTER TABLE é limitado, batch recria a tabela quando precisa
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
