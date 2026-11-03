# WebView2 Runtime — redistribuível

`inno_setup.iss` espera encontrar aqui o arquivo:

```
MicrosoftEdgeWebview2Setup.exe
```

Esse arquivo **não fica versionado no repositório** (é um binário da
Microsoft, ~130 MB, e muda de conteúdo a cada atualização de segurança —
não faz sentido guardar no git). Baixe a **versão "Evergreen Standalone
Installer"** (não a "Evergreen Bootstrapper" — essa é pequena mas baixa o
runtime pela rede na hora da instalação, o que quebra o requisito "sem
chamada de rede") direto da página oficial da Microsoft antes de cada build
do instalador:

https://developer.microsoft.com/en-us/microsoft-edge/webview2/#download-section

Role até "Evergreen Standalone Installer" e baixe o `.exe` de 64 bits
(x64) — é o que a maioria das máquinas Windows 10/11 vai usar. Salve-o
exatamente com o nome `MicrosoftEdgeWebview2Setup.exe` nesta pasta.

## Por que esta versão, e não outra

- **Bootstrapper** (pequeno, ~2 MB): baixa o runtime da internet durante a
  instalação — não serve, quebra o requisito de instalação 100% offline.
- **Evergreen Standalone Installer** (a usada aqui, ~130 MB): instala
  offline, mas o runtime instalado continua se autoatualizando em segundo
  plano depois (via o serviço `MicrosoftEdgeUpdate` do Windows) — aceitável,
  é o próprio Windows/Edge cuidando de patch de segurança do componente,
  não o Calc 54 fazendo chamada de rede.
- **Fixed Version Runtime**: opção mais determinística (nunca atualiza
  sozinho), mas também mais pesada e exige trocar manualmente a cada
  atualização de segurança do Chromium. Fica como alternativa futura se o
  autoatualizar da Standalone se provar um problema em campo — não decidido
  agora.

## O instalador já verifica se é preciso

`inno_setup.iss`'s `PrecisaWebView2()` confere o registro do Windows antes
de rodar esse instalador — em uma máquina que já tem o runtime (Windows 11
de fábrica, por exemplo), ele não roda de novo. Mesmo assim, o arquivo
precisa estar presente nesta pasta para o Inno Setup compilar
(`[Files] ... Check: PrecisaWebView2` só pula a CÓPIA/EXECUÇÃO em tempo de
instalação, não a compilação do instalador).
