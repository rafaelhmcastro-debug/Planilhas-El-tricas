# Proveniência dos dados de seed

Todos os arquivos `.json` desta pasta foram **extraídos programaticamente** do
seeder real do app web (`cabos-app/app/seed_data.py`, rodado contra um SQLite
em memória), não retypados à mão — elimina risco de erro de transcrição.
Script de extração: ver `decisions-and-spec-corrections.md` na raiz do
repositório, decisões D4/D5 (2026-11-03): o engenheiro responsável confirmou
usar esses valores como estão, sem esperar confirmação adicional de datasheet
real da Prysmian nem de edição específica da NBR 5410.

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `tab_capacidade_conducao.json` | 528 | NBR 5410, tabelas 36–39 (PVC 70°C e EPR/XLPE 90°C, cobre) |
| `tab_fator_temperatura.json` | 26 | NBR 5410, tabela 40 |
| `tab_fator_agrupamento.json` | 12 | NBR 5410, tabela 42 |
| `tab_resistividade_condutor.json` | 18 | Resistência do condutor por seção |
| `tab_limite_ocupacao_eletroduto.json` | 3 | 1 cabo=53%, 2 cabos=31%, 3+=40% (regra 10a) |
| `tab_limite_ocupacao_bandeja.json` | 1 | Critério de disposição (regra 10b) |
| `catalogo_infraestrutura_eletrica.json` | 47 | Catálogo Elecon 2018 (eletrodutos, perfilados, eletrocalhas, leitos) |
| `catalogo_cabos.json` | 208 | Catálogo de cabos Prysmian — **valores de referência, não extraídos de datasheet real** (ver D4) |

Mesma observação do `seed_data.py` original continua válida: antes de usar em
projeto real, os valores de `catalogo_cabos.json` devem ser substituídos pelos
datasheets reais da Prysmian quando disponíveis (campo `fonte_datasheet` de
cada item já indica isso). O catálogo de infraestrutura (Elecon 2018) é a
referência oficial confirmada no requisito do projeto.

`app/seed.py` carrega estes arquivos no banco local na primeira execução do
programa (equivalente ao `seed_if_empty()` do app web, mas lendo de arquivo em
vez de literais Python inline).
