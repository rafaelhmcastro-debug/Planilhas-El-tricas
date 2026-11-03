# Especificação técnica — Sistema de Cálculo de Cabos, Eletrodutos, Bandejas e Demanda

## 1. Visão geral

Aplicação **web** (interface em HTML, acessível pelo navegador, uso online), para engenharia elétrica, organizada por **projetos** (cada projeto identificado por um número no formato `9999-99-9999`), com quatro módulos integrados:

1. **Equipamentos** (cargas) — cadastro de cada carga da instalação, informando o painel ou transformador que a alimenta.
2. **Cabos** — cadastro de cabos vinculados a uma carga (De/Para), com cálculo automático de corrente, seção e queda de tensão, e memória de cálculo detalhada.
3. **Eletrodutos e Bandejas** — cadastro da infraestrutura física por onde os cabos passam, usada para montar o percurso e a distância de cada cabo.
4. **Cargas e Demanda** — soma automática das cargas por painel/transformador (a partir da TAG informada em cada equipamento), com cálculo da demanda total e do alimentador.

Todo o cadastro (equipamentos, cabos, eletrodutos/bandejas, painéis) pertence a um projeto específico; o usuário escolhe ou cria o projeto ao entrar no sistema, e todas as telas trabalham dentro desse projeto ativo.

Os dados alimentam relatórios finais: lista de cabos, lista de eletrodutos/bandejas com taxa de ocupação, memória de cálculo por cabo e lista de materiais (BOM) — todos exportáveis em Excel.

## 2. Stack tecnológica sugerida

| Camada | Tecnologia |
|---|---|
| Frontend | HTML5 + CSS + JavaScript — interface web responsiva (framework leve como Vue.js ou React opcional; funciona também só com HTML/JS puro) |
| Backend | Python 3.11+ com FastAPI (API REST) |
| Banco de dados | PostgreSQL (ou SQLite para começar/ambiente pequeno) via SQLAlchemy (ORM) |
| Cálculo e tabelas normativas | pandas (tabelas NBR 5410 de capacidade de condução e fatores de correção) |
| Exportação Excel | openpyxl (backend gera o `.xlsx` e o navegador faz o download) |
| Autenticação (opcional) | login simples por usuário/senha, caso mais de uma pessoa use o sistema |
| Hospedagem | servidor web (intranet da empresa ou nuvem), acessível por navegador em qualquer computador da rede |

> Justificativa: interface web permite acesso de qualquer computador sem instalação, facilita uso simultâneo por mais de uma pessoa, e mantém os dados centralizados em um único banco.

## 3. Arquitetura de módulos (fluxo de dados)

```
Cadastro de Equipamentos ──┐
                            ├──> Cadastro de Cabos ──> Cálculo elétrico do cabo ──> Cálculo de cargas e demanda ──> Relatórios e listas
Cadastro de Eletrodutos/Bandejas ──┘
```

Dentro do cálculo elétrico do cabo:

```
Carga vinculada (De/Para) ──> Potência e corrente de projeto ──> Percurso do cabo (soma eletrodutos/bandejas) ──> Dimensionamento da seção ──> Ficha do cabo
```

## 4. Modelo de dados (tabelas do banco)

### 4.1 `projetos`
| Campo | Tipo | Observação |
|---|---|---|
| id | inteiro | |
| numero_projeto | texto (chave única) | formato obrigatório `9999-99-9999` (ex.: `2011-KS-03105`), validado por máscara/regex `^\d{4}-\d{2}-\d{4}$` |
| nome_projeto | texto | |
| cliente | texto | opcional |
| descricao | texto | opcional |
| revisao | texto | ex.: "Rev. 0" |
| data_criacao | data | preenchida automaticamente |

> Todas as tabelas abaixo (equipamentos, eletrodutos/bandejas, cabos, painéis) possuem um campo `projeto_id` (FK → `projetos`), de forma que os dados de projetos diferentes fiquem completamente isolados entre si. O `catalogo_cabos` (4.7), o `catalogo_infraestrutura_eletrica` (4.8) e as tabelas normativas (4.9) são globais, compartilhadas por todos os projetos.

### 4.2 `equipamentos`
| Campo | Tipo | Observação |
|---|---|---|
| projeto_id | FK → projetos | |
| tag | texto (único dentro do projeto) | |
| descricao | texto | |
| tipo_carga | texto/enum | motor, iluminação, tomada, climatização, etc. |
| potencia_ativa_kw | decimal | opcional se informar aparente |
| potencia_aparente_kva | decimal | opcional se informar ativa |
| tensao_v | decimal | |
| num_fases | inteiro | 1 ou 3 |
| fator_potencia | decimal | 0–1 |
| fator_demanda | decimal | 0–1 |
| painel_transformador_tag | texto | **TAG do painel/quadro ou transformador que alimenta este equipamento** — usado para somar automaticamente as cargas na planilha de cargas e demanda (ver 4.6 e regra 11) |
| dimensoes | texto/JSON | comprimento x largura x altura |
| peso_kg | decimal | |
| folha_dados_path | texto | caminho do arquivo anexado |
| diagrama_eletrico_path | texto | caminho do arquivo anexado |
| fornecedor | texto | |
| observacao | texto | |
| *(calculado)* corrente_nominal_a | decimal | gerado, não editável |
| *(calculado)* potencia_demanda_kw | decimal | gerado, não editável |

