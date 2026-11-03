; Instalador do Calc 54 (Inno Setup). NÃO testado neste sandbox (ISCC é
; Windows-only) — ver packaging/BUILD.md para o passo a passo de build e
; validação numa máquina Windows real antes do primeiro uso em produção.
;
; Requisitos atendidos aqui (ver docs/adr/0001-porte-desktop-windows.md):
; - Instala sem privilégio de administrador (PrivilegesRequired=lowest,
;   instala em {localappdata}, nunca em Arquivos de Programas).
; - WebView2 Runtime embutido e instalado silenciosamente, sem chamada de
;   rede (Evergreen Standalone Installer — ver packaging/redist/README.md).
; - Pergunta na desinstalação se quer preservar o banco de dados do
;   usuário (requisito 5) — ver seção [Code].

#define AppName "Calc 54"
#define AppVersion "0.1.0"
#define AppPublisher "Castro Desenho e Projetos"
#define AppExeName "Calc 54.exe"
#define DistDir "..\dist\Calc 54"

[Setup]
; GUID gerado uma única vez para este app — NUNCA trocar entre versões
; (é o que permite o instalador reconhecer "já instalado" e oferecer
; atualizar em vez de instalar por cima às cegas).
AppId={{134BD4FC-9002-4166-BDF8-8ED598F8C9BE}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\dist_instalador
OutputBaseFilename=Calc54_Instalador_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
; Unicode nativo do Inno Setup 6+ — caminho com espaço/acento (requisito não
; funcional) funciona sem configuração extra.

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; WebView2 Runtime (Evergreen Standalone Installer) — baixar antes do build,
; ver packaging/redist/README.md. O instalador do Calc 54 só roda esse
; arquivo em [Run] abaixo; não há chamada de rede feita por este script.
Source: "redist\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: PrecisaWebView2

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na área de trabalho"; GroupDescription: "Ícones adicionais:"

[Run]
; /silent + /install: instala o runtime sem interação e sem reiniciar nada
; que já esteja em uso. A Standalone Installer funciona sem rede (diferente
; do Bootstrapper, que baixa o runtime na hora — por isso a escolha de
; empacotar a Standalone, não o Bootstrapper, ver ADR 0001 §3).
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Instalando o componente do navegador (WebView2)..."; Check: PrecisaWebView2; Flags: waituntilterminated
Filename: "{app}\{#AppExeName}"; Description: "Abrir o {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Nunca lista aqui a pasta de dados do usuário (%LOCALAPPDATA%\Calc 54\...) —
; essa decisão é feita em tempo real pelo diálogo em [Code], não por uma
; regra estática de arquivos a apagar.

[Code]
function PrecisaWebView2(): Boolean;
var
  ChaveExiste: Boolean;
begin
  { Mesma verificação que o Bootstrapper do WebView2 documenta oficialmente:
    a presença da chave de versão "pv" (não vazia, diferente de "0.0.0.0")
    sob qualquer uma das chaves abaixo indica runtime já instalado — não
    reinstala por cima de uma instalação existente (Windows 11 já vem com
    o WebView2 Runtime, por exemplo). }
  ChaveExiste :=
    RegKeyExists(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}') or
    RegKeyExists(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}') or
    RegKeyExists(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}');
  Result := not ChaveExiste;
end;

function PastaDeDados(): String;
begin
  { Mesma regra de app/database.py: %LOCALAPPDATA%\Calc 54 — repetida aqui
    porque o instalador roda fora do Python; se o nome do programa mudar
    de novo, precisa atualizar os dois lugares. }
  Result := ExpandConstant('{localappdata}\{#AppName}');
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Resposta: Integer;
  Pasta: String;
begin
  { Requisito 5: ao desinstalar, perguntar se quer preservar o banco. A
    pergunta vem DEPOIS de desinstalar os arquivos do programa
    (usPostUninstall), não antes — assim o arquivo de dados nunca corre
    risco de ser apagado por engano pelo processo normal de remoção do
    Inno Setup, que só lista os arquivos do PROGRAMA em [Files], nunca a
    pasta de dados do usuário. }
  if CurUninstallStep = usPostUninstall then
  begin
    Pasta := PastaDeDados();
    if DirExists(Pasta) then
    begin
      Resposta := MsgBox(
        'Deseja preservar os dados do Calc 54 (projetos, catálogos, backups)?' + #13#10 +
        'Pasta: ' + Pasta + #13#10#13#10 +
        'Sim = mantém a pasta para uma reinstalação futura.' + #13#10 +
        'Não = apaga os dados definitivamente.',
        mbConfirmation, MB_YESNO
      );
      if Resposta = IDNO then
        DelTree(Pasta, True, True, True);
    end;
  end;
end;
