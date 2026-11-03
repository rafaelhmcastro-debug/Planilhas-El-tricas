# ADR 0001 — Porte do sistema de cabos para desktop Windows offline

- **Status:** proposto, aguardando aprovação do engenheiro responsável antes da Fase 1.
- **Data:** 2026-11-03
- **Contexto:** "Programa para preencher planilhas elétricas" é hoje uma aplicação
  web (FastAPI + SQLAlchemy + HTML/CSS/JS, `cabos-app/`, implantada no Render).
  O pedido é portá-lo para um executável Windows 10/11 (64 bits) totalmente
  offline, com banco local e instalador próprio, preservando a especificação
  (`especificacao_software_cabos.md`) e sem alterar fórmulas sem registrar em
  `decisions-and-spec-corrections.md`.

---

## 1. Stack escolhida

| Camada | Escolha | Por quê |
|---|---|---|
| Núcleo de cálculo | Python puro, pacote `core/`, sem `Session` do SQLAlchemy nem import de FastAPI | Requisito explícito (Fase 1): testável sem banco nem UI |
| Persistência | SQLite em arquivo, SQLAlchemy ORM (já em uso) | Já é o banco de dev do app web; zero infra extra para o usuário final |
| Migrações | **Alembic** (substitui `cabos-app/app/migrate.py`) | Ver §4 |
| Camada de API/orquestração | FastAPI, reaproveitando quase integralmente `routers/`, `schemas.py`, `excel_export.py` | Minimiza reescrita; services passam a chamar `core/` em vez de calcular inline |
| Interface | **pywebview** sobre o FastAPI existente, escutando só em `127.0.0.1` em porta livre; frontend = o `static/` atual (HTML/CSS/JS), reaproveitado quase sem mudança | Ver §2 — decisão com maior impacto no cronograma |
| Empacotamento | **PyInstaller**, modo `--onedir` | Ver §3 |
| Instalador | **Inno Setup** | Ver §3 |
| Export Excel | `openpyxl` (já em uso) | Já não depende de Office instalado |
| Export PDF da memória de cálculo | `reportlab` ou `weasyprint` — **a decidir na Fase 4**, não bloqueia Fase 0 | Nenhum dos dois exige Office; weasyprint tem dependência nativa (GTK/Pango no Windows) mais pesada — avaliar quando chegar na Fase 4 |
| Dependências | `requirements.txt` com versões travadas (`==`), herdando os pins já usados em `cabos-app/requirements.txt` onde aplicável | Requisito explícito; evita builds não reprodutíveis |

## 2. pywebview vs. PySide6 — comparação pedida no item 3

| Critério | pywebview + frontend atual | PySide6 (reescrita nativa) |
|---|---|---|
| **Esforço** | Baixo–médio. Reaproveita ~100% de `static/` (10 telas JS já construídas, incluindo a identidade visual recém-refeita) e ~100% de `routers/`+`schemas.py`+`excel_export.py`. O trabalho real é: extrair `core/` de `calculations.py` (ver §4), adaptar `database.py` para o caminho local, e escrever a casca pywebview (abrir janela, subir uvicorn em thread, escolher porta livre). | Alto. Reescreve as 10 telas do zero em widgets/QML: grades com busca/ordenação, formulários com validação, modal de memória de cálculo com fórmulas passo a passo, seletor de percurso com reordenação de trechos (exigido na spec §6.4), árvore de painéis. Esse esforço rivaliza ou ultrapassa o de portar o núcleo de cálculo inteiro. |
| **Aparência** | Idêntica à web atual — já tem identidade visual própria ("Pôr do sol"), já testada visualmente nas 10 telas. | Visual nativo do Windows (Qt), mas exige retrabalho de design do zero; Qt no Windows não replica automaticamente o visual já aprovado. |
| **Risco** | WebView2 precisa estar presente — no Windows 11 já vem instalado; no Windows 10 geralmente chega via Windows Update, mas não é garantido em máquina limpa/offline. Mitigação: empacotar o **WebView2 Runtime (Evergreen Standalone Installer ou Fixed Version)** dentro do instalador Inno Setup e instalá-lo silenciosamente — sem chamada de rede em tempo de execução. Testar em VM limpa Windows 10 e 11 com rede desligada (critério de aceite 2). | Sem dependência de WebView2 — risco desse tipo zero. Em troca, risco de cronograma/regressão muito maior (reescrever 10 telas já validadas) e risco de a UI nova não cobrir alguma regra de negócio que hoje só existe implícita no JS atual (ex.: lógica de alerta não bloqueante, autocomplete de TAG). |
| **Manutenção** | Qualquer ajuste de tela continua sendo HTML/CSS/JS — mesma velocidade de iteração já demonstrada neste projeto. Possível (não obrigatório) manter o mesmo código rodando como app web no futuro, já que backend/frontend não mudam de natureza. | Exige conhecimento de Qt/PySide6 para qualquer ajuste futuro de tela — curva de aprendizado maior, duas bases de UI divergentes (web existente + desktop novo) se algum dia o app web precisar continuar existindo. |

