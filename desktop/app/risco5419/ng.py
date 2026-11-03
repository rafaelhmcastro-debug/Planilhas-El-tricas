"""
Resolução da densidade de descargas atmosféricas NG (1/km²·ano) para uma análise
de risco: Modo A (valor informado manualmente) ou Modo B (por município, Anexo F
da NBR 5419-2). Funções puras de consulta/validação — quem persiste o snapshot
é o chamador (router), conforme A.1.3 da norma: os valores de NG devem ser
exclusivamente os do Anexo F, exceto quando o próprio usuário assume a
responsabilidade de informar um valor manual com justificativa.
"""
import csv
import unicodedata
from datetime import datetime

from sqlalchemy.orm import Session

from .modelos import MunicipioNG

UFS_VALIDAS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


def importar_csv(db: Session, caminho_csv: str, referencia: str) -> dict:
    """Importa/atualiza municipios_ng a partir de um CSV (codigo_ibge;municipio;uf;ng).

    Faz upsert por (município, UF). Linhas com UF inválida, NG não numérico,
    município vazio ou duplicadas dentro do próprio arquivo são rejeitadas e
    reportadas, nunca estimadas. Retorna um resumo {inseridos, atualizados, rejeitados}.
    """
    linhas_validas = []
    rejeitados = []
    vistos = set()

    with open(caminho_csv, encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f, delimiter=";")
        colunas_esperadas = {"codigo_ibge", "municipio", "uf", "ng"}
        if not colunas_esperadas.issubset(set(leitor.fieldnames or [])):
            raise ValueError(
                f"Cabeçalho do CSV deve conter as colunas {sorted(colunas_esperadas)}; "
                f"encontrado: {leitor.fieldnames}"
            )

        for numero, linha in enumerate(leitor, start=2):
            municipio = (linha.get("municipio") or "").strip()
            uf = (linha.get("uf") or "").strip().upper()
            ng_bruto = (linha.get("ng") or "").strip()
            codigo_ibge = (linha.get("codigo_ibge") or "").strip() or None

            motivo = None
            if not municipio:
                motivo = "município vazio"
            elif uf not in UFS_VALIDAS:
                motivo = f"UF inválida: '{uf}'"
            else:
                try:
                    valor_ng = float(ng_bruto.replace(",", "."))
                    if valor_ng < 0:
                        motivo = f"NG negativo: '{ng_bruto}'"
                except ValueError:
                    motivo = f"NG não numérico: '{ng_bruto}'"

            if motivo:
                rejeitados.append({"linha": numero, "dados": linha, "motivo": motivo})
                continue

            chave = (municipio, uf)
            if chave in vistos:
                rejeitados.append({"linha": numero, "dados": linha, "motivo": f"duplicado no arquivo: {municipio}/{uf}"})
                continue
            vistos.add(chave)
            linhas_validas.append({"codigo_ibge": codigo_ibge, "municipio": municipio, "uf": uf, "ng": valor_ng})

    inseridos, atualizados = 0, 0
    agora = datetime.utcnow()
    for dados in linhas_validas:
        existente = (
            db.query(MunicipioNG)
            .filter(MunicipioNG.municipio == dados["municipio"], MunicipioNG.uf == dados["uf"])
            .first()
        )
        if existente:
            existente.ng = dados["ng"]
            existente.codigo_ibge = dados["codigo_ibge"]
            existente.referencia = referencia
            existente.importado_em = agora
            atualizados += 1
        else:
            db.add(MunicipioNG(
                codigo_ibge=dados["codigo_ibge"], municipio=dados["municipio"], uf=dados["uf"],
                ng=dados["ng"], referencia=referencia, importado_em=agora,
            ))
            inseridos += 1
    db.commit()
    return {"inseridos": inseridos, "atualizados": atualizados, "rejeitados": rejeitados}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return texto.strip().lower()


def listar_ufs(db: Session) -> list[str]:
    linhas = db.query(MunicipioNG.uf).distinct().order_by(MunicipioNG.uf).all()
    return [uf for (uf,) in linhas]


def buscar_municipios(db: Session, uf: str, q: str = "", limit: int = 20) -> list[MunicipioNG]:
    query = db.query(MunicipioNG).filter(MunicipioNG.uf == uf.upper())
    candidatos = query.order_by(MunicipioNG.municipio).all()
    if not q:
        return candidatos[:limit]
    alvo = _normalizar(q)
    filtrados = [m for m in candidatos if alvo in _normalizar(m.municipio)]
    return filtrados[:limit]


def resolver_ng_manual(valor: float, fonte: str | None) -> dict:
    if valor is None or valor <= 0:
        raise ValueError("NG informado manualmente deve ser um valor maior que zero.")
    fonte = (fonte or "").strip()
    referencia = f"informado pelo usuário{f'; fonte: {fonte}' if fonte else ''}"
    return {
        "ng_modo": "manual",
        "ng_valor": valor,
        "ng_municipio": None,
        "ng_uf": None,
        "ng_fonte_justificativa": fonte or None,
        "ng_referencia": referencia,
    }


def resolver_ng_municipio(db: Session, municipio: str, uf: str) -> dict:
    registro = (
        db.query(MunicipioNG)
        .filter(MunicipioNG.uf == uf.upper(), MunicipioNG.municipio == municipio)
        .first()
    )
    if not registro:
        raise ValueError(
            f'Município "{municipio}/{uf}" não encontrado na tabela de NG (Anexo F). '
            "Verifique o nome exato ou use o Modo A (valor manual)."
        )
    return {
        "ng_modo": "municipio",
        "ng_valor": registro.ng,
        "ng_municipio": registro.municipio,
        "ng_uf": registro.uf,
        "ng_fonte_justificativa": None,
        "ng_referencia": f"município {registro.municipio}/{registro.uf}, {registro.referencia}",
    }
