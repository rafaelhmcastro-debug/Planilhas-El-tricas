"""
Casca desktop: sobe o backend FastAPI (mesmo app de `app/main.py`) num
servidor uvicorn local, escutando só em 127.0.0.1 numa porta livre escolhida
dinamicamente (requisito "sem chamada de rede" / risco 9 da ADR — nunca
0.0.0.0, nunca porta fixa), e abre uma janela pywebview apontando para esse
endereço. O frontend é o `static/` atual, servido pelo próprio FastAPI.

Ponto de entrada do executável empacotado (Fase 5): `python -m desktop_shell.main`.
"""
import logging
import logging.handlers
import socket
import sys
import threading
from pathlib import Path

DESKTOP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DESKTOP_DIR))

import uvicorn  # noqa: E402
import webview  # noqa: E402

from app import database  # noqa: E402
from desktop_shell.bridge import Bridge  # noqa: E402

STATIC_DIR = DESKTOP_DIR / "static"


def _configurar_logging(pasta_dados) -> None:
    """Log de erros com rotação (requisito 7): só exceção + stack trace +
    timestamp, nunca corpo de requisição nem dado de projeto."""
    pasta_logs = database.caminho_logs(pasta_dados)
    arquivo = pasta_logs / "calc54.log"
    handler = logging.handlers.RotatingFileHandler(
        arquivo, maxBytes=2_000_000, backupCount=5, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.addHandler(handler)


def _porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _aguardar_servidor(porta: int, timeout_s: float = 15.0) -> None:
    """Espera o uvicorn começar a aceitar conexões antes de abrir a janela —
    sem isso, a janela abre numa tela de erro de conexão na maioria das
    vezes, porque o servidor ainda está rodando migrações/seed nesse instante."""
    import time

    prazo = time.monotonic() + timeout_s
    while time.monotonic() < prazo:
        try:
            with socket.create_connection(("127.0.0.1", porta), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)


def _subir_servidor(porta: int, pasta_dados) -> None:
    from app.main import criar_app

    app = criar_app(pasta_dados=pasta_dados, static_dir=STATIC_DIR)
    config = uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="info", log_config=None)
    servidor = uvicorn.Server(config)
    servidor.run()


def main() -> None:
    pasta_dados = database.resolver_pasta_dados()
    _configurar_logging(pasta_dados)
    try:
        porta = _porta_livre()
        thread = threading.Thread(target=_subir_servidor, args=(porta, pasta_dados), daemon=True)
        thread.start()
        _aguardar_servidor(porta)

        webview.create_window(
            "Calc 54", f"http://127.0.0.1:{porta}/", js_api=Bridge(),
            width=1280, height=800, min_size=(900, 600),
        )
        webview.start()
    except Exception:
        logging.getLogger(__name__).exception("Falha ao iniciar o Calc 54.")
        raise


if __name__ == "__main__":
    main()
