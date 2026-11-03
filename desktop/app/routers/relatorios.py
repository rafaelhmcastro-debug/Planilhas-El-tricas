from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import models, excel_export
from ..database import get_db

router = APIRouter(prefix="/api/projetos/{projeto_id}/relatorios", tags=["relatorios"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _get_projeto(db, projeto_id):
    projeto = db.get(models.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")
    return projeto


def _xlsx_response(conteudo: bytes, nome_arquivo: str):
    return Response(
        content=conteudo, media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@router.get("/equipamentos.xlsx")
def relatorio_equipamentos(projeto_id: int, db: Session = Depends(get_db)):
    projeto = _get_projeto(db, projeto_id)
    return _xlsx_response(excel_export.exportar_equipamentos(db, projeto), f"Lista_Equipamentos_{projeto.numero_projeto}.xlsx")


@router.get("/cabos.xlsx")
def relatorio_cabos(projeto_id: int, db: Session = Depends(get_db)):
    projeto = _get_projeto(db, projeto_id)
    return _xlsx_response(excel_export.exportar_cabos(db, projeto), f"Lista_Cabos_{projeto.numero_projeto}.xlsx")


@router.get("/infraestrutura.xlsx")
def relatorio_infraestrutura(projeto_id: int, db: Session = Depends(get_db)):
    projeto = _get_projeto(db, projeto_id)
    return _xlsx_response(excel_export.exportar_infraestrutura(db, projeto), f"Lista_Eletrodutos_Bandejas_{projeto.numero_projeto}.xlsx")


@router.get("/cargas-demanda.xlsx")
def relatorio_cargas_demanda(projeto_id: int, db: Session = Depends(get_db)):
    projeto = _get_projeto(db, projeto_id)
    return _xlsx_response(excel_export.exportar_cargas_demanda(db, projeto), f"Cargas_Demanda_{projeto.numero_projeto}.xlsx")


@router.get("/memoria-calculo.xlsx")
def relatorio_memoria(projeto_id: int, cabo_id: int = None, db: Session = Depends(get_db)):
    projeto = _get_projeto(db, projeto_id)
    return _xlsx_response(excel_export.exportar_memoria_calculo(db, projeto, cabo_id), f"Memoria_Calculo_{projeto.numero_projeto}.xlsx")