### 4.3 `eletrodutos_bandejas`
| Campo | Tipo | Observação |
|---|---|---|
| projeto_id | FK → projetos | |
| tag | texto (único dentro do projeto) | |
| tipo | enum | eletroduto, eletrocalha, perfilado, leito |
| catalogo_infraestrutura_id | FK → catalogo_infraestrutura_eletrica | item do catálogo Elecon efetivamente escolhido (ver 4.8) — de onde vêm diâmetro/dimensão nominal, parede e área útil |
| no_origem | texto | |
| no_destino | texto | |
| comprimento_m | decimal | |
| dimensao_definida_manualmente | booleano | `false` = dimensão sugerida pelo cálculo (regra 10); `true` = usuário escolheu manualmente outro item do catálogo |
| *(herdado do catálogo)* diametro_nominal_mm | decimal | eletrodutos |
| *(herdado do catálogo)* parede_mm | decimal | espessura de parede do eletroduto |
| *(herdado do catálogo)* area_util_mm2 | decimal | área interna útil (eletrodutos), calculada a partir do diâmetro interno do catálogo |
| *(herdado do catálogo)* largura_util_mm | decimal | largura útil (eletrocalhas, perfilados e leitos) |
| *(calculado)* dimensao_sugerida_id | FK → catalogo_infraestrutura_eletrica | item do catálogo que atenderia à ocupação mínima necessária para os cabos hoje atribuídos a este trecho (ver regra 10) |

> Nomenclatura: o termo genérico "bandeja", usado no restante deste documento (título, regras, telas), cobre os três produtos do catálogo Elecon usados como leito de cabos: **eletrocalha** (perfurada ou lisa), **perfilado** e **leito** propriamente dito. O campo `tipo` guarda a categoria específica do catálogo; a regra de ocupação (10b) é a mesma para os três.

### 4.4 `cabos`
| Campo | Tipo | Observação |
|---|---|---|
| projeto_id | FK → projetos | |
| tag | texto (único dentro do projeto) | |
| equipamento_de_id | FK → equipamentos | |
| equipamento_para_id | FK → equipamentos | |
| tipo_isolacao | enum | PVC, EPR, XLPE, HEPR |
| metodo_instalacao | texto | conforme tabela NBR 5410 |
| queda_tensao_admissivel_pct | decimal | padrão 3% ou 5% |
| num_cabos_paralelo | inteiro | |
| catalogo_cabo_id | FK → catalogo_cabos | cabo comercial efetivamente escolhido (ver 4.7) |
| secao_definida_manualmente | booleano | `false` = seção sugerida pelo cálculo; `true` = usuário sobrescreveu a escolha |
| observacao | texto | |
| *(auto)* tensao_v | decimal | herdada do equipamento |
| *(calculado)* corrente_projeto_a | decimal | |
| *(calculado)* secao_sugerida_mm2 | decimal | resultado do dimensionamento automático (seção 5) |
| *(editável pelo usuário)* secao_mm2 | decimal | seção adotada final — pré-preenchida com `secao_sugerida_mm2`, mas o usuário pode selecionar outro cabo do catálogo (item 4.7) e sobrescrever |
| *(calculado)* queda_tensao_calc_pct | decimal | recalculada para o cabo efetivamente escolhido |
| *(calculado)* distancia_total_m | decimal | soma dos trechos |
| *(calculado)* diametro_externo_mm | decimal | herdado de `catalogo_cabos`, conforme o cabo escolhido |
| *(calculado)* area_secao_transversal_mm2 | decimal | `π × (diametro_externo_mm / 2)²`, usada no cálculo de ocupação de eletrodutos/bandejas |
| *(calculado)* memoria_calculo_json | texto/JSON | registro estruturado de todos os passos e valores intermediários do dimensionamento (ver regra 12, seção 5), usado para montar a memória de cálculo na tela e na exportação |

> Fluxo de escolha do cabo: o sistema calcula a seção mínima necessária (`secao_sugerida_mm2`) e pré-seleciona, no catálogo, o cabo comercial mais próximo que atenda a essa seção, a tensão de isolamento e o tipo de isolação exigidos. O usuário pode aceitar essa sugestão ou trocar manualmente por qualquer outro cabo do catálogo (`catalogo_cabo_id`). Se a seção do cabo escolhido manualmente for **menor** que `secao_sugerida_mm2`, o sistema marca `secao_definida_manualmente = true` e exibe um alerta (não bloqueante) informando que a escolha não atende ao dimensionamento calculado — mas permite prosseguir, pois pode haver justificativa técnica do engenheiro.

### 4.5 `cabo_trechos` (tabela associativa, define o percurso)
| Campo | Tipo | Observação |
|---|---|---|
| cabo_id | FK → cabos | |
| eletroduto_bandeja_id | FK → eletrodutos_bandejas | |
| ordem | inteiro | ordem do trecho no percurso |

### 4.6 `paineis_transformadores`
| Campo | Tipo | Observação |
|---|---|---|
| projeto_id | FK → projetos | |
| tag | texto (único dentro do projeto) | deve corresponder ao texto digitado em `equipamentos.painel_transformador_tag` |
| tipo | enum | painel, quadro, transformador, CCM |
| tensao_v | decimal | tensão nominal do painel/transformador, usada no cálculo da corrente do alimentador (regra 11) |
| fator_diversidade | decimal | |
| *(calculado)* demanda_total_kw | decimal | soma automática, ver regra 11 |
| *(calculado)* corrente_total_a | decimal | |

> A soma das cargas para a planilha de cargas e demanda **não depende de o usuário selecionar equipamentos manualmente**: basta informar a TAG do painel/transformador em cada equipamento (`equipamentos.painel_transformador_tag`). O sistema agrupa automaticamente todos os equipamentos com a mesma TAG e soma suas potências de demanda. Se a TAG digitada ainda não existir em `paineis_transformadores`, o sistema cria o registro automaticamente (com fator de diversidade padrão editável depois) ou avisa o usuário para cadastrá-lo.

