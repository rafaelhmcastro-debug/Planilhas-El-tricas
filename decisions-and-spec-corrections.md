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

## 2026-11-03 — Divergências novas: resolvidas pelo engenheiro

Todas as seis pendências abaixo (D1–D6) foram decididas pelo engenheiro
responsável no mesmo dia em que foram levantadas. Deixo o histórico completo
(o que a spec dizia, o que o código faz) porque é exatamente o tipo de
divergência que não pode voltar a aparecer sem passar por aqui de novo.

### D1. Potência do equipamento — RESOLVIDO: mantém campo único + unidade
- **Spec (§4.2):** dois campos, `potencia_ativa_kw` e `potencia_aparente_kva`.
- **Código atual:** um único campo `potencia_valor` (float) + `potencia_unidade`
  (enum `kW`/`W`/`CV`/`HP`/`kVA`) — `models.Equipamento`,
  `schemas.UNIDADES_POTENCIA`, `calculations.FATOR_UNIDADE_KW`.
- **Decisão (2026-11-03):** manter o código como está — campo único + unidade,
  incluindo CV/HP. A spec fica desatualizada neste ponto; **não alterar** o
  cadastro para voltar a dois campos separados.
- **Nota para a Fase 4:** o layout real do PE-G-622 (ver D6) tem duas
  sub-colunas separadas, "kW" e "kVA", dentro de "POTÊNCIA UNITÁRIA" — a
  exportação precisa converter `potencia_valor`+`potencia_unidade` para essas
  duas colunas no momento de gerar a planilha (ex.: unidade `kVA` preenche a
  coluna kVA; kW/W/CV/HP convertidos preenchem a coluna kW). Isso é só um
  detalhe de exportação, não reabre o cadastro.

### D2. Hierarquia painel → painel a montante — RESOLVIDO: regra confirmada
- **Spec (§4.6):** um único nível, sem campo nem regra para painel alimentar
  painel.
- **Código atual:** `PainelTransformador.painel_alimentador_tag` + recursão em
  `recalcular_paineis_projeto()`.
- **Decisão (2026-11-03), regra definitiva (vira regra 11-bis da spec na
  próxima revisão dela):** o usuário cadastra o **painel TOP** como o ponto
  mais a montante da instalação (sem `painel_alimentador_tag`, ou vazio). Todo
  painel/transformador a jusante informa, no seu próprio cadastro, a TAG do
  painel que o alimenta (`painel_alimentador_tag`). A demanda de cada painel é
  a soma das cargas diretas (equipamentos com essa TAG) **mais** a demanda já
  calculada de cada painel filho (que o aponta como alimentador), aplicando o
  fator de diversidade do próprio painel sobre essa soma — propagação
  recursiva jusante→montante até chegar ao TOP. **Confirma exatamente o
  comportamento já implementado em `calculations.recalcular_paineis_projeto()`
  — nenhuma mudança de código necessária, só documentar.**

### D3. Folha de dados / diagrama elétrico — RESOLVIDO: mantém campo-texto
- **Spec (§4.2):** `folha_dados_path`/`diagrama_eletrico_path` (anexo de
  arquivo).
- **Código atual:** `folha_dados_numero`/`diagrama_eletrico_numero` (texto
  livre, sem upload).
- **Decisão (2026-11-03):** manter campo-texto (nº do documento), **sem**
  implementar upload/armazenamento de arquivo para estes dois campos. A spec
  fica desatualizada neste ponto.
- **Consequência para o requisito 4 da versão Windows** ("Backup e restauração
  por arquivo .zip contendo o banco e os anexos"): como não há nenhum ponto do
  sistema hoje que armazene arquivo de usuário (confirmado por grep em
  `app/routers/*.py` — nenhum endpoint de upload em lugar nenhum, nem para
  equipamento nem para catálogo), o backup `.zip` da Fase 2, por ora, só
  precisa cobrir o banco `.db`. Se um ponto de anexo real surgir depois, o
  formato do backup é revisado então — não precisa prever uma pasta `anexos/`
  vazia desde já.

### D4. Catálogo de cabos (Prysmian) — RESOLVIDO: usar `seed_data.py` como fonte
- **Spec (§4.7):** dados extraídos dos datasheets reais da Prysmian.
- **Código atual:** `seed_data.py` rotula os valores como "SEED - valores de
  referência; substituir pelo datasheet real".
- **Decisão (2026-11-03):** usar os dados de `seed_data.py` como estão —
  **não** bloquear a Fase 1 esperando os PDFs reais da Prysmian. O comentário
  "substituir pelo datasheet real" deixa de valer como pendência bloqueante;
  continua valendo como nota de proveniência (são valores de referência, não
  extraídos de datasheet, mas aprovados para uso).

### D5. Tabelas de capacidade de condução (NBR 5410) — RESOLVIDO: usar as atuais
- `seed_data.py`: "As tabelas de capacidade de condução (NBR 5410, tabelas 36 a
  39) também devem ser conferidas com a edição vigente da norma."
