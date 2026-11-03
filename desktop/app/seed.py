"""
Carga inicial das tabelas normativas e dos catálogos a partir dos arquivos
`seed/*.json` (ver `seed/README.md` para a proveniência de cada um) — mesma
ideia de `cabos-app/app/seed_data.py`, mas lendo de arquivo de dados em vez de
literais Python inline, seguindo o padrão já consolidado em
`cabos-app/app/risco5419/dados/*.json`.
"""
import json
from pathlib import Path

from sqlalchemy.orm import Session

from . import models

SEED_DIR = Path(__file__).parent / "seed"

_TABELAS = [
    ("tab_capacidade_conducao", models.TabCapacidadeConducao),
    ("tab_fator_temperatura", models.TabFatorTemperatura),
    ("tab_fator_agrupamento", models.TabFatorAgrupamento),
    ("tab_resistividade_condutor", models.TabResistividadeCondutor),
    ("tab_limite_ocupacao_eletroduto", models.TabLimiteOcupacaoEletroduto),
    ("tab_limite_ocupacao_bandeja", models.TabLimiteOcupacaoBandeja),
    ("catalogo_infraestrutura_eletrica", models.CatalogoInfraestrutura),
    ("catalogo_cabos", models.CatalogoCabo),
]


def _carregar_arquivo(nome: str) -> list[dict]:
    caminho = SEED_DIR / f"{nome}.json"
    if not caminho.exists():
        raise FileNotFoundError(f'Arquivo de seed "{caminho}" não existe.')
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def seed_if_empty(db: Session) -> None:
    """Semeia cada tabela normativa/catálogo só se ela ainda estiver vazia —
    nunca sobrescreve dados que o usuário já tenha (ex.: depois de uma
    importação própria pela tela de Configurações)."""
    for nome, modelo in _TABELAS:
        if db.query(modelo).count() > 0:
            continue
        linhas = _carregar_arquivo(nome)
        for linha in linhas:
            db.add(modelo(**linha))
    db.commit()
