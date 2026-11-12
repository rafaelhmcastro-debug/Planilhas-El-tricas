# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller --onedir (ADR 0001 §3: onedir em vez de onefile — inicialização
mais rápida, sem extrair para %TEMP% a cada execução, menor taxa de falso
positivo de antivírus/SmartScreen).

Build (Windows, com o venv do projeto ativado, a partir de `desktop/`):
    pyinstaller packaging/pyinstaller.spec --noconfirm

Gera `dist/Calc 54/Calc 54.exe` + a pasta `_internal/` ao lado (dados
empacotados: `static/`, `app/migrations/`, `app/seed/*.json`, `alembic.ini`,
`app/risco5419/dados/*` e `app/risco5419/templates/*.docx` — ver
`app/database.pasta_recursos_empacotados()`, que lê `sys._MEIPASS` para
achar esses arquivos no executável empacotado).
"""
from pathlib import Path

DESKTOP_DIR = Path(SPECPATH).parent  # noqa: F821 — SPECPATH é a pasta do .spec (packaging/); desktop/ é a pasta acima

a = Analysis(
    [str(DESKTOP_DIR / "desktop_shell" / "main.py")],
    pathex=[str(DESKTOP_DIR)],
    binaries=[],
    datas=[
        (str(DESKTOP_DIR / "static"), "static"),
        (str(DESKTOP_DIR / "app" / "migrations"), "app/migrations"),
        (str(DESKTOP_DIR / "app" / "seed"), "app/seed"),
        (str(DESKTOP_DIR / "alembic.ini"), "."),
        (str(DESKTOP_DIR / "app" / "risco5419" / "dados"), "app/risco5419/dados"),
        (str(DESKTOP_DIR / "app" / "risco5419" / "templates"), "app/risco5419/templates"),
    ],
    hiddenimports=[
        # uvicorn escolhe implementação de loop/protocolo em tempo de
        # execução (importlib por nome) — a análise estática do PyInstaller
        # não enxerga essas strings, então entram à mão.
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "email_validator",
        # app/migrations/env.py é carregado dinamicamente pelo Alembic
        # (lê o arquivo do disco e executa, não é um "import" normal) — a
        # análise estática do PyInstaller não enxerga os imports de DENTRO
        # dele. Hoje esse módulo acaba entrando "de carona" via outras
        # dependências do app, mas isso não é garantido (achado testando um
        # build mínimo isolado, só com o necessário pra rodar migração) —
        # declarado explicitamente para não depender de sorte.
        "logging.config",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Calc 54",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # sem janela de console — erros vão para o log com rotação (requisito 7), não para a tela
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Requisito 4 (ícone do .exe): reaproveita o logo já usado pelo próprio
    # app (favicon/cabeçalho em static/img/logo-planilhas.svg — ver
    # static/index.html), convertido para .ico multi-resolução
    # (16/32/48/256 px). O título da janela (WebView2) e a barra de tarefas
    # no Windows herdam o ícone embutido no .exe automaticamente — pywebview
    # 6.2.1 não tem um parâmetro de ícone próprio em `create_window()` para
    # sobrepor isso (conferido via `inspect.signature`).
    icon=str(DESKTOP_DIR / "packaging" / "calc54.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Calc 54",
)