### 4.7 `catalogo_cabos` (catálogo de cabos comerciais, somente leitura/importável, global — compartilhado entre projetos)

Tabela alimentada a partir das folhas de dados (datasheets) dos fabricantes — no seu caso, os PDFs da Prysmian já levantados (Multiplex, Afumex Green 1kV, Afumex Green 750V, Sintenax CTL Flex e Sintenax CTL BFC Flex). É essa tabela que fornece o **diâmetro externo** usado para calcular a área do cabo e, por consequência, a taxa de ocupação de eletrodutos e bandejas.

| Campo | Tipo | Observação |
|---|---|---|
| id | inteiro | |
| fabricante | texto | ex.: Prysmian |
| linha_produto | texto | ex.: Multiplex, Afumex Green 1kV, Afumex Green 750V, Sintenax CTL Flex, Sintenax CTL BFC Flex |
| aplicacao | enum | energia BT aérea, energia BT, controle, controle blindado |
| material_condutor | enum | cobre, alumínio |
| tipo_isolacao | enum | XLPE, PE, HEPR, PVC, polímero não halogenado |
| possui_blindagem | booleano | ex.: `true` para Sintenax CTL BFC Flex (blindagem em fita de cobre) |
| tensao_isolamento | texto | ex.: "0,6/1 kV", "450/750 V" |
| construcao_basica | texto | ex.: "3x1x35+70", "4 x 2.5", "12 x 1.0" (como consta no datasheet) |
| num_condutores | inteiro | |
| secao_nominal_mm2 | decimal | |
| diametro_externo_nominal_mm | decimal | **usado para calcular a área do cabo** |
| peso_kg_km | decimal | |
| resistencia_condutor_20c_ohm_km | decimal | usada no cálculo de queda de tensão |
| capacidade_conducao_a | decimal (opcional) | quando informada pelo fabricante (ex.: tabela do Multiplex); senão, usar `tab_capacidade_conducao_*` |
| norma_referencia | texto | ex.: NBR 8182, NBR 13248, NBR 7289 |
| fonte_datasheet | texto | nome do arquivo PDF de origem, para rastreabilidade |
| *(calculado)* area_secao_mm2 | decimal | `π × (diametro_externo_nominal_mm / 2)²` |

**Importação:** como os datasheets são PDFs, a rotina de importação deve converter cada tabela "Dados construtivos" em linhas desta tabela (uma linha por combinação de nº de condutores × seção). Isso pode ser feito uma única vez por uma planilha auxiliar de conversão (semelhante ao `tabela_de_cabo.xlsx` já usado pela equipe) e depois carregado no banco; a tela de Configurações deve permitir reimportar/atualizar o catálogo quando o fabricante revisar um datasheet.

### 4.8 `catalogo_infraestrutura_eletrica` (catálogo Elecon — eletrodutos, perfilados, eletrocalhas e leitos, global — compartilhado entre projetos)

