"""
Importa a tabela de densidade de descargas atmosféricas NG por município
(Anexo F da NBR 5419-2) para o banco de dados.

Uso:
    python scripts/importar_ng_municipios.py caminho/arquivo.csv "Referência da fonte"

O CSV deve ter as colunas (separador ";"): codigo_ibge;municipio;uf;ng
codigo_ibge pode vir vazio. Linhas com UF inválida, NG não numérico ou
duplicidade de (município, UF) dentro do próprio arquivo são rejeitadas e
listadas no relatório final — nunca estimadas ou ignoradas silenciosamente.

Municípios já existentes (mesmo município+UF) são atualizados (upsert);
novos são inseridos. Isso preserva o histórico de análises já emitidas,
que guardam um snapshot do NG usado (ver AnaliseRisco em app/risco5419/modelos.py)
e não são afetadas por uma reimportação posterior da base.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, engine, Base
from app import models  # noqa: F401 (registra Projeto no Base — exigido pela relationship de AnaliseRisco)
from app.risco5419.modelos import MunicipioNG
from app.risco5419.ng import importar_csv


def main(caminho_csv: str, referencia: str):
    Base.metadata.create_all(bind=engine, tables=[MunicipioNG.__table__])
    db = SessionLocal()
    try:
        resumo = importar_csv(db, caminho_csv, referencia)
    finally:
        db.close()

    print(f"Importação concluída: {resumo['inseridos']} inseridos, "
          f"{resumo['atualizados']} atualizados, {len(resumo['rejeitados'])} rejeitados.")
    if resumo["rejeitados"]:
        print("\nLinhas rejeitadas:")
        for r in resumo["rejeitados"]:
            print(f"  linha {r['linha']}: {r['dados']} -> {r['motivo']}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Uso: python scripts/importar_ng_municipios.py caminho/arquivo.csv "Referência da fonte"')
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
