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
import time
from pathlib import Path

DESKTOP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DESKTOP_DIR))

import uvicorn  # noqa: E402
import webview  # noqa: E402

from app import database  # noqa: E402
from desktop_shell.bridge import Bridge  # noqa: E402

STATIC_DIR = database.pasta_recursos_empacotados() / "static"


def _instalar_log_rotativo(pasta_dados) -> None:
    """Log de erros com rotação (requisito 7): só exceção + stack trace +
    timestamp, nunca corpo de requisição nem dado de projeto.

    Chamado DEPOIS de `criar_app()` (migrações/seed) ter terminado, de
    propósito: `app/migrations/env.py` chama `logging.config.fileConfig()`
    (boilerplate padrão do Alembic) para formatar a saída de `alembic
    upgrade`, e isso ADICIONA um handler do `alembic.ini` ao logger raiz (um
    `StreamHandler` para stderr — invisível no executável empacotado, que
    roda sem console). Chama-se `raiz.handlers.clear()` antes de adicionar o
    nosso para que ele seja o ÚNICO handler do processo a partir daqui — sem
    isso, o handler do alembic continuava recebendo (e duplicando) tudo que
    o resto do app loga depois. Seguro chamar mais de uma vez (idempotente:
    sempre limpa antes de adicionar) — é o que acontece no caminho de erro,
    que tenta instalar de novo antes de registrar a falha."""
    pasta_logs = database.caminho_logs(pasta_dados)
    arquivo = pasta_logs / "calc54.log"
    handler = logging.handlers.RotatingFileHandler(
        arquivo, maxBytes=2_000_000, backupCount=5, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.handlers.clear()
    raiz.addHandler(handler)


def _porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _ServidorNaoSubiu(RuntimeError):
    pass


def _aguardar_servidor(porta: int, thread: threading.Thread, erro: dict, timeout_s: float = 30.0) -> None:
    """Espera o uvicorn começar a aceitar conexões antes de abrir a janela —
    sem isso, a janela abre numa tela de erro de conexão na maioria das
    vezes, porque o servidor ainda está rodando migrações/seed nesse
    instante. Detecta também o caso da thread do servidor ter morrido antes
    disso (ex.: falha na migração) — sem essa checagem, o programa ficava
    preso aqui até o timeout e só então abria uma janela fadada a não
    conectar nunca, sem indicar o motivo real."""
    prazo = time.monotonic() + timeout_s
    while time.monotonic() < prazo:
        if not thread.is_alive():
            raise _ServidorNaoSubiu(erro.get("exc") or "o servidor encerrou antes de começar a responder.")
        try:
            with socket.create_connection(("127.0.0.1", porta), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise _ServidorNaoSubiu(f"o servidor não respondeu em {timeout_s:.0f} s.")


def _subir_servidor(porta: int, pasta_dados, erro: dict) -> None:
    try:
        from app.main import criar_app

        app = criar_app(pasta_dados=pasta_dados, static_dir=STATIC_DIR)
        config = uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="info", log_config=None)
        servidor = uvicorn.Server(config)
        servidor.run()
    except Exception as e:  # repassado para a thread principal via `erro` — ver _aguardar_servidor
        erro["exc"] = e
        raise


def main() -> None:
    pasta_dados = database.resolver_pasta_dados()
    try:
        porta = _porta_livre()
        erro: dict = {}
        thread = threading.Thread(target=_subir_servidor, args=(porta, pasta_dados, erro), daemon=True)
        thread.start()
        _aguardar_servidor(porta, thread, erro)
        _instalar_log_rotativo(pasta_dados)

        # Requisito 3 (download de relatórios): o pywebview CANCELA qualquer
        # download silenciosamente por padrão (ALLOW_DOWNLOADS=False em ambos
        # os backends, WebView2 e GTK — confirmado lendo
        # webview/platforms/edgechromium.py e gtk.py) — sem essa linha,
        # clicar em "Baixar Excel"/"Baixar Word"/backup.zip não dá erro
        # nenhum, simplesmente não faz nada. Precisa ser setado antes de
        # create_window/start.
        webview.settings["ALLOW_DOWNLOADS"] = True

        webview.create_window(
            "Calc 54", f"http://127.0.0.1:{porta}/", js_api=Bridge(),
            width=1280, height=800, min_size=(900, 600),
        )
        webview.start()
    except Exception:
        # Antes de instalar o log rotativo (ex.: erro na migração/seed) não
        # há pasta de dados/arquivo garantidos ainda; tenta instalar aqui
        # também, best-effort, para a falha ficar registrada de qualquer jeito.
        try:
            _instalar_log_rotativo(pasta_dados)
        except Exception:
            pass
        logging.getLogger(__name__).exception("Falha ao iniciar o Calc 54.")
        raise


if __name__ == "__main__":
    main()
