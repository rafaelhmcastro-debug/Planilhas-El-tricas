"""
Migração simples de esquema para SQLite: se a tabela existente não tiver
exatamente as colunas do modelo (ou tiver restrições NOT NULL diferentes),
a tabela é recriada e os dados das colunas em comum são copiados.
"""
from sqlalchemy import inspect, text

from .database import Base


def _divergente(insp, tabela):
    cols_db = {c["name"]: c for c in insp.get_columns(tabela.name)}
    cols_modelo = {c.name: c for c in tabela.columns}
    if set(cols_db) != set(cols_modelo):
        return True
    return not all(
        bool(cols_db[n]["nullable"]) == bool(cols_modelo[n].nullable) or cols_modelo[n].primary_key
        for n in cols_db if n in cols_modelo
    )


def _adicionar_colunas_faltantes(engine, insp, tabelas):
    """No PostgreSQL, colunas novas opcionais (nullable, sem chave/índice) podem ser
    adicionadas com ALTER TABLE ADD COLUMN sem recriar a tabela. Isso cobre o caso comum
    de um campo novo no modelo que ainda não existe no banco de produção."""
    with engine.begin() as conn:
        for tabela in tabelas:
            cols_db = {c["name"] for c in insp.get_columns(tabela.name)}
            for coluna in tabela.columns:
                if coluna.name in cols_db or not coluna.nullable or coluna.primary_key:
                    continue
                tipo = coluna.type.compile(dialect=engine.dialect)
                print(f"Adicionando coluna ausente: {tabela.name}.{coluna.name} ({tipo})")
                conn.execute(text(f'ALTER TABLE "{tabela.name}" ADD COLUMN "{coluna.name}" {tipo}'))


def migrate(engine):
    insp = inspect(engine)
    existentes = set(insp.get_table_names())
    tabelas_existentes = [t for t in Base.metadata.sorted_tables if t.name in existentes]

    # No PostgreSQL, tenta primeiro o caminho aditivo (ADD COLUMN) antes de só avisar.
    if engine.dialect.name != "sqlite":
        _adicionar_colunas_faltantes(engine, insp, tabelas_existentes)
        insp = inspect(engine)

    divergentes = [t for t in tabelas_existentes if _divergente(insp, t)]
    if not divergentes:
        return

    # Recriar a tabela só é seguro no SQLite, onde índices e constraints acompanham
    # o RENAME. No PostgreSQL eles ficam no schema e colidem ao recriar a tabela.
    if engine.dialect.name != "sqlite":
        nomes = ", ".join(t.name for t in divergentes)
        print(f"AVISO: esquema divergente do modelo em: {nomes}.")
        print("Ajuste essas tabelas manualmente — a recriação automática só roda em SQLite.")
        return

    with engine.begin() as conn:
        for tabela in divergentes:
            nome = tabela.name
            cols_db = {c["name"]: c for c in insp.get_columns(nome)}
            cols_modelo = {c.name: c for c in tabela.columns}
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