- **Decisão (2026-11-03):** usar as tabelas já seedadas
  (`tab_capacidade_conducao`, `tab_fator_temperatura`, `tab_fator_agrupamento`,
  `tab_resistividade_condutor`) como estão — **não** bloquear a Fase 1
  esperando confirmação de edição da norma.

### D6. PE-G-622 / PE-E-601 — RESOLVIDO: ambos recebidos como exemplo
- **Arquivo recebido:** `PE-G-622_Lista_Equipamentos_Rev_3.xls` (autor original
  CVRD/Vale, formato Excel 97-2003), salvo em
  `docs/referencias/PE-G-622_Lista_Equipamentos_Rev_3.xls`. **Assumi que é um
  modelo em branco (sem dado de projeto real preenchido — só texto de
  placeholder como "XXXXXXX", "X0000(-00)", "LL-NNNNLL-L-NNNNN") e por isso
  seguro para versionar no repositório; não encontrei marca de classificação/
  restrição preenchida na planilha. Sinalizando essa suposição aqui — corrija
  se o arquivo não puder ficar no repositório.**
- **Estrutura confirmada (aba "Elétrica", a relevante para este sistema; há
  também "F. Rosto" e "Mecânica", fora do nosso escopo):**
  - **Bloco de cabeçalho do documento** (linhas 0–9, todas com mesclagem de
    células): logomarca da contratada, classificação, nº do programa/projeto
    genérico, fase do projeto, nome da área/subárea, **Nº VALE** (nº do projeto
    do cliente, formato `LL-NNNNLL-L-NNNNN` — diferente do nosso
    `9999-99-9999`), **Nº (CONTRATADA)** (nosso próprio nº de projeto), página,
    revisão, tipo de documento.
  - **Bloco de revisões** (igual ao já usado no memorial da NBR 5419-2 gerado
    neste mesmo projeto): Rev. / TE (A-PRELIMINAR ... H-CANCELADO) / Descrição
    / Por / Ver. / Apr. / Aut. / Data.
  - **Colunas de dados** (linhas 12–14, 10 colunas lógicas, bem mais enxuto que
    nossa exportação atual): `TAG` | `NOME` | `DESCRIÇÃO (características
    principais)` | `POTÊNCIA UNITÁRIA` (subcolunas `kW` e `kVA`) | `DIMENSÕES
    (m)` | `PESO UNITÁRIO kg` | `FOLHAS DE DADOS` | `DIAGRAMA ELÉTRICO` |
    `FORNECEDOR` | `OBSERVAÇÃO`.
  - **Achados que a Fase 4 precisa tratar, não a Fase 0:**
    1. O layout real **não tem** tensão, fases, cosφ, FD, corrente nominal nem
       potência de demanda — nossa `exportar_equipamentos()` atual tem essas
       colunas a mais (20 colunas no total); não é uma contradição, é um
       relatório mais analítico que o PE-G-622 oficial pede. Decisão de Fase 4:
       gerar a aba no formato PE-G-622 estrito (10 colunas, cabeçalho
       completo) como exportação própria, mantendo a exportação atual
       (mais rica) como relatório interno/analítico separado — **a confirmar**.
    2. O layout real tem `TAG` **e** `NOME` como colunas separadas; nosso
       `models.Equipamento` só tem `tag` + `descricao` (sem campo `nome`
       próprio). Precisa decidir, na Fase 4 (ou já na Fase 2 se o engenheiro
       preferir mudar o esquema), se `NOME` vem de um novo campo ou é derivado
       de `descricao`/`tipo_carga`.
    3. Confirma meu achado anterior sobre a lista de cabos (PE-E-601): o
       conjunto de colunas citado na seção 9 da spec já é compatível com o que
       `exportar_cabos()` gera hoje, mais colunas analíticas extras — mesmo
       padrão do PE-G-622.
