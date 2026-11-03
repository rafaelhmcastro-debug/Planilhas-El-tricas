# Decisões e correções à especificação

Registro de toda mudança de fórmula, regra ou campo em relação a
`especificacao_software_cabos.md`, com a data, o motivo e a fonte. Nada aqui é
alterado silenciosamente — toda entrada nova é confirmada com o engenheiro
responsável antes de ser tratada como definitiva para a Fase 1 em diante.

---

## 2026-11-03 — Decisões já travadas (reafirmadas na sessão de porte para Windows)

Estas eram instruções diretas do usuário ao abrir o porte para desktop. Checadas
contra `especificacao_software_cabos.md` (anexado nesta mesma sessão) e contra o
código atual de `cabos-app/`: **as cinco já estão implementadas e já batem com a
especificação como está escrita hoje.** Registradas aqui como ponto de partida
confirmado, não como mudança.

1. **TAG agrupa cargas sob painéis/transformadores automaticamente, sem seleção
   manual.** Spec §4.6 e regra 11; código: `calculations.garantir_painel()` +
   `recalcular_paineis_projeto()` em `cabos-app/app/calculations.py`.
2. **Dimensionamento de cabos automático, com override do usuário e alertas não
   bloqueantes.** Spec regra 8 e §7; código: `Cabo.secao_definida_manualmente` +
   `Cabo.alerta_secao_insuficiente`.
3. **Ocupação de eletroduto separada da de eletrocalha/perfilado/leito.** Spec
   regra 10a/10b; código: `calculations.calcular_ocupacao()` ramifica por
   `infra.tipo == "eletroduto"` vs. os demais.
