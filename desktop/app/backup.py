"""
Backup e restauração do banco local em arquivo `.zip` (requisito 4).

Escopo atual: só o banco (`dados.db`), sem pasta de anexos — decisão D3
(decisions-and-spec-corrections.md, 2026-11-03): o programa não armazena
nenhum arquivo de usuário hoje (folha de dados/diagrama elétrico continuam
campo-texto). Se um ponto de anexo real surgir depois, este módulo precisa
ser revisto para incluir a pasta de anexos no `.zip`.

Usa a API de backup do próprio SQLite (`sqlite3.Connection.backup`), não uma
cópia de arquivo bruta — evita inconsistência se o banco estiver em modo WAL
(que mantém dados ainda não gravados em arquivos `-wal`/`-shm` à parte; uma
cópia de arquivo ingênua perderia essas escritas).
"""
import datetime
import json
import sqlite3
import zipfile
from pathlib import Path

NOME_BANCO_NO_ZIP = "dados.db"
NOME_METADADOS_NO_ZIP = "backup_info.json"


def criar_backup(caminho_banco: Path, destino_zip: Path) -> Path:
    """Cria um `.zip` com uma cópia consistente do banco atual. Não altera o
    banco original nem fecha conexões existentes."""
    destino_zip = Path(destino_zip)
    destino_zip.parent.mkdir(parents=True, exist_ok=True)

    origem = sqlite3.connect(str(caminho_banco))
    try:
        copia = sqlite3.connect(":memory:")
        try:
            origem.backup(copia)
            with zipfile.ZipFile(destino_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                # Serializa a cópia em memória de volta para bytes de arquivo SQLite.
                conteudo = copia.serialize() if hasattr(copia, "serialize") else None
                if conteudo is None:
                    # Python < 3.11 não tem Connection.serialize(); usa um arquivo
                    # temporário como ponte.
                    tmp = destino_zip.with_suffix(".tmp.db")
                    tmp_conn = sqlite3.connect(str(tmp))
                    copia.backup(tmp_conn)
                    tmp_conn.close()
                    zf.write(tmp, NOME_BANCO_NO_ZIP)
                    tmp.unlink()
                else:
                    zf.writestr(NOME_BANCO_NO_ZIP, bytes(conteudo))
                metadados = {
                    "criado_em": datetime.datetime.now().isoformat(timespec="seconds"),
                    "origem": str(caminho_banco),
                }
                zf.writestr(NOME_METADADOS_NO_ZIP, json.dumps(metadados, ensure_ascii=False, indent=2))
        finally:
            copia.close()
    finally:
        origem.close()
    return destino_zip


def validar_backup(origem_zip: Path) -> dict:
    """Confere que o `.zip` tem um banco SQLite válido dentro, sem restaurar
    nada. Levanta `ValueError` com uma mensagem clara se não tiver."""
    origem_zip = Path(origem_zip)
    with zipfile.ZipFile(origem_zip) as zf:
        nomes = zf.namelist()
        if NOME_BANCO_NO_ZIP not in nomes:
            raise ValueError(f'O arquivo "{origem_zip.name}" não contém "{NOME_BANCO_NO_ZIP}" — não parece ser um backup deste programa.')
        dados_banco = zf.read(NOME_BANCO_NO_ZIP)
        metadados = {}
        if NOME_METADADOS_NO_ZIP in nomes:
            metadados = json.loads(zf.read(NOME_METADADOS_NO_ZIP))

    if not dados_banco.startswith(b"SQLite format 3\x00"):
        raise ValueError(f'O arquivo "{NOME_BANCO_NO_ZIP}" dentro do backup não é um banco SQLite válido.')
    return metadados


def restaurar_backup(origem_zip: Path, caminho_banco: Path) -> Path:
    """Restaura o banco a partir de um `.zip` de backup, SUBSTITUINDO o banco
    atual — mas nunca apaga o banco atual sem guardar uma cópia antes
    (requisito: nunca apagar dados do usuário silenciosamente). Devolve o
    caminho da cópia de segurança do banco anterior (ou None se não havia
    banco anterior)."""
    validar_backup(origem_zip)  # levanta ValueError cedo, antes de mexer em qualquer arquivo
    caminho_banco = Path(caminho_banco)
    caminho_banco.parent.mkdir(parents=True, exist_ok=True)

    copia_seguranca = None
    if caminho_banco.exists():
        agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        copia_seguranca = caminho_banco.with_name(f"{caminho_banco.stem}.antes_de_restaurar_{agora}{caminho_banco.suffix}")
        caminho_banco.replace(copia_seguranca)

    with zipfile.ZipFile(origem_zip) as zf:
        with zf.open(NOME_BANCO_NO_ZIP) as origem, open(caminho_banco, "wb") as destino:
            destino.write(origem.read())

    return copia_seguranca