Tabela alimentada pelo [Catálogo Elecon 2018](https://elecon.com.br/wp-content/uploads/2018/08/catalogo-elecon.pdf), a referência oficial de infraestrutura de passagem de cabos do projeto. É esse catálogo (e não mais um valor digitado à mão) que fornece o **diâmetro nominal em mm**, a **parede** e a **área útil** usados na regra 10.

| Campo | Tipo | Observação |
|---|---|---|
| id | inteiro | |
| fabricante | texto | Elecon |
| linha_produto | texto | ex.: "Eletroduto Rígido Médio Eletrolítico/Pré-Zincado", "Eletroduto Rígido Pesado NBR 13057", "Eletroduto Galvanizado à Fogo", "Eletroduto Alumínio SCH-40", "Eletroduto PVC NBR 15465", "Perfilado", "Eletrocalha Perfurada", "Eletrocalha Lisa", "Leito para cabo" |
| tipo | enum | eletroduto, eletrocalha, perfilado, leito |
| diametro_nominal_pol | texto | bitola em polegadas, como consta no catálogo (ex.: `1/2"`, `3/4"`, `1"`...) — só para eletrodutos |
| diametro_nominal_mm | decimal | **DN em mm** (ex.: 15, 20, 25, 32, 40, 50, 65, 80, 100...) — só para eletrodutos |
| parede_mm | decimal | espessura de parede do eletroduto — só para eletrodutos |
| diametro_externo_mm | decimal | conforme catálogo |
| *(calculado)* diametro_interno_mm | decimal | `diametro_externo_mm − 2 × parede_mm` (eletrodutos rígidos); para o eletroduto de alumínio o catálogo já informa o diâmetro interno diretamente |
| *(calculado)* area_util_mm2 | decimal | `π × (diametro_interno_mm / 2)²` — usada na regra 10a (eletrodutos) |
| largura_nominal_mm | decimal | só para eletrocalha/perfilado/leito (ex.: perfilado 38×38, 38×19, 76×38; leito 250 ou 500 mm; eletrocalha em múltiplos de 25 mm) |
| altura_nominal_mm | decimal | idem |
| largura_util_mm | decimal | usada na regra 10b (eletrocalhas, perfilados e leitos) |
| fonte_datasheet | texto | "Catálogo Elecon 2018" |

**Exemplos de linhas** (extraídos do catálogo, para referência — a importação completa deve trazer todas as bitolas de cada linha):

| Linha | DN (mm) | Parede (mm) | Diâm. externo (mm) | Diâm. interno calc. (mm) | Área útil (mm²) |
|---|---|---|---|---|---|
| Eletroduto Médio Eletrolítico/Pré-Zincado | 15 | 0,90 | 20,40 | 18,60 | ≈272 |
| Eletroduto Médio Eletrolítico/Pré-Zincado | 25 | 0,90 | 31,90 | 30,10 | ≈712 |
| Eletroduto Médio Eletrolítico/Pré-Zincado | 50 | 0,90 | 59,00 | 57,20 | ≈2.570 |
| Eletroduto Pesado NBR 13057 | 25 | 1,50 | 31,90 | 28,90 | ≈656 |
| Eletroduto Pesado NBR 13057 | 50 | 2,25 | 59,00 | 54,50 | ≈2.333 |
| Eletroduto Galvanizado à Fogo (RIR) NBR 5597 | 25 | 2,65 | 33,70 | 28,40 | ≈634 |
| Eletroduto Alumínio SCH-40 | 25 | 3,38 | 33,40 | 26,64 (informado direto) | ≈557 |

| Linha | Dimensão (mm) | Largura útil considerada (mm) |
|---|---|---|
| Perfilado 38×19 | 38 × 19 | 38 |
| Perfilado 38×38 | 38 × 38 | 38 |
| Perfilado 76×38 | 76 × 38 | 76 |
| Leito 250 mm (aba 45×100) | 250 | 250 |
| Leito 500 mm (aba 45×100) | 500 | 500 |
| Eletrocalha (base×altura, múltiplos de 25 mm) | conforme especificado pelo usuário na compra | base informada |

**Importação:** como o catálogo é um PDF, a rotina de importação deve converter cada tabela de dimensões ("Eletrodutos", "Perfilados", "Eletrocalha" e "Leitos") em linhas desta tabela. Como a Elecon não fixa uma dimensão única para eletrocalha (é especificada por encomenda, em múltiplos de 25 mm), o sistema deve permitir também o cadastro avulso de uma eletrocalha com base/altura customizadas, mantendo o mesmo critério de cálculo da regra 10b.


### 4.9 Tabelas de referência normativa (somente leitura, pré-carregadas, globais)
- `tab_capacidade_conducao_pvc` — capacidade de condução de corrente por seção, método de instalação e nº de condutores carregados (isolação PVC).
- `tab_capacidade_conducao_epr_xlpe` — idem para EPR/XLPE.
- `tab_fator_temperatura` — fator de correção por temperatura ambiente.
- `tab_fator_agrupamento` — fator de correção por agrupamento de circuitos.
- `tab_resistividade_condutor` — resistência do condutor por seção (para cálculo de queda de tensão), conforme `tabela_de_cabo.xlsx` já usada pela equipe. Pode ser substituída pela resistência já presente em `catalogo_cabos` quando o cabo específico já estiver cadastrado no catálogo.
- `tab_limite_ocupacao_eletroduto` — taxa de ocupação máxima por nº de cabos no trecho (1 cabo = 53%, 2 cabos = 31%, 3+ cabos = 40%, conforme NBR 5410), usada na regra 10a, combinada com a `area_util_mm2` de cada item de `catalogo_infraestrutura_eletrica`.
- `tab_limite_ocupacao_bandeja` — critério de disposição de cabos em eletrocalhas/perfilados/leitos (camada única por padrão; espaçamento mínimo entre cabos quando configurado), usada na regra 10b, combinada com a `largura_util_mm` de cada item de `catalogo_infraestrutura_eletrica`.

## 5. Regras de cálculo

1. **Completar potência faltante**
   - Se só houver `potencia_ativa_kw`: `S = P / cos φ`
   - Se só houver `potencia_aparente_kva`: `P = S × cos φ`

2. **Corrente nominal do equipamento**
   - Trifásico: `In = (P × 1000) / (√3 × V × cos φ)`
   - Monofásico: `In = (P × 1000) / (V × cos φ)`
   - `P` em kW (`potencia_ativa_kw`), `V` em Volts, `In` resulta em Ampères. O fator `× 1000` converte kW para W.

3. **Potência de demanda**
   - `Pd = P × FD`

4. **Corrente de projeto do cabo (Ib)** — a corrente nominal do equipamento vinculado, **dividida** pelo nº de cabos em paralelo (quando há mais de um cabo por fase repartindo a mesma carga, cada cabo individual conduz apenas a fração correspondente da corrente total).

5. **Distância do cabo** — soma do `comprimento_m` de todos os registros em `cabo_trechos` vinculados àquele cabo, na ordem definida.

6. **Seção mínima por capacidade de condução**
   - Buscar em `tab_capacidade_conducao_*` (conforme isolação) a seção cuja capacidade, após aplicar fatores de correção (`tab_fator_temperatura` × `tab_fator_agrupamento`), seja ≥ Ib.
   - O fator de agrupamento é indexado pelo número de circuitos (cabos de outras cargas) que dividem o mesmo trecho de eletroduto/bandeja com o cabo em questão — contabilizado a partir de `cabo_trechos` para cada `eletroduto_bandeja_id` do percurso.

7. **Seção mínima por queda de tensão**
   - `ΔV% = (√3 × I × L_km × (R×cosφ + X×senφ)) / V × 100` (trifásico) — usar resistência de `tab_resistividade_condutor` (ou de `catalogo_cabos.resistencia_condutor_20c_ohm_km`, quando o cabo já estiver escolhido) conforme seção candidata; testar seções crescentes até `ΔV% ≤ queda_tensao_admissivel_pct`. `I` em Ampères, `L_km = distancia_total_m / 1000` (R/X estão em ohm/km), `V` em Volts (`tensao_v`).
   - A reatância `X` não consta nos datasheets hoje levantados; na ausência de uma tabela de reatância por seção, usar um valor típico de referência (ex.: 0,08 Ω/km para cabos em baixa tensão) ou simplificar a fórmula desprezando o termo `X×senφ` — ambas as opções devem ficar registradas na memória de cálculo (regra 12), já que mudam o resultado.

8. **Seção sugerida**
   - `secao_sugerida_mm2 = max(seção por capacidade de condução, seção por queda de tensão)`.
   - O sistema busca em `catalogo_cabos` o cabo comercial (do fabricante e tipo de isolação escolhidos) com a menor seção comercial ≥ `secao_sugerida_mm2` e o pré-seleciona em `catalogo_cabo_id`.
   - **O usuário pode substituir essa sugestão**, escolhendo manualmente qualquer outro cabo do catálogo. Nesse caso `secao_mm2` passa a refletir o cabo escolhido e `secao_definida_manualmente = true`; se a seção escolhida for menor que `secao_sugerida_mm2`, exibir alerta não bloqueante.

9. **Área da seção transversal do cabo**
   - `cabos.area_secao_transversal_mm2 = π × (diametro_externo_mm / 2)²`, onde `diametro_externo_mm` é herdado de `catalogo_cabos.diametro_externo_nominal_mm` no momento em que o cabo comercial é escolhido (sugerido ou selecionado manualmente).

10. **Ocupação e dimensão mínima de eletrodutos e bandejas** (tratamento diferenciado por tipo)

    **10a. Eletrodutos** — critério de percentual de área ocupada, conforme NBR 5410, e o limite **depende do número de cabos** no trecho (não é um valor fixo):

    | Nº de cabos no trecho | Taxa de ocupação máxima |
    |---|---|
    | 1 cabo | 53% |
    | 2 cabos | 31% |
    | 3 ou mais cabos | 40% |

    - `taxa_ocupacao = Σ cabos.area_secao_transversal_mm2 (para cada cabo do trecho, × num_cabos_paralelo) ÷ area_util_mm2` — sendo `area_util_mm2` a área interna do eletroduto **do catálogo Elecon** (calculada em 4.8 a partir do diâmetro externo e da parede daquele item).
    - Alertar se `taxa_ocupacao` ultrapassar o limite da tabela acima, buscado em `tab_limite_ocupacao_eletroduto` (indexada por nº de cabos).
    - **Dimensão sugerida:** o sistema percorre os itens de `catalogo_infraestrutura_eletrica` do tipo "eletroduto" (dentro da linha/acabamento escolhido, ex.: Médio, Pesado, Galvanizado à Fogo, Alumínio, PVC), em ordem crescente de diâmetro, e seleciona o primeiro cujo `area_util_mm2` mantenha a ocupação dentro do limite da tabela acima para os cabos hoje atribuídos ao trecho, gravando a referência em `dimensao_sugerida_id`.

    **10b. Eletrocalhas, perfilados e leitos** — critério de disposição lado a lado (cabos em camada única), não de percentual de área fechada:
    - `soma_diametros_mm = Σ cabos.diametro_externo_mm (para cada cabo do trecho, × num_cabos_paralelo)`
    - Alertar se `soma_diametros_mm` ultrapassar `largura_util_mm` do item do catálogo Elecon associado ao trecho (ou o critério de espaçamento mínimo entre cabos, se o projeto exigir feixe espaçado em vez de camada única — configurável em `tab_limite_ocupacao_bandeja`).
    - **Dimensão sugerida:** o sistema percorre os itens de `catalogo_infraestrutura_eletrica` do tipo escolhido (eletrocalha, perfilado ou leito), em ordem crescente de `largura_nominal_mm`, e seleciona o primeiro cuja `largura_util_mm` comporte `soma_diametros_mm` (mais folga de manutenção futura, se configurada), gravando a referência em `dimensao_sugerida_id`. Para eletrocalha com dimensão customizada (fora do catálogo padrão), o cálculo usa a `largura_nominal_mm` informada manualmente pelo usuário no cadastro avulso (ver 4.8).

    **Em ambos os casos:** o usuário pode manter a dimensão calculada ou escolher manualmente outra (`dimensao_definida_manualmente = true`); se a dimensão escolhida manualmente for insuficiente para a ocupação atual, exibir alerta não bloqueante — mesmo padrão já usado para a seção do cabo (regra 8). Todo o cálculo (10a/10b) deve ser refeito automaticamente sempre que um cabo for adicionado, removido ou trocado em qualquer trecho.

11. **Demanda do painel/transformador**
    - Agrupar automaticamente todos os `equipamentos` do projeto cujo campo `painel_transformador_tag` seja igual à `tag` do painel/transformador.
    - `Demanda_total = Σ Pd (equipamentos agrupados) × fator_diversidade`
    - Corrente do alimentador: mesma fórmula do item 2 (corrente nominal), substituindo `P` por `Demanda_total` e usando a tensão do painel/transformador.
    - Recalcular automaticamente sempre que um equipamento for criado, editado (mudar de `painel_transformador_tag`) ou removido.

12. **Memória de cálculo do cabo**
    - Para cada cabo, o sistema deve registrar e apresentar, em ordem, todos os passos do dimensionamento com as fórmulas e os valores substituídos (não apenas o resultado final):
      1. Dados de entrada herdados do equipamento (P/S, V, cos φ, FD).
      2. Potência complementar calculada (se aplicável), com a fórmula e os números usados.
      3. Corrente de projeto (Ib), com a fórmula e os números usados.
      4. Distância total do percurso e os trechos somados (lista de eletrodutos/bandejas com seus comprimentos).
      5. Seção mínima por capacidade de condução: tabela consultada, fatores de correção aplicados (temperatura e agrupamento) e o valor final de capacidade admissível.
      6. Seção mínima por queda de tensão: fórmula com os valores substituídos (I, L, R, X, cos φ, V) e o percentual resultante.
      7. Seção sugerida (o maior dos dois critérios) e o cabo do catálogo pré-selecionado.
      8. Cabo efetivamente escolhido (se diferente da sugestão), com o alerta correspondente, quando aplicável.
      9. Área da seção transversal do cabo escolhido e sua participação na ocupação de cada trecho percorrido.
    - Esse conteúdo é a base da tela "Memória de cálculo" (ver seção 6) e da exportação em Excel (uma aba por cabo, ou uma planilha consolidada com os passos de todos os cabos).

## 6. Telas (UI) necessárias

1. **Tela Projetos** — grade de projetos cadastrados (número, nome, cliente, revisão) + formulário de criação/edição, com o campo "Número do projeto" validado no formato `9999-99-9999`; ao abrir um projeto, ele passa a ser o "projeto ativo" e todas as demais telas trabalham somente com os dados desse projeto (indicado fixo no topo da página, com opção de trocar de projeto a qualquer momento).
2. **Tela Equipamentos** — grade (lista) + formulário lateral/modal com todos os campos da seção 4.2, incluindo o campo "Painel/Transformador (TAG)" com autocomplete sobre `paineis_transformadores` do projeto ativo (permitindo digitar uma TAG nova); upload de folha de dados e diagrama elétrico; botão "duplicar" para cadastro rápido de equipamentos semelhantes.
3. **Tela Eletrodutos/Bandejas** — grade + formulário, com o campo "Item do catálogo" (combobox pesquisável sobre `catalogo_infraestrutura_eletrica`, filtrável por tipo — eletroduto, eletrocalha, perfilado ou leito — e por linha/acabamento) preenchendo automaticamente diâmetro/dimensão, parede e área útil; visualização opcional de topologia (nós De/Para) como lista de trechos; exibir, para cada trecho, a lista de cabos que passam por ele com suas áreas/diâmetros, a taxa de ocupação (eletroduto) ou soma de diâmetros (eletrocalha/perfilado/leito) calculada em tempo real, e o **item do catálogo sugerido** — o usuário pode aceitar a sugestão ou escolher manualmente outro item do catálogo (ou cadastrar uma eletrocalha customizada), com aviso não bloqueante se a escolha for insuficiente. Tudo se atualiza automaticamente quando um cabo é adicionado, removido ou trocado em qualquer tela.
4. **Tela Cabos** — grade + formulário com:
   - Campos "De" e "Para": combobox pesquisável listando `equipamentos.tag` do projeto ativo.
   - Campo "Tensão": preenchido automaticamente e bloqueado para edição ao selecionar "De".
   - Seletor de percurso: lista ordenável (drag-and-drop ou setas para cima/baixo) para escolher e ordenar os `eletrodutos_bandejas` do trecho.
   - Botão "Calcular": dispara as regras da seção 5 e mostra corrente, seção sugerida, queda de tensão e distância total.
   - Campo "Cabo escolhido": combobox pesquisável sobre `catalogo_cabos` (filtrado por tipo de isolação/tensão compatíveis), **pré-preenchido com a sugestão do cálculo mas editável pelo usuário**. Ao trocar, os campos "diâmetro externo", "área do cabo", "peso" e "queda de tensão calculada" são recalculados imediatamente para o novo cabo. Se a seção escolhida for inferior à sugerida, mostrar um aviso (ícone/tooltip) sem bloquear o salvamento.
   - Botão/aba "Memória de cálculo": exibe na tela, passo a passo, todo o raciocínio do dimensionamento descrito na regra 12 (dados de entrada, fórmulas com os valores substituídos, seção sugerida, cabo escolhido), com opção de exportar aquele cabo individualmente em Excel.
5. **Tela Cargas e Demanda** — grade de painéis/transformadores do projeto ativo (criados automaticamente conforme as TAGs informadas nos equipamentos), cada um mostrando a lista de equipamentos agrupados automaticamente por TAG, a demanda total e a corrente do alimentador; não há seleção manual de equipamentos — apenas edição do fator de diversidade de cada painel.
6. **Tela Relatórios** — botões de exportação (todos gerando `.xlsx` para download pelo navegador), sempre referentes ao projeto ativo: Lista de Equipamentos, Lista de Cabos (no formato já usado no `PE-E-601`), Lista de Eletrodutos/Bandejas com ocupação, Planilha de Cargas e Demanda por painel/transformador, e Memória de Cálculo (uma planilha com uma aba por cabo, ou consolidada, contendo todos os passos da regra 12).
7. **Tela de Configurações/Normas** — visualização (somente leitura) das tabelas normativas, do catálogo de cabos e do catálogo de infraestrutura Elecon (eletrodutos, eletrocalhas, perfilados e leitos), todos globais e compartilhados entre projetos, com opção de importar/atualizar cada catálogo via upload de Excel.

## 7. Validações e regras de negócio

- Não permitir cadastrar um cabo sem equipamento "De" e "Para" válidos.
- Não permitir remover um equipamento referenciado por cabos existentes sem confirmação.
- Alertar se a seção calculada ultrapassar a maior seção disponível na tabela normativa ou no catálogo.
- Alertar (sem bloquear) quando o usuário escolher manualmente um cabo com seção menor que a sugerida pelo cálculo.
- Alertar se a taxa de ocupação de um eletroduto ultrapassar o limite da NBR 5410 correspondente ao nº de cabos do trecho (53%/31%/40%).
- Alertar se a soma dos diâmetros dos cabos de uma bandeja/leito ultrapassar a largura útil do trecho.
- Alertar (sem bloquear) quando o usuário escolher manualmente uma dimensão de eletroduto/bandeja menor que a sugerida pelo cálculo.
- Impedir potência ativa e aparente conflitantes (ex.: ambas informadas com cos φ incompatível) — se ambas forem informadas, validar contra o cos φ e avisar se não bater.
- Validar o número do projeto no formato `9999-99-9999`; não permitir dois projetos com o mesmo número.
- Não permitir operações em equipamentos, cabos ou eletrodutos/bandejas sem um projeto ativo selecionado.
- Ao digitar uma `painel_transformador_tag` que não exista ainda em `paineis_transformadores` do projeto, criar o registro automaticamente (fator de diversidade padrão = 1, tensão herdada do primeiro equipamento vinculado) e notificar o usuário, para que ele possa ajustar depois na tela de Cargas e Demanda.

## 8. Requisitos não funcionais

- Interface acessível via navegador (Chrome/Edge/Firefox), sem necessidade de instalar software no computador do usuário.
- Banco de dados centralizado no servidor, com rotina de backup periódico.
- Toda exportação de dados (listas e memória de cálculo) gerada em formato Excel (`.xlsx`), baixado diretamente pelo navegador.
- Importação/exportação compatível com os layouts já usados pela empresa (`PE-G-622` para equipamentos, `PE-E-601` para cabos).
- Interface em português, unidades no padrão brasileiro (vírgula decimal opcional).

---

## 9. Prompt pronto para solicitar a criação do software

Copie o bloco abaixo para pedir a construção do programa (ex.: em uma ferramenta de geração de código, ou para um desenvolvedor):

```
Crie uma aplicação web (frontend em HTML/CSS/JavaScript, backend em Python com
FastAPI, banco de dados via SQLAlchemy) para dimensionamento elétrico de projetos
industriais, organizada por PROJETOS, com os seguintes módulos:

0. PROJETOS: cadastro de projetos com número no formato obrigatório "9999-99-9999"
   (chave única, validado por máscara/regex), nome, cliente, revisão e data de
   criação. Todo o restante do sistema (equipamentos, cabos, eletrodutos/bandejas,
   painéis/transformadores) pertence a um projeto específico; o usuário escolhe ou
   cria o projeto ao entrar, e esse projeto ativo fica fixo no topo da tela, filtrando
   todos os dados exibidos e editados. O catálogo de cabos e as tabelas normativas são
   globais, compartilhados entre todos os projetos.

1. EQUIPAMENTOS: cadastro com TAG, descrição, tipo de carga, potência ativa (kW) e/ou
   aparente (kVA), tensão, nº de fases, fator de potência, fator de demanda,
   TAG DO PAINEL OU TRANSFORMADOR que alimenta o equipamento (campo texto com
   autocomplete sobre os painéis já cadastrados no projeto, permitindo digitar um novo),
   dimensões, peso, folha de dados (anexo), diagrama elétrico (anexo), fornecedor e
   observação. O sistema deve calcular automaticamente a potência que não foi
   informada (P = S×cosφ ou S = P/cosφ), a corrente nominal e a potência de demanda.

2. ELETRODUTOS E BANDEJAS: cadastro com TAG, tipo (eletroduto, eletrocalha, perfilado
   ou leito), nó de origem, nó de destino, comprimento (m), e seleção de um ITEM DO
   CATÁLOGO ELECON (item 4b, abaixo) que preenche automaticamente diâmetro nominal
   (mm), parede (mm) e área útil. O sistema deve calcular a ocupação de forma
   DIFERENTE por tipo: para ELETRODUTOS, taxa de ocupação = área dos cabos ÷ área
   útil interna (calculada a partir do diâmetro externo e da parede do item do
   catálogo Elecon), com limite que MUDA conforme o nº de cabos no trecho (1 cabo =
   53%, 2 cabos = 31%, 3 ou mais cabos = 40%, conforme NBR 5410) — não um valor fixo
   único; para ELETROCALHAS/PERFILADOS/LEITOS, o critério é a soma dos diâmetros
   externos dos cabos comparada à largura útil do item do catálogo (disposição em
   camada única). Em ambos os casos, o sistema deve SUGERIR automaticamente o menor
   item do catálogo Elecon que atenda aos cabos hoje atribuídos ao trecho, mas o
   usuário pode substituir essa sugestão por outro item do catálogo manualmente (ou
   por uma eletrocalha de dimensão customizada), com aviso não bloqueante se a
   escolha for insuficiente.

3. CABOS: cadastro com TAG, seleção do equipamento "De" e "Para" (a tensão deve ser
   preenchida automaticamente a partir do equipamento selecionado), tipo de isolação
   (PVC/EPR/XLPE/HEPR), método de instalação, queda de tensão admissível, número de
   cabos em paralelo. O usuário deve poder selecionar e ordenar os trechos de
   eletrodutos/bandejas percorridos por aquele cabo; o sistema soma automaticamente a
   distância total. O sistema deve calcular: corrente de projeto, seção mínima por
   capacidade de condução (com fatores de correção por temperatura e agrupamento,
   conforme tabelas NBR 5410), seção mínima por queda de tensão, e seção sugerida (o
   maior dos dois critérios). A partir da seção sugerida, o sistema pré-seleciona
   automaticamente um cabo comercial no catálogo (item 4a), mas o usuário deve poder
   TROCAR MANUALMENTE o cabo escolhido por qualquer outro do catálogo a qualquer
   momento; ao trocar, diâmetro externo, área do cabo, peso e queda de tensão
   recalculada devem ser atualizados imediatamente, com um aviso não bloqueante caso
   a seção escolhida seja menor que a sugerida. O sistema deve gerar e exibir, para
   cada cabo, uma MEMÓRIA DE CÁLCULO detalhada — passo a passo, com as fórmulas e os
   valores efetivamente substituídos (não só o resultado): dados de entrada, potência
   complementar calculada, corrente de projeto, percurso e distância total, seção por
   capacidade de condução com os fatores de correção aplicados, seção por queda de
   tensão, seção sugerida e cabo escolhido no catálogo.

4a. CATÁLOGO DE CABOS: base de cabos comerciais importada a partir das folhas de dados
   (datasheets) dos fabricantes, contendo, para cada seção/construção: nº de
   condutores, seção nominal (mm²), diâmetro externo nominal (mm), peso (kg/km),
   resistência do condutor a 20°C (ohm/km) e, quando disponível, capacidade de
   condução de corrente. O DIÂMETRO EXTERNO dessa tabela é usado para calcular a
   ÁREA DA SEÇÃO TRANSVERSAL de cada cabo (π × (diâmetro/2)²), que por sua vez
   alimenta o cálculo de taxa de ocupação dos eletrodutos e bandejas. Disponibilize
   uma rotina de importação (upload de planilha Excel) para carregar/atualizar esse
   catálogo sem precisar alterar o código.

4b. CATÁLOGO DE INFRAESTRUTURA (ELETRODUTOS, ELETROCALHAS, PERFILADOS E LEITOS):
   base importada do Catálogo Elecon 2018
   (https://elecon.com.br/wp-content/uploads/2018/08/catalogo-elecon.pdf), contendo,
   para cada linha de produto e bitola: diâmetro nominal em mm (para eletrodutos),
   espessura de parede em mm, diâmetro externo em mm e, calculado a partir desses
   dois, o diâmetro interno e a ÁREA ÚTIL em mm² (π × (diâmetro interno/2)²); para
   eletrocalhas, perfilados e leitos, dimensão nominal (base x altura) e largura útil
   em mm. Inclua pelo menos as linhas: Eletroduto Rígido Leve/Médio/Pesado
   Eletrolítico/Pré-Zincado, Eletroduto Galvanizado à Fogo (Médio/Pesado/RIR),
   Eletroduto Alumínio SCH-40, Eletroduto PVC NBR 15465, Perfilados (38x19, 38x38,
   76x38), Eletrocalhas (perfurada/lisa, dimensão customizável em múltiplos de 25mm)
   e Leitos (250mm e 500mm). Disponibilize uma rotina de importação/atualização
   (upload de planilha Excel) para esse catálogo.

5. CARGAS E DEMANDA: a soma das cargas por painel/transformador deve ser AUTOMÁTICA,
   agrupando todos os equipamentos do projeto que tenham a mesma TAG de painel/
   transformador informada no cadastro do equipamento (item 1) — sem exigir que o
   usuário selecione manualmente os equipamentos de cada painel. Se uma TAG nova for
   digitada em um equipamento, o painel correspondente deve ser criado automaticamente.
   Cada painel/transformador tem um fator de diversidade editável; o sistema calcula a
   demanda total e a corrente do alimentador.

6. RELATÓRIOS E EXPORTAÇÃO: todas as exportações devem gerar arquivos Excel (.xlsx)
   para download pelo navegador, sempre referentes ao projeto ativo — lista de
   equipamentos, lista de cabos (no layout usado internamente, com colunas Item/
   Identificação/Tensão/Nº Cabos/Nº Condutores/Seção/Isolamento/De/Para/Percurso/
   Observação), lista de eletrodutos/bandejas com taxa de ocupação, planilha de
   cargas e demanda por painel/transformador, e a memória de cálculo de cada cabo
   (uma aba por cabo, ou planilha consolidada com todos os passos do dimensionamento).

Use tabelas de referência (capacidade de condução PVC e EPR/XLPE, fatores de
temperatura e agrupamento, resistência de condutores, catálogo de cabos comerciais,
catálogo de infraestrutura Elecon) carregadas de arquivos Excel de apoio, editáveis
pelo usuário (upload) na tela de configurações.

Valide: número do projeto sempre no formato "9999-99-9999" e único; não permitir
cabo sem "De"/"Para" válidos; alertar (sem bloquear) quando o cabo escolhido
manualmente tiver seção menor que a sugerida pelo cálculo; alertar se a ocupação de
um eletroduto ultrapassar o limite da NBR 5410 correspondente ao nº de cabos do
trecho (53%/31%/40%), ou se a soma dos diâmetros de uma bandeja/leito ultrapassar a
largura útil — recalculando essas verificações automaticamente sempre que um cabo
for trocado em qualquer trecho.

A interface deve ser toda em HTML, responsiva, acessível por navegador, sem
necessidade de instalação no computador do usuário.
```

---

**Próximo passo sugerido:** revisar esta especificação, ajustar o que for necessário (por exemplo, incluir campo de código do projeto, revisão de documento, ou layout de exportação específico), e então usar o prompt da seção 9 para iniciar a construção do software.