4. **Cabos em paralelo: corrente dividida (não multiplicada) pelo nº de cabos.**
   Spec regra 4 ("corrente nominal do equipamento vinculado, **dividida** pelo
   nº de cabos em paralelo"); código: `ib = corrente_carga / cabo.num_cabos_paralelo`
   em `calculations.recalcular_cabo()`.
5. **Conversão kW→W nas fórmulas.** Spec regra 2 ("O fator × 1000 converte kW
   para W"); código: `corrente_por_aparente()` multiplica `s_kva * 1000`.

## 2026-11-03 — Correções já feitas, que não podem voltar

Idem acima — conferidas contra spec + código, **já consistentes**:

6. **Reatância X com fonte definida na fórmula de queda de tensão.** Spec regra 7
   já registra que X não consta nos datasheets levantados e manda usar um valor
   típico de referência (0,08 Ω/km), deixando isso explícito na memória de
   cálculo. O código vai além do mínimo da spec: usa
   `catalogo_cabos.reatancia_ohm_km` quando o cabo específico já foi escolhido
   (passo 8 de `recalcular_cabo()`) e só cai para o valor típico
   (`REATANCIA_TIPICA_OHM_KM = 0.08`) na falta dele — **essa extensão (prioridade
   ao catálogo) não está escrita na spec; fica registrada aqui como o
   comportamento vigente**, a confirmar.
7. **`tensao_v` presente em `paineis_transformadores`.** Já está em spec §4.6 e em
   `models.PainelTransformador.tensao_v`.
8. **`dimensao_definida_manualmente` no contexto de eletrodutos (antes
   `secao_definida_manualmente`).** Já está em spec §4.3 e em
   `models.EletrodutoBandeja.dimensao_definida_manualmente`. O nome
   `secao_definida_manualmente` continua existindo, mas só no contexto de
   **cabos** (`models.Cabo.secao_definida_manualmente`, spec §4.4) — são dois
   campos distintos em duas tabelas distintas, não o mesmo campo renomeado
   parcialmente. Registrado para não confundir os dois na Fase 1.
9. **Fator de agrupamento vem de `cabo_trechos`.** Spec regra 6 ("indexado pelo
   número de circuitos... contabilizado a partir de `cabo_trechos`"); código:
   `_num_circuitos_no_trecho()` conta `cabo_id` distintos em
   `CaboTrecho.eletroduto_bandeja_id`.
10. **Campos herdados do registro de cabo nas fórmulas.** `_dados_da_carga()`
    herda tensão/fases/neutro/terra/cosφ da ponta "Para" (equipamento ou
    painel), conforme spec §4.4 ("a carga alimentada pelo cabo é sempre a ponta
    'Para'").

---

## 2026-11-03 — Divergências novas encontradas ao ler spec + código (Fase 0)

**Pendentes de confirmação do engenheiro antes da Fase 1.** Não decidi nenhuma
delas sozinho; a coluna "proposta" é só o que pareceu mais natural para o porte,
não uma decisão já tomada.

### D1. Potência do equipamento: campo único + unidade, não dois campos separados
- **Spec (§4.2):** dois campos, `potencia_ativa_kw` (decimal) e
  `potencia_aparente_kva` (decimal), um dos dois opcional conforme o outro é
  informado.
- **Código atual:** um único campo `potencia_valor` (float) + `potencia_unidade`
  (enum `kW`/`W`/`CV`/`HP`/`kVA`) — ver `models.Equipamento`,
  `schemas.UNIDADES_POTENCIA`. `calculations.FATOR_UNIDADE_KW` converte CV/HP/W
  para kW antes de aplicar a regra 1 da spec.
- **Por quê isso é uma mudança real, não só nome diferente:** a spec supõe que o
  usuário pode informar P **ou** S diretamente; o código supõe que o usuário
  sempre informa um valor + uma unidade (que pode ser `kVA`, aí sim equivalente
  a informar S diretamente), e adiciona CV/HP como unidades de entrada que a
  spec não previa.
- **Pendência:** confirmar que o campo único + unidade (com CV/HP) é o
  comportamento desejado para o core do Windows, ou se deveria voltar aos dois
  campos separados da spec.

### D2. Hierarquia painel → painel a montante (não está na spec)
- **Spec (§4.6):** um único nível — equipamentos se agrupam direto em um
  painel/transformador; não há campo nem regra para um painel alimentar outro.
- **Código atual:** `PainelTransformador.painel_alimentador_tag` + recursão em
  `recalcular_paineis_projeto()` propaga demanda de painéis a jusante para o
  painel a montante, "até o painel TOP" (comentário no próprio código).
- **Pendência:** essa hierarquia multinível é claramente um requisito real do
  projeto (TOP → quadros → subquadros), mas não está descrita em nenhuma regra
  da spec. Preciso que o engenheiro confirme a regra por escrito (como ela deve
  aparecer na seção 5 da spec) antes de portar o core, para não "inventar" a
  regra 11-bis a partir só do código.

### D3. Folha de dados / diagrama elétrico: referência em texto, não anexo de arquivo
- **Spec (§4.2):** `folha_dados_path` e `diagrama_eletrico_path` — caminho de um
  arquivo anexado.
- **Código atual:** `folha_dados_numero` e `diagrama_eletrico_numero` — texto
  livre (número do documento), sem upload nem armazenamento de arquivo. Não há
  nenhum endpoint de upload para equipamento em nenhum router (conferido com
  grep em `app/routers/*.py`) — existe uma pasta `uploads/` em
  `app/main.py`, mas ela não é usada por este módulo.
- **Pendência:** confirmar se o Windows precisa de anexo de arquivo de verdade
  (PDF do datasheet/diagrama guardado junto do projeto) ou se o campo-texto
  (nº do documento, remetendo a um arquivo externo) é suficiente — isso muda o
  esquema de banco e exige lógica de backup de anexos (requisito 4 da versão
  Windows: "Backup e restauração por arquivo .zip contendo o banco **e os
  anexos**").

### D4. Catálogo de cabos (Prysmian): dados de referência, não datasheet real
- **Spec (§4.7):** "Tabela alimentada a partir das folhas de dados (datasheets)
  dos fabricantes... os PDFs da Prysmian já levantados."
- **Código atual:** `seed_data.py` marca explicitamente, no próprio comentário,
  `fonte_datasheet = "SEED - valores de referência; substituir pelo datasheet
  real"` para toda a tabela de cabos, e os diâmetros/pesos em
  `DIAM_UNIPOLAR`/`DIAM_MULTIPOLAR`/`PESO_UNIPOLAR` têm o comentário "valores de
  referência a substituir pelo datasheet real" — ou seja, **nunca foram
  conferidos contra os PDFs reais da Prysmian**, apesar do que a spec afirma.
- **Pendência:** os datasheets reais da Prysmian (Multiplex, Afumex Green
  1kV/750V, Sintenax Flex/CTL/CTL BFC Flex) precisam ser fornecidos antes da
  Fase 1 fechar os testes de aceite — não vou portar os valores de seed como se
  fossem definitivos.

### D5. Tabelas de capacidade de condução: também marcadas como "a conferir"
- `seed_data.py` (docstring do módulo): "As tabelas de capacidade de condução
  (NBR 5410, tabelas 36 a 39) também devem ser conferidas com a edição vigente
  da norma." Isso cobre `tab_capacidade_conducao`, `tab_fator_temperatura`,
  `tab_fator_agrupamento`, `tab_resistividade_condutor` — todas com valores
  plausíveis (batem com a NBR 5410 que conheço), mas sem confirmação formal de
  edição/data registrada no código.
- **Pendência:** confirmar a edição da NBR 5410 usada como referência (a spec
  não data isso) antes de tratar essas tabelas como caso de aceite na Fase 1.

### D6. PE-G-622 / PE-E-601: layouts reais não estão no repositório
- Spec §8 e §9 citam os dois códigos de documento da empresa como referência de
  layout de exportação. Nenhum arquivo `PE-G-622` ou `PE-E-601` está no
  repositório nem foi anexado até agora.
- O único ponto em que a spec dá colunas concretas é na seção 9 (prompt),
  para a lista de cabos: "Item/Identificação/Tensão/Nº Cabos/Nº
  Condutores/Seção/Isolamento/De/Para/Percurso/Observação". A exportação atual
  (`excel_export.exportar_cabos()`) usa essas colunas na mesma ordem, mais
  extras (Configuração, Construção, Cabo do catálogo, Distância, Ib, Queda de
  tensão, Método, Seção sugerida) — um superconjunto plausível, não uma
  contradição.
- Para a lista de equipamentos (PE-G-622) não há nem esse mínimo: a spec não
  lista colunas, só diz "layout já usado pela empresa".
- **Pendência:** preciso dos arquivos/modelos reais de PE-G-622 e PE-E-601
  (mesmo que só o cabeçalho de colunas, numeração e campos fixos como
  logotipo/rodapé) antes da Fase 4 (exportações) — não vou supor o layout a
  partir só do que já existe.

---

*Toda entrada futura segue este formato: data, o que mudou, onde está na spec
vs. no código, e se já foi confirmada ou ainda está pendente.*
