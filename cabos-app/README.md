# Sistema de Cálculo de Cabos, Eletrodutos, Bandejas e Demanda

Aplicação web (FastAPI + SQLite + HTML/JS puro) para dimensionamento elétrico
de projetos industriais: cadastro de projetos, equipamentos, painéis (com
hierarquia até o TOP), eletrodutos/bandejas e cabos, com dimensionamento
automático conforme NBR 5410, ocupação de infraestrutura, cargas/demanda e
exportação de relatórios em Excel.

## Como rodar (Windows)

Dê dois cliques em `iniciar.bat` — ele instala as dependências, sobe o servidor
e abre o navegador em http://localhost:8000.

Ou, manualmente:

```bash
cd cabos-app
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

O banco (`cabos.db`) é criado automaticamente; ao atualizar o programa, o
esquema do banco é migrado preservando os dados já cadastrados.

## Como o cálculo funciona (resumo para o engenheiro)

**Equipamento**
- Potência informada em kW, W, CV, HP (potência nominal/no eixo) ou kVA (aparente absorvida).
- P elétrica = Pn / η (rendimento). S = P / cos φ. Q = √(S² − P²).
- In = S / (√3 × V) para trifásico; In = S / V para monofásico (F-N) e bifásico (F-F).
- Pd = P × FD (fator de demanda).
- Fases (1, 2 ou 3) + neutro + terra definem o nº de vias do cabo.

**Painéis / transformadores**
- Cada equipamento aponta para o painel que o alimenta (TAG). Cada painel pode
  apontar para o painel a montante ("Alimentado por"); o painel sem alimentador é o TOP.
- Demanda do painel = (Σ Pd dos equipamentos diretos + Σ demanda dos painéis a jusante) × fator de diversidade.
  Q é somado da mesma forma; S = √(P² + Q²); cos φ = P/S; I = S / (√3 × V).

**Cabos**
- A carga do cabo é a ponta "Para" (equipamento ou painel). Ib = I da carga / nº de cabos em paralelo.
- Seção por capacidade: tabela NBR 5410 (isolação × método A1…G × nº de condutores carregados) ×
  fator de temperatura (temperatura informada) × fator de agrupamento (nº de circuitos no trecho ou valor manual) ≥ Ib.
- Seção por queda de tensão: ΔV% = k × Ib × L × (R cos φ + X sen φ) / V × 100 (k = √3 trifásico, 2 mono/bifásico).
- Seção sugerida = maior das duas. Até 35 mm² → cabo multipolar; a partir de 50 mm² → cabos singelos.
- O usuário pode trocar o cabo do catálogo; se a seção for menor que a sugerida, o sistema alerta sem bloquear.
- A memória de cálculo mostra cada passo com a fórmula e os números substituídos.

**Eletrodutos / bandejas**
- Eletroduto: ocupação = Σ áreas dos cabos físicos / área útil; limite 53 % (1 cabo), 31 % (2), 40 % (3+).
- Eletrocalha/perfilado/leito: ocupação = Σ diâmetros / largura útil (camada única).
- O sistema sugere o menor item do catálogo que atende.

## Catálogos e tabelas normativas

Os catálogos de cabos (Prysmian) e infraestrutura (Elecon) vêm pré-carregados
com **valores de referência** para o sistema funcionar de ponta a ponta — não
substituem os datasheets oficiais. As tabelas de capacidade de condução
reproduzem as tabelas 36 a 39 da NBR 5410 e devem ser conferidas com a edição
vigente. Na tela **Configurações/Normas** é possível:

- cadastrar cabos manualmente (todos os campos: vias, seção, Ø externo, R, X, peso…);
- baixar a planilha-modelo e importar catálogos/tabelas por Excel;
- cadastrar eletrocalhas com dimensão customizada.

## Estrutura

- `app/models.py` — modelo de dados (SQLAlchemy).
- `app/calculations.py` — motor de cálculo (equipamentos, painéis, cabos, ocupação, memória).
- `app/seed_data.py` — carga inicial (NBR 5410 e catálogos).
- `app/migrate.py` — migração automática do esquema do banco.
- `app/routers/` — API REST; `app/excel_export.py` — relatórios `.xlsx`.
- `static/` — interface web (sem build).
