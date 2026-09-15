"""
Migração simples de esquema para SQLite: se a tabela existente não tiver
exatamente as colunas do modelo (ou tiver restrições NOT NULL diferentes),
a tabela é recriada e os dados das colunas em comum são copiados.
"""
from sqlalchemy import inspect, text

from .database import Base


def migrate(engine):
    insp = inspect(engine)
    existentes = set(insp.get_table_names())

    # Detectar se é SQLite ou PostgreSQL
    is_sqlite = engine.dialect.name == "sqlite"

    with engine.begin() as conn:
        # PRAGMA é apenas para SQLite
        if is_sqlite:
            conn.execute(text("PRAGMA foreign_keys=OFF"))

        for tabela in Base.metadata.sorted_tables:
            nome = tabela.name
            if nome not in existentes:
                continue
            cols_db = {c["name"]: c for c in insp.get_columns(nome)}
            cols_modelo = {c.name: c for c in tabela.columns}
            mesmas_colunas = set(cols_db) == set(cols_modelo)
            mesma_nulabilidade = all(
                bool(cols_db[n]["nullable"]) == bool(cols_modelo[n].nullable) or cols_modelo[n].primary_key
                for n in cols_db if n in cols_modelo
            )
            if mesmas_colunas and mesma_nulabilidade:
                continue

            destino = [n for n in cols_modelo if n in cols_db]
            origem = [f'"{n}"' for n in destino]
            # colunas renomeadas entre versões: (coluna nova, expressão SQL sobre a tabela antiga, colunas antigas exigidas)
            for nova, expr, exigidas in RENOMEADAS.get(nome, []):
                if nova in cols_modelo and nova not in cols_db and all(e in cols_db for e in exigidas):
                    destino.append(nova)
                    origem.append(expr)
            temp = f"{nome}__old"
            conn.execute(text(f'DROP TABLE IF EXISTS "{temp}"'))
            conn.execute(text(f'ALTER TABLE "{nome}" RENAME TO "{temp}"'))
            tabela.create(conn)
            if destino:
                conn.execute(text(
                    f'INSERT INTO "{nome}" ({", ".join(chr(34) + c + chr(34) for c in destino)}) '
                    f'SELECT {", ".join(origem)} FROM "{temp}"'
                ))
            conn.execute(text(f'DROP TABLE "{temp}"'))
            _pos_migracao(conn, nome)

        # PRAGMA é apenas para SQLite
        if is_sqlite:
            conn.execute(text("PRAGMA foreign_keys=ON"))


RENOMEADAS = {
    "equipamentos": [
        ("potencia_valor", "COALESCE(potencia_ativa_kw, potencia_aparente_kva)", ["potencia_ativa_kw", "potencia_aparente_kva"]),
        ("potencia_unidade", "CASE WHEN potencia_ativa_kw IS NULL AND potencia_aparente_kva IS NOT NULL THEN 'kVA' ELSE 'kW' END",
         ["potencia_ativa_kw", "potencia_aparente_kva"]),
    ],
}


def _pos_migracao(conn, nome):
    """Valores padrão para colunas novas."""
    if nome == "equipamentos":
        conn.execute(text("UPDATE equipamentos SET potencia_unidade='kW' WHERE potencia_unidade IS NULL"))
        conn.execute(text("UPDATE equipamentos SET rendimento=1.0 WHERE rendimento IS NULL"))
        conn.execute(text("UPDATE equipamentos SET possui_neutro=0 WHERE possui_neutro IS NULL"))
        conn.execute(text("UPDATE equipamentos SET possui_terra=1 WHERE possui_terra IS NULL"))
    if nome == "paineis_transformadores":
        conn.execute(text("UPDATE paineis_transformadores SET num_fases=3 WHERE num_fases IS NULL"))
        conn.execute(text("UPDATE paineis_transformadores SET painel_alimentador_tag='' WHERE painel_alimentador_tag IS NULL"))
    if nome == "cabos":
        conn.execute(text("UPDATE cabos SET temperatura_ambiente_c=30 WHERE temperatura_ambiente_c IS NULL"))