- **Atualização (2026-11-03) — PE-E-601 RESOLVIDO:** o engenheiro enviou 4
  planilhas reais como modelo ("o layout PE-E601 usa os modelos em anexos"):
  `Lista_Cabos_0010-26-0003.xlsx`, `Lista_Eletrodutos_Bandejas_0010-26-0003.xlsx`,
  `Lista_Equipamentos_0010-26-0003.xlsx`, `Memoria_Calculo_0010-26-0003_1.xlsx`.
  Conferindo campo a campo: **os cabeçalhos de coluna das 4 planilhas são
  idênticos, na mesma ordem, aos que `cabos-app/app/excel_export.py` já gera
  hoje** (`exportar_cabos`, `exportar_infraestrutura`, `exportar_equipamentos`,
  `exportar_memoria_calculo`) — são exports reais do próprio app web, sem o
  bloco de cabeçalho/revisão formal visto no PE-G-622. Conclusão: **PE-E-601
  não exige layout novo nem bloco de cabeçalho da contratada** — o formato que
  a Fase 4 deve reproduzir no app desktop é exatamente o que já existe em
  `excel_export.py`. Isso não contradiz os achados do PE-G-622 (item 1 acima,
  ainda "a confirmar"): ficam como duas questões distintas — se será preciso
  também um export estrito em formato PE-G-622 para a lista de equipamentos,
  decisão que continua pendente para a Fase 4.
  **Não versionei os 4 arquivos recebidos no repositório** (diferente do que
  fiz com o PE-G-622): eles têm dado de projeto específico preenchido (nº
  0010-26-0003, "CASAS DE BOMBAS", tags de equipamento) em vez de texto de
  placeholder em branco; mesmo parecendo dado de teste, preferi não assumir
  que é seguro publicar no git sem confirmar. A informação estrutural que
  importa (cabeçalhos de coluna, ausência de bloco formal) já está registrada
  aqui por extenso. Avise se quiser que eu guarde os arquivos originais no
  repo mesmo assim.

---

## 2026-11-03 — Decisões finais antes do início da Fase 1

- **ADR 0001 aprovada como está** pelo engenheiro responsável.
- **Login multiusuário — RESOLVIDO: removido.** `models_auth.py`,
  `routers/auth.py`, `routers/admin.py` (~800 linhas: login, aprovação de
  usuário, log de acesso) não entram no esquema de banco nem na Fase 2 do
  porte. App desktop de usuário único.
- **Formato do PDF da memória de cálculo** (reportlab vs. weasyprint): ainda em
  aberto, decisão adiada para a Fase 4 — não bloqueia Fase 1.
- **PE-E-601** (layout real da lista de cabos): RESOLVIDO em 2026-11-03 (ver
  D6 acima) — usa o formato já existente em `excel_export.py`, sem bloco de
  cabeçalho formal.
- **Nome do programa:** RESOLVIDO em 2026-11-03 — `Calc 54` (atualizado em
  `desktop/app/database.py`, constante `NOME_PROGRAMA`).

---

## 2026-11-03 — Fase 3 (interface): decisões de implementação, nenhuma de cálculo

Nenhuma fórmula ou regra normativa mudou na Fase 3 — a camada de orquestração
(`desktop/app/calculations.py`) só busca dados e chama o núcleo puro já
testado na Fase 1 (`desktop/core/`); o teste de integração novo
(`app/tests/test_integracao_api.py`) sobe a API de ponta a ponta e confere
que os resultados batem com os mesmos casos de referência. As decisões abaixo
são de produto/implementação, dentro do que a ADR 0001 já previa, mas registro
aqui por completude:

- **Tela "Sistema" nova em Configurações** (pasta de dados, backup,
  restauração): não existe no app web (lá o banco mora no servidor; quem usa
  nunca precisa escolher pasta nem tirar backup manual) — criada para cumprir
  os requisitos 2 e 4, que a Fase 2 só tinha implementado no backend
  (`database.py`, `backup.py`), sem tela nenhuma até agora.
- **Troca de pasta de dados e restauração de backup exigem reiniciar o
  programa.** Decisão de segurança: trocar o engine do SQLAlchemy em tempo de
  execução, com conexões abertas, é risco real de corrupção que não compensa
  evitar um restart. A pasta antiga nunca é apagada — só deixa de ser apontada
  pelo ponteiro — e a restauração sempre guarda cópia de segurança do banco
  atual antes de sobrescrever (requisito "nunca apagar dado do usuário em
  silêncio").
- **Catálogos em Configurações deixam de ter modo "somente leitura".** O app
  web restringia edição de catálogo a `usuarioRole === 'admin'`; sem login,
  esse conceito não existe mais — o engenheiro (único usuário) tem acesso
  completo. Consequência direta da decisão já confirmada de remover o login,
  não uma decisão nova.
- **CORS restrito a `127.0.0.1`/`localhost`** (qualquer porta, via regex) em
  vez do `allow_origins=["*"]` do app web — exigido pelo app rodar
  inteiramente offline, sem exposição de rede.

---

*Toda entrada futura segue este formato: data, o que mudou, onde está na spec
vs. no código, e se já foi confirmada ou ainda está pendente.*