**Recomendação: pywebview.** Para este projeto especificamente, a interface já está
construída, testada e com identidade visual recém-fechada — descartá-la para uma
reescrita nativa não se paga em nenhum dos critérios pedidos, e o único risco real
do pywebview (presença do WebView2) tem mitigação direta e testável. Guardo a
alternativa PySide6 nesta ADR caso o critério de "aparência 100% nativa" se prove
mais importante do que parece hoje — nesse caso, reabrir esta decisão antes da
Fase 3, não durante.

## 3. Empacotamento e instalador

- **PyInstaller `--onedir`** em vez de `--onefile`: inicialização mais rápida (sem
  extrair para `%TEMP%` a cada execução — risco de caminho com acentuação
  problemática em cenários raros de codepage legado, requisito 8), menor taxa de
  falso positivo de antivírus/SmartScreen, e mais fácil de depurar "módulo
  faltando" durante a Fase 5. FastAPI/SQLAlchemy/Alembic/openpyxl/pywebview fazem
  import dinâmico — vou precisar de `hiddenimports` explícitos no `.spec`;
  recomendo um **teste de empacotamento de fumaça já ao final da Fase 1** (não
  esperar a Fase 5), para não descobrir problema de empacotamento só no fim.
- **Inno Setup** em vez de MSIX: instala sem privilégio de administrador
  (`%LOCALAPPDATA%`), permite página customizada de pergunta "preservar o banco?"
  na desinstalação (requisito 5) sem fricção, e tem exemplos maduros para apps
  PyInstaller. MSIX exigiria certificado de assinatura e empacotamento mais
  rígido sem ganho claro para este caso de uso de instalação local única.
- **Nenhuma chamada de rede**: `CORSMiddleware(allow_origins=["*"])` do app atual
  precisa restringir a `http://127.0.0.1:<porta>`. **Confirmado, não é hipótese:**
  `static/index.html` carrega as fontes Barlow/Barlow Condensed/JetBrains Mono
  direto do Google Fonts (`fonts.googleapis.com`/`fonts.gstatic.com`) desde a
  identidade visual implantada nesta mesma sessão — isso quebra o critério de
  aceite "com a rede desligada, o programa abre" exatamente como está hoje.
  Ação da Fase 3: baixar os arquivos `.woff2` dessas três famílias e servi-los
  como estáticos locais (`static/fonts/`), trocando o `<link>` do Google por
  `@font-face` local — mudança pequena e isolada, não reabre a decisão de design.

## 4. Refatoração necessária do núcleo de cálculo (não é cópia direta)

`cabos-app/app/calculations.py` hoje recebe `db: Session` e consulta as tabelas
normativas (`TabCapacidadeConducao`, `TabFatorTemperatura` etc.) **durante** o
cálculo — o núcleo está acoplado ao SQLAlchemy. Isso contraria o requisito da
Fase 1 ("núcleo de cálculo... sem dependência de UI nem de banco, para testar sem
interface"). Proposta: `core/` recebe **dados simples** (dicionários/dataclasses:
tabelas já carregadas, parâmetros do cabo) e devolve resultados simples; a busca
no banco migra para a camada `app/` (routers), que carrega a tabela normativa e
repassa ao `core/`.

Uso como referência o padrão já consolidado em `cabos-app/app/risco5419/`
(`dados/*.json` + `tabelas.py` com `ValorNaoDisponivel` apontando exatamente a
tabela/chave faltante) — mais rigoroso que o padrão atual do `calculations.py` e
já testado neste mesmo repositório.

## 5. Esquema de banco (visão geral — detalhado na Fase 2)

Mantém as tabelas atuais de `cabos-app/app/models.py` (`projetos`,
`equipamentos`, `eletrodutos_bandejas`, `cabos`, `cabo_trechos`,
`paineis_transformadores`, `catalogo_cabos`, `catalogo_infraestrutura_eletrica`,
tabelas normativas), mais:
- Tabela de versão do Alembic (`alembic_version`, criada pelo próprio Alembic).
- **Pendente de D2** (`decisions-and-spec-corrections.md`): confirmar por escrito
  a regra de hierarquia painel→painel a montante antes de fechar o esquema.
- **Pendente de D3**: se anexos viram arquivo de verdade, uma tabela `anexos`
  (metadado + caminho relativo dentro da pasta de dados) — afeta o layout da
  pasta de dados e o formato do backup `.zip` desde a Fase 2, não é algo para
  adicionar depois.
- **Proposta a confirmar, não decidida:** remover ou simplificar drasticamente
  `models_auth.py` (login multiusuário, aprovação, log de acesso — ~800 linhas)
  para um app desktop de usuário único instalado na própria máquina. Guardo como
  proposta porque é decisão de produto, não só técnica.
- Módulo `risco5419` (já maduro, com dados próprios e testes) entra no esquema
  **só depois da Fase 5**, como o próprio pedido já define.

