"""
Resolução da pasta de dados local e conexão com o banco (ADR 0001 §6).

Pasta de dados padrão: %LOCALAPPDATA%\\<NOME_PROGRAMA>\\ no Windows. Como o
usuário pode escolher outra pasta nas Configurações (requisito 2), e esse
"onde está minha pasta de dados" não pode morar dentro da própria pasta que
ele aponta, o ponteiro fica num arquivo fixo e pequeno em
%APPDATA%\\<NOME_PROGRAMA>\\config.json — local que nunca muda.

Fora do Windows (dev/teste neste repositório), cai para ~/.config e
~/.local/share, só para o pacote funcionar nos testes; em produção (Windows
10/11) sempre usa LOCALAPPDATA/APPDATA.

NOME_PROGRAMA = "Calc 54" (nome oficial confirmado pelo engenheiro em
2026-11-03). Tem espaço de propósito — o programa precisa funcionar em
caminhos com espaço/acento de qualquer forma (requisito não funcional), e
é o mesmo nome usado na janela e no instalador.
"""
import json
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

NOME_PROGRAMA = "Calc 54"
NOME_ARQUIVO_BANCO = "dados.db"


def _base_appdata() -> Path:
    return Path(os.getenv("APPDATA") or os.path.expanduser("~/.config"))


def _base_localappdata() -> Path:
    return Path(os.getenv("LOCALAPPDATA") or os.path.expanduser("~/.local/share"))


def caminho_config() -> Path:
    """Arquivo-ponteiro fixo: guarda só onde está a pasta de dados atual."""
    return _base_appdata() / NOME_PROGRAMA / "config.json"


def pasta_dados_padrao() -> Path:
    return _base_localappdata() / NOME_PROGRAMA


def resolver_pasta_dados() -> Path:
    """Lê o ponteiro de config.json; se ainda não existir (primeira execução),
    cria apontando para a pasta padrão. Garante que a pasta exista no disco."""
    cfg_path = caminho_config()
    if cfg_path.exists():
        dados = json.loads(cfg_path.read_text(encoding="utf-8"))
        pasta = Path(dados["pasta_dados"])
    else:
        pasta = pasta_dados_padrao()
        definir_pasta_dados(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def definir_pasta_dados(pasta: Path) -> None:
    """Atualiza o ponteiro para uma nova pasta de dados. NÃO move dados
    existentes — mover/copiar o banco (se houver) é responsabilidade de quem
    chama (ex.: a tela de Configurações), antes de apontar para cá."""
    cfg_path = caminho_config()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps({"pasta_dados": str(pasta)}, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(pasta).mkdir(parents=True, exist_ok=True)


def caminho_banco(pasta_dados: Path | None = None) -> Path:
    pasta = pasta_dados if pasta_dados is not None else resolver_pasta_dados()
    return Path(pasta) / NOME_ARQUIVO_BANCO


def caminho_logs(pasta_dados: Path | None = None) -> Path:
    pasta = pasta_dados if pasta_dados is not None else resolver_pasta_dados()
    d = Path(pasta) / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def criar_engine(pasta_dados: Path | None = None, *, echo: bool = False):
    caminho = caminho_banco(pasta_dados)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{caminho}"
    # check_same_thread=False: o pywebview roda a UI numa thread e o servidor
    # local noutra; a sessão do SQLAlchemy já serializa o acesso por request.
    return create_engine(url, connect_args={"check_same_thread": False}, echo=echo)


def criar_fabrica_sessao(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Sessão global usada pelos routers do FastAPI (desktop_shell/main.py chama
# `inicializar()` uma vez na subida do app; os testes de unidade/integração
# continuam usando `criar_engine`/`criar_fabrica_sessao` direto, sem passar
# por aqui).
# ---------------------------------------------------------------------------
_engine = None
_Sessao = None
_pasta_dados_ativa: Path | None = None


def inicializar(pasta_dados: Path | None = None):
    """Cria o engine/fábrica de sessão globais a partir da pasta de dados
    (resolvida automaticamente se `pasta_dados` não for informado). Guarda a
    pasta efetivamente usada em `_pasta_dados_ativa` — rotas como as de
    `routers/sistema.py` devem ler `pasta_dados_ativa()`, não chamar
    `resolver_pasta_dados()` de novo, porque isso ignoraria um `pasta_dados`
    explícito (o caso dos testes de integração, que usam uma pasta
    temporária em vez da pasta real do sistema)."""
    global _engine, _Sessao, _pasta_dados_ativa
    _pasta_dados_ativa = pasta_dados if pasta_dados is not None else resolver_pasta_dados()
    _engine = criar_engine(_pasta_dados_ativa)
    _Sessao = criar_fabrica_sessao(_engine)
    return _engine


def pasta_dados_ativa() -> Path:
    """Pasta de dados que o app FastAPI está efetivamente usando nesta
    execução. Chama `inicializar()` (com a pasta padrão) se ainda não tiver
    sido chamada — mesma rede de segurança de `get_db()`."""
    if _pasta_dados_ativa is None:
        inicializar()
    return _pasta_dados_ativa


def get_db():
    """Dependency do FastAPI — mesmo formato de `cabos-app/app/database.py`."""
    if _Sessao is None:
        inicializar()
    db = _Sessao()
    try:
        yield db
    finally:
        db.close()
