# Empacotamento do Calc 54 (Fase 5)

Passo a passo para gerar o instalador Windows a partir deste código. Escrito
e testado parcialmente **neste sandbox Linux, sem interface gráfica** — a
seção final deste documento diz exatamente o que foi e o que não foi
verificado aqui, e o que ainda precisa de confirmação numa máquina Windows
real antes do primeiro uso em produção.

## 1. Pré-requisitos (máquina Windows 10/11, 64 bits)

- **Python 3.11** (mesma versão usada no desenvolvimento) instalado —
  https://www.python.org/downloads/release/python-3119/, marcando "Add
  python.exe to PATH" no instalador.
  **Importante:** se a máquina já tiver outra versão de Python (ex.: 3.13,
  3.14) como padrão, o comando `python -m venv` abaixo vai criar o venv com
  essa outra versão, não com o 3.11 — e aí o `matplotlib==3.8.4` (travado
  na mesma versão do app web) não vai achar wheel pronta pra ela, tentando
  compilar `numpy` do zero (exige Visual Studio Build Tools, que a máquina
  provavelmente não tem) e falhando. Por isso o passo 2 usa `py -3.11`
  (o "Python Launcher for Windows", instalado junto com qualquer Python
  oficial), que escolhe a versão certa mesmo com várias instaladas — não
  `python` sozinho.
- [Inno Setup 6](https://jrsoftware.org/isdl.php) instalado (fornece o
  `ISCC.exe` usado no passo 4).

## 2. Preparar o ambiente

```powershell
cd desktop
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python --version
```
- `Set-ExecutionPolicy -Scope Process` libera rodar o script de ativação só
  nesta janela do PowerShell (volta ao normal ao fechá-la) — necessário em
  várias instalações do Windows, onde isso vem bloqueado por padrão.
- Use `.\.venv\Scripts\Activate.ps1` (com `.\` na frente e a extensão
  `.ps1`), não `.venv\Scripts\activate` — sem o `.\` o PowerShell não
  resolve o caminho como script e dá erro de "módulo não encontrado".
- Confirme que `python --version` mostrou `Python 3.11.x` antes de seguir —
  se mostrou outra versão, `py -3.11` não achou o Python 3.11 instalado
  (reinstale-o marcando "Add python.exe to PATH").

```powershell
pip install -r requirements.txt
```

## 3. Gerar o executável com PyInstaller

```powershell
pip install -r requirements-build.txt
pyinstaller packaging\pyinstaller.spec --noconfirm
```

Gera `desktop\dist\Calc 54\Calc 54.exe` + a pasta `_internal\` ao lado
(dados empacotados: `static\`, `app\migrations\`, `app\seed\*.json`,
`alembic.ini`).

**Teste manual obrigatório aqui, antes de seguir para o instalador:**
rode `dist\Calc 54\Calc 54.exe` diretamente — pelo Explorer (clique duplo)
ou pelo PowerShell com:
```powershell
& ".\dist\Calc 54\Calc 54.exe"
```
(o `&` + o caminho inteiro entre aspas é a forma correta no PowerShell de
rodar um executável cujo caminho tem espaço). A janela do Calc 54 deve
abrir e o app deve funcionar normalmente. Se não abrir, **não** compile o
instalador — volte e investigue o log em
`%LOCALAPPDATA%\Calc 54\logs\calc54.log` primeiro.

## 4. Baixar o WebView2 Runtime (Standalone Installer)

Siga `packaging/redist/README.md` — baixe o arquivo e salve como
`desktop\packaging\redist\MicrosoftEdgeWebview2Setup.exe`.

## 5. Compilar o instalador

```powershell
cd packaging
ISCC.exe inno_setup.iss
```

Gera `dist_instalador\Calc54_Instalador_0.1.0.exe` (um nível acima de
`desktop\`, na raiz do repositório).

## 6. Critérios de aceite antes de liberar (ver pedido original)

Testar numa **VM Windows limpa** (sem o Calc 54, sem WebView2 pré-instalado
se possível, para testar o caminho de instalação dele também):

- [ ] Instala sem pedir elevação de administrador.
- [ ] **Com a rede desligada**, o instalador completa e o programa abre
  normalmente (critério de aceite "100% offline" — testar de verdade com a
  placa de rede desligada, não só "sem abrir nada na tela").
- [ ] Abre numa pasta com espaço/acento no caminho do usuário (ex.:
  `C:\Users\João Ápice Araújo\`) sem erro.
- [ ] Desinstalar oferece a opção de preservar o banco; escolher "não" de
  fato apaga `%LOCALAPPDATA%\Calc 54\`, escolher "sim" preserva.
- [ ] Reinstalar depois de preservar os dados encontra o banco anterior.

## O que foi verificado neste sandbox (Linux, sem GUI) e o que não foi

**Verificado de verdade** (rodando o build gerado, não só lendo o código):
- O `.spec` builda sem erro com PyInstaller 6.22 (versão em
  `requirements.txt`/testada aqui).
- O binário gerado (versão Linux do build, mesma lógica de empacotamento)
  resolve corretamente os caminhos de dados empacotados via
  `sys._MEIPASS` (`app/database.pasta_recursos_empacotados()`) — migrações
  do Alembic rodam, acham `alembic.ini` e `app/migrations/` dentro do
  pacote; `app/seed.py` acha `app/seed/*.json`; `desktop_shell/main.py` acha
  `static/`.
- **Dois bugs reais encontrados e corrigidos** só por ter rodado o binário
  de verdade (não apareceriam só lendo o código):
  1. `alembic.ini` tinha comentário com acento; o Alembic lê esse arquivo
     com `encoding="locale"` — quebra em qualquer ambiente sem locale UTF-8
     configurado (este sandbox, e possivelmente alguma instalação limpa de
     Windows). Corrigido deixando os comentários em ASCII.
  2. O logger raiz recebia dois handlers conflitantes (o nosso + um que o
     Alembic instala via `fileConfig()` no `env.py`), causando log
     duplicado e, mais grave, o handler do Alembic (que escreve em stderr,
     invisível no executável sem console) ficava sobrepondo o nosso depois
     de cada migração. Corrigido instalando o handler rotativo DEPOIS das
     migrações e limpando os handlers existentes antes.
  3. Se o servidor falhar ao subir (ex.: erro de migração), o programa
     ficava preso 15s esperando conexão numa porta que nunca ia responder,
     e só então abria uma janela fadada a não conectar — sem indicar o
     motivo real. Corrigido: a thread do servidor agora repassa a exceção
     para a thread principal, que detecta a morte da thread e falha rápido
     com a mensagem de erro original.
- Suíte de testes completa (18 núcleo + 17 app) continua passando depois
  de todas essas mudanças.

**NÃO verificado neste sandbox** (sem GUI/Windows — precisa de confirmação
numa máquina Windows real antes de liberar para o engenheiro usar):
- A janela pywebview em si abrindo de verdade (aqui só confirmamos que o
  pywebview tenta e falha corretamente por falta de GTK/Qt — esperado num
  Linux sem ambiente gráfico; no Windows real ele deve achar o backend
  `edgechromium`/WebView2 em vez disso).
- O diálogo nativo de pasta (`desktop_shell/bridge.py`, usado pela tela
  Sistema → "Escolher outra pasta…").
- A instalação do WebView2 Runtime pelo instalador (`PrecisaWebView2()` e o
  `[Run]` que executa o Standalone Installer).
- O instalador Inno Setup em si (`ISCC.exe` é Windows-only).
- Todos os itens da checklist da seção 6 acima.