## 6. Pasta de dados e configurações

- Local padrão: `%LOCALAPPDATA%\<NomeDoPrograma>\` (`dados.db` + `anexos/` +
  `logs/`).
- Pasta alternativa (requisito 2): como o ponteiro para "onde está minha pasta de
  dados" não pode morar dentro da própria pasta que ele aponta, fica em um
  arquivo fixo e pequeno em `%APPDATA%\<NomeDoPrograma>\config.json`. Trocar a
  pasta nas Configurações fecha a conexão com o banco atual, oferece
  copiar/mover os dados existentes, atualiza o ponteiro e reabre no novo local.
- Log de erros com rotação (requisito 7): `logging.handlers.RotatingFileHandler`
  em `logs/`, sem payload de requisição nem dado de projeto no corpo da mensagem
  — só exceção + stack trace + timestamp.

## 7. Estrutura de pastas proposta

```
desktop/
  core/                     # cálculo puro — sem FastAPI, sem Session
    calculo_equipamentos.py
    calculo_cabos.py
    calculo_infraestrutura.py
    calculo_paineis.py
    tabelas_normativas.py    # funções de busca sobre dados já carregados
    memoria.py
  app/
    models.py
    schemas.py
    database.py              # resolução do caminho local + config.json
    routers/                 # mesma divisão do app atual
    migrations/               # Alembic
      versions/
    seed/                     # Elecon 2018 + NBR 5410 como dados versionados
                              # (json/csv), não literais Python inline
  desktop_shell/
    main.py                  # sobe uvicorn em thread, escolhe porta livre,
                              # abre janela pywebview em 127.0.0.1
    bridge.py                # pontes JS↔Python (diálogos nativos de
                              # arquivo para backup/restauração e anexos)
  static/                    # frontend atual, quase sem mudança
  packaging/
    pyinstaller.spec
    inno_setup.iss
  tests/
    core/                    # unitários, sem banco
    integracao/              # API + SQLite real
```

## 8. Riscos

| # | Risco | Mitigação |
|---|---|---|
| 1 | WebView2 ausente em Windows 10 limpo/offline | Empacotar o runtime (Evergreen Standalone ou Fixed Version) no instalador; testar em VM limpa com rede desligada |
| 2 | PyInstaller + imports dinâmicos (FastAPI/SQLAlchemy/Alembic/openpyxl) | `hiddenimports` explícitos; teste de empacotamento de fumaça já ao fim da Fase 1, não só na Fase 5 |
| 3 | SmartScreen/antivírus sinalizando o instalador | `--onedir` reduz heurística de falso positivo; avaliar custo de certificado de assinatura de código (fora do escopo de preço desta ADR) |
| 4 | Dados de catálogo de cabos (Prysmian) e tabelas NBR 5410 marcados no próprio código como "valor de referência, substituir pelo datasheet real" (D4/D5) | Bloqueia os casos de aceite da Fase 1 até os datasheets reais e a edição da NBR 5410 serem confirmados — não vou tratar como definitivo |
| 5 | Hierarquia painel→painel a montante não está escrita na especificação (D2) | Confirmar a regra por escrito antes de portar — é cálculo, não UI |
| 6 | Extrair `core/` de `calculations.py` é refatoração, não cópia — risco de mudar comportamento sem perceber | Mitigado pelo próprio plano da Fase 1: casos de referência fornecidos e conferidos à mão antes de virarem teste de aceite |
| 7 | Requisito de anexo de arquivo real (backup "com anexos") depende de D3 não resolvido | Resolver D3 antes de fechar o esquema da Fase 2, não depois |
| 8 | Caminhos com espaço/acento (`C:\Users\João\Documentos`) | `pathlib` + SQLite já lidam bem com Unicode; `--onedir` evita extração para `%TEMP%`, reduzindo a superfície desse risco |
| 9 | Firewall do Windows perguntando ao abrir o programa | Bind estrito em `127.0.0.1` (nunca `0.0.0.0`) evita o prompt na grande maioria dos casos; porta escolhida dinamicamente (bind em porta 0) evita conflito com outros serviços locais |

## 9. Fora do escopo desta ADR (decisões de produto, não técnicas)

- Manter ou remover o login multiusuário (`models_auth.py`) — proposto remover,
  mas não decidido aqui.
- Formato final do PDF da memória de cálculo (reportlab vs. weasyprint) — decidir
  na Fase 4.
- Anexo de arquivo real vs. campo-texto para folha de dados/diagrama elétrico
  (D3) — decidir antes da Fase 2.

---

**Pendências que bloqueiam a Fase 1** (listadas também em
`decisions-and-spec-corrections.md`, seção "Divergências novas"): D1 (campo de
potência), D2 (hierarquia de painéis), D3 (anexos), D4 (datasheets Prysmian
reais), D5 (edição da NBR 5410), D6 (layouts PE-G-622/PE-E-601 reais).

Esta ADR fica parada aqui para aprovação, conforme pedido — nenhum código de
porte foi escrito.
