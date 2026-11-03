# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller --onedir (ADR 0001 §3: onedir em vez de onefile — inicialização
mais rápida, sem extrair para %TEMP% a cada execução, menor taxa de falso
positivo de antivírus/SmartScreen).

Build (Windows, com o venv do projeto ativado, a partir de `desktop/`):
    pyinstaller packaging/pyinstaller.spec --noconfirm

Gera `dist/Calc 54/Calc 54.exe` + a pasta `_internal/` ao lado (dados
empacotados: `static/`, `app/migrations/`, `app/seed/*.json`, `alembic.ini`
— ver `app/database.pasta_recursos_empacotados()`, que lê `sys._MEIPASS`
para achar esses arquivos no executável empacotado).
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
    icon=None,  # TODO Fase 5: ícone próprio do Calc 54, se/quando o engenheiro fornecer um
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
