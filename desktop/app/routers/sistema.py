"""
Endpoints exclusivos do app desktop (não existem no app web, que não precisa
deles: lá o banco mora no servidor, nunca no computador de quem usa):
pasta de dados, backup e restauração (requisitos 2 e 4).

A troca de pasta de dados é feita arquivo a arquivo (copia o banco atual para
a nova pasta, só então atualiza o ponteiro) e exige reiniciar o programa —
de propósito: trocar o engine do SQLAlchemy em tempo de execução, com
conexões abertas, é um risco real de corrupção que não se paga pelo ganho de
não reiniciar. O ponteiro só muda depois da cópia ter sido confirmada, então
uma falha no meio do caminho nunca deixa o programa "perdido" — a pasta
antiga continua sendo a vigente até a cópia terminar com sucesso.
"""
import datetime
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from sqlalchemy.orm import Session

from .. import backup, database
from ..database import get_db

router = APIRouter(prefix="/api/sistema", tags=["sistema"])


@router.get("/info")
def info(db: Session = Depends(get_db)):
    pasta = database.pasta_dados_ativa()
    return {
        "pasta_dados": str(pasta),
        "caminho_banco": str(database.caminho_banco(pasta)),
        "pasta_dados_padrao": str(database.pasta_dados_padrao()),
    }


@router.get("/backup.zip")
def criar_backup_download(db: Session = Depends(get_db)):
    pasta = database.pasta_dados_ativa()
    caminho_banco = database.caminho_banco(pasta)
    with tempfile.TemporaryDirectory() as tmp:
        destino = Path(tmp) / "backup.zip"
        backup.criar_backup(caminho_banco, destino)
        conteudo = destino.read_bytes()
    nome = f"backup_calc54_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return Response(
        content=conteudo, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.post("/restaurar")
async def restaurar_backup_upload(arquivo: UploadFile = File(...)):
    pasta = database.pasta_dados_ativa()
    caminho_banco = database.caminho_banco(pasta)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_zip = Path(tmp) / "enviado.zip"
        tmp_zip.write_bytes(await arquivo.read())
        try:
            copia_seguranca = backup.restaurar_backup(tmp_zip, caminho_banco)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return {
        "ok": True,
        "copia_seguranca_do_banco_anterior": str(copia_seguranca) if copia_seguranca else None,
        "aviso": "Reinicie o programa para carregar os dados restaurados.",
    }


@router.post("/pasta-dados")
def definir_nova_pasta(payload: dict):
    nova_pasta = payload.get("pasta")
    if not nova_pasta:
        raise HTTPException(400, "Informe o caminho da nova pasta em 'pasta'.")
    nova_pasta = Path(nova_pasta)
    pasta_atual = database.pasta_dados_ativa()
    if nova_pasta.resolve() == pasta_atual.resolve():
        raise HTTPException(400, "A pasta escolhida já é a pasta de dados atual.")

    nova_pasta.mkdir(parents=True, exist_ok=True)
    caminho_atual = database.caminho_banco(pasta_atual)
    if caminho_atual.exists():
        shutil.copy2(caminho_atual, nova_pasta / database.NOME_ARQUIVO_BANCO)
    database.definir_pasta_dados(nova_pasta)
    return {
        "ok": True,
        "pasta_dados": str(nova_pasta),
        "aviso": "Reinicie o programa para usar a nova pasta de dados. "
                 "Os dados antigos continuam intactos na pasta anterior.",
    }
