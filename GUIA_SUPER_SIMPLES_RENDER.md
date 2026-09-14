# 🎈 GUIA SUPER SIMPLES: COLOCAR O PROGRAMA NA INTERNET

## ⚠️ IMPORTANTE: ANTES DE COMEÇAR

Você vai precisar de:
- ✅ Uma conta de **email** (pode ser Gmail, Outlook, etc)
- ✅ Seu computador conectado à internet
- ✅ A pasta `C:\Users\Rafael Castro\Downloads\files` com o código

---

## 📋 ÍNDICE DO GUIA

1. [PASSO 1: Criar conta no GitHub](#passo-1-criar-conta-no-github)
2. [PASSO 2: Enviar o código para GitHub](#passo-2-enviar-o-código-para-github)
3. [PASSO 3: Criar conta no Render](#passo-3-criar-conta-no-render)
4. [PASSO 4: Conectar GitHub com Render](#passo-4-conectar-github-com-render)
5. [PASSO 5: Fazer o programa rodar](#passo-5-fazer-o-programa-rodar)
6. [PASSO 6: Testar se funcionou](#passo-6-testar-se-funcionou)

---

# PASSO 1: Criar conta no GitHub

GitHub é como um "armário na nuvem" onde você guarda seu código para o mundo ver.

## 1.1 - Ir para o site do GitHub

1. **Abra o navegador** (Chrome, Edge, Firefox)
2. **Digite na barra de endereço:** `https://github.com`
3. **Aperte ENTER**

Você deve ver uma página com um logo com um gato preto.

## 1.2 - Clicar em "Sign up"

Na página principal, procure pelo botão **"Sign up"** (que quer dizer "Registrar")
- Está geralmente no canto superior direito
- **Clique nele**

## 1.3 - Preencher seu email

1. Uma página abrirá pedindo seu **email**
2. **Digite seu email** (por exemplo: seu@gmail.com)
3. **Clique em CONTINUE**

## 1.4 - Criar uma senha

1. GitHub pedirá uma **senha**
2. **Digite uma senha segura** (use letras, números e símbolos)
3. **Clique em CONTINUE**

❗ **DICA:** Escreva essa senha em um lugar seguro! Você vai precisar dela.

## 1.5 - Escolher um nome de usuário

1. GitHub pedirá um **nome de usuário** (seu nickname)
2. **Escolha um nome legal** (por exemplo: `rafael-cabos`, `cable-master`, etc)
3. Verifique se o nome está disponível (GitHub avisa)
4. **Clique em CONTINUE**

## 1.6 - Confirmar seu email

GitHub vai enviar um **código para seu email**

1. **Abra seu email**
2. **Procure por uma mensagem do GitHub**
3. **Copie o código** que está lá (geralmente 6 números)
4. **Volte para o site do GitHub**
5. **Cole o código** na caixa que pediu
6. **Clique em CONTINUE**

## 1.7 - Pronto! Conta criada!

GitHub vai mostrar algumas perguntas (você pode pular todas ou responder)
- Pode deixar como está
- **Clique em "Skip this for now"** se quiser pular

✅ **Sua conta GitHub foi criada!**

---

# PASSO 2: Enviar o código para GitHub

Agora você vai enviar todo o código do programa para o GitHub.

## 2.1 - Abrir o PowerShell (Terminal do Windows)

1. **Pressione:** `Windows + R`
2. Uma caixa abrirá
3. **Digite:** `powershell`
4. **Aperte ENTER**

Uma janela preta abrirá (é o terminal).

## 2.2 - Ir para a pasta do programa

Na janela preta, digite este comando e aperte ENTER:

```
cd "C:\Users\Rafael Castro\Downloads\files"
```

Você deve ver algo como:
```
PS C:\Users\Rafael Castro\Downloads\files>
```

## 2.3 - Verificar se o Git está instalado

Digite este comando:

```
git --version
```

Se mostrar um número (como `git version 2.42.0`) = Git está instalado ✅

Se não funcionar, você precisa instalar Git:
1. Ir para `https://git-scm.com`
2. Clicar em "Download"
3. Executar o instalador
4. Deixar tudo "padrão" e clicar "Next" várias vezes

## 2.4 - Configurar Git com seu nome e email

Na janela preta, digite DOIS comandos (um de cada vez):

**Comando 1:**
```
git config --global user.name "Seu Nome Aqui"
```

Substitua `"Seu Nome Aqui"` pelo seu nome de verdade. Por exemplo:
```
git config --global user.name "Rafael Castro"
```

**Comando 2:**
```
git config --global user.email "seu@email.com"
```

Substitua `"seu@email.com"` pelo seu email. Por exemplo:
```
git config --global user.email "rafaelhmcastro@gmail.com"
```

## 2.5 - Criar repositório local

Digite este comando na janela preta:

```
git init
```

Você verá algo como:
```
Initialized empty Git repository in C:\Users\Rafael Castro\Downloads\files\.git
```

## 2.6 - Adicionar todos os arquivos

Digite este comando:

```
git add .
```

(Esse comando pega TODOS os arquivos da pasta)

## 2.7 - Fazer um "snapshot" (salvar estado)

Digite este comando:

```
git commit -m "Primeiro commit - programa pronto para Render"
```

Você verá algo como:
```
[main (root-commit) abc1234] Primeiro commit - programa pronto para Render
 15 files changed, 2000 insertions(+)
```

## 2.8 - Criar repositório no GitHub

1. **Abra GitHub** (https://github.com)
2. **Clique no ícone do seu perfil** (canto superior direito)
3. **Clique em "Your repositories"**
4. **Clique no botão verde "New"**

## 2.9 - Preencher informações do repositório

Uma página abrirá pedindo informações:

**Repository name:**
- Digite um nome (por exemplo: `cabos-app`, `sistema-eletrico`, `meu-programa`)

**Description:** (opcional)
- Digite uma descrição (por exemplo: `Sistema de cálculo de cabos NBR 5410`)

**Public ou Private:**
- Escolha **"Public"** (assim qualquer um pode ver)

**Clique em "Create repository"**

## 2.10 - Conectar sua pasta com GitHub

GitHub vai mostrar alguns comandos. Você vai ver algo como:

```
git remote add origin https://github.com/seu-usuario/seu-repositorio.git
git branch -M main
git push -u origin main
```

Na janela preta (PowerShell), digite estes comandos um por um:

**Comando 1:**
```
git remote add origin https://github.com/seu-usuario/seu-repositorio.git
```

(Substitua `seu-usuario` pelo seu nome de usuário do GitHub e `seu-repositorio` pelo nome que você escolheu)

**Exemplo real:**
```
git remote add origin https://github.com/rafael-castros/cabos-app.git
```

**Comando 2:**
```
git branch -M main
```

**Comando 3:**
```
git push -u origin main
```

Ele pedirá seu **email do GitHub** e **token de acesso**:

### ⚠️ PARA O TOKEN:

1. GitHub pedirá um "token" (uma chave de segurança)
2. **Não é sua senha!**
3. **Você precisa criar um token:**

**Como criar o token:**

1. **Abra GitHub** e clique na sua foto de perfil
2. **Clique em "Settings"**
3. **Clique em "Developer settings"** (na esquerda)
4. **Clique em "Personal access tokens"**
5. **Clique em "Tokens (classic)"**
6. **Clique no botão "Generate new token"**
7. **Clique em "Generate new token (classic)"**

Na página que abriu:

8. **Note**: Digite um nome (por exemplo: `github-token`)
9. **Expiration**: Escolha `No expiration` (sem vencimento)
10. **Selects scopes**: Clique em `repo` (para ter acesso ao repositório)
11. **Clique em "Generate token"**

GitHub mostrará um código long (tipo: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxx`)

12. **COPIE ESTE CÓDIGO** (Ctrl+C)
13. **Guarde este código em um lugar seguro!** Você vai precisar dele

Agora:

14. **Volte para o PowerShell**
15. **Cole o token** quando ele pedir
16. **Aperte ENTER**

Você verá:
```
Enumerating objects: XX, done.
Counting objects: 100% (XX/XX), done.
Writing objects: 100% (XX/XX), done.

Branch 'main' set up to track remote branch 'main' from 'origin'.
```

✅ **Seu código foi enviado para GitHub!**

---

# PASSO 3: Criar conta no Render

Render é um "servidor na nuvem" onde sua aplicação vai rodar 24/7.

## 3.1 - Ir para o site do Render

1. **Abra o navegador**
2. **Digite:** `https://render.com`
3. **Aperte ENTER**

Você verá um site bonito com cores azul e roxo.

## 3.2 - Clicar em "Sign up"

Procure pelo botão **"Sign up"** no topo direito
- **Clique nele**

## 3.3 - Escolher forma de registro

Render vai oferecer várias opções:
- Google
- GitHub ← **ESCOLHA ESSA!**
- GitLab

**Clique em "GitHub"**

## 3.4 - Autorizar Render no GitHub

GitHub pedirá permissão para Render acessar seus repositórios.

1. **Clique em "Authorize Render"**
2. **Digite sua senha do GitHub** (a que você criou antes)
3. **Clique em "Confirm"**

✅ **Sua conta Render foi criada!**

Render abrirá seu dashboard (painel de controle).

---

# PASSO 4: Conectar GitHub com Render

Agora você vai dizer ao Render: "Pegue meu código que está no GitHub e faça funcionar!"

## 4.1 - Ir para criar novo serviço

No dashboard do Render:

1. **Clique no botão "New +"** (canto superior direito)
2. **Clique em "Web Service"**

Uma página abrirá.

## 4.2 - Selecionar repositório

Você verá uma lista dos seus repositórios GitHub.

1. **Procure pelo repositório que você criou** (por exemplo: `cabos-app`)
2. **Clique no botão "Select"** ao lado dele

Se não aparecer na lista:
- Clique em "Connect account" para reconectar com GitHub
- Ou clique em "Refresh" para atualizar a lista

## 4.3 - Preencher informações do serviço

Uma página com muitas opções abrirá. Aqui está o que fazer:

### **Name** (Nome do serviço)
- Deixe como está ou digite um nome
- Por exemplo: `cabos-app`, `sistema-eletrico`

### **Region** (Região/Local do servidor)
- Escolha **`Ohio (us-east)`** (é gratuito)

### **Branch** (Ramificação do código)
- Deixe como **`main`**

### **Root Directory** (Diretório raiz)
- Deixe **vazio**

### **Runtime** (Linguagem/Ambiente)
- Render vai detectar automaticamente como **Python**
- Deixe assim mesmo

### **Build Command** (Comando para preparar)
- Deixe em branco
- Render vai ler do arquivo `render.yaml` automaticamente

### **Start Command** (Comando para iniciar)
- Deixe em branco
- Render vai ler do arquivo `render.yaml` automaticamente

## 4.4 - Descer até "Environment"

**Aqui você pode deixar como está!**

Render vai usar as variáveis do arquivo `render.yaml` automaticamente.

## 4.5 - Clicar em "Create Web Service"

Procure pelo botão **"Create Web Service"** (geralmente em roxo)

**Clique nele!**

---

# PASSO 5: Fazer o programa rodar

Agora Render vai pegar seu código e fazer funcionar!

## 5.1 - Acompanhar o deploy

Render vai mostrar uma página com um vidro chamado **"Logs"** (Registros).

Você verá mensagens aparecendo, tipo:

```
Building application...
Building container...
Installing dependencies...
```

Deixe ele trabalhar! Vai levar alguns minutos (3 a 5 minutos).

## 5.2 - Procurar a mensagem de sucesso

Enquanto o Render trabalha, procure por uma mensagem que diz:

```
Application running on http://0.0.0.0:8000
```

Quando ver essa mensagem = **Sucesso!** ✅

## 5.3 - Se der erro

Se aparecer `ERROR` ou `FAILED`:

1. **Clique na aba "Logs"**
2. **Procure pela mensagem de erro**
3. **Tire uma screenshot e envie para Claude**

Geralmente os erros são:
- Versão do Python errada (solução: atualizar `requirements.txt`)
- Falta de dependência (solução: adicionar ao `requirements.txt`)
- Erro no código (solução: corrigir o arquivo Python)

## 5.4 - Esperar aparecer a URL

Depois que aparecer a mensagem de sucesso, em cima da página Render vai mostrar:

```
https://seu-servico.onrender.com
```

Essa é a URL do seu programa! 🎉

---

# PASSO 6: Testar se funcionou

Agora vamos testar se o programa está mesmo funcionando!

## 6.1 - Abrir a URL

1. **Clique na URL** que apareceu (ou copie e cole no navegador)
2. **Exemplo:** `https://cabos-app.onrender.com`
3. **Aperte ENTER**

## 6.2 - Esperar carregar

A primeira vez leva mais tempo (até 30-60 segundos) porque o servidor está "acordando".

Você verá uma tela branca ou a mensagem "Loading..."

Aguarde! 🕐

## 6.3 - Ver o programa rodando

Quando carregar, você deve ver:

- A tela principal do Sistema de Cálculo de Cabos
- Os menus funcionando
- Os botões respondendo

✅ **Sucesso! Seu programa está na internet!**

---

## 6.4 - Testar as funcionalidades

Agora você pode testar tudo:

**1. Criar um novo Projeto**
- Clique em "Novo Projeto"
- Digite um nome
- Clique em "Salvar"

**2. Adicionar Equipamento**
- Escolha o projeto
- Clique em "Novo Equipamento"
- Preencha os dados
- Clique em "Salvar"

**3. Exportar Relatório**
- Clique em "Relatórios"
- Clique em "Exportar Excel"
- O arquivo baixará no seu computador

✅ **Tudo funcionando!**

---

## 📊 RESUMO DO PROCESSO

```
PASSO 1: Criar conta GitHub
         ↓
PASSO 2: Enviar código para GitHub (git push)
         ↓
PASSO 3: Criar conta Render
         ↓
PASSO 4: Conectar GitHub com Render
         ↓
PASSO 5: Render faz o deploy (build + start)
         ↓
PASSO 6: Testar a URL fornecida
         ↓
        ✅ PROGRAMA NA INTERNET! 🎉
```

---

## 🔄 E QUANDO VOCÊ QUER ATUALIZAR O PROGRAMA?

Depois que está tudo pronto, se você quer fazer mudanças no programa:

**1. Modifique os arquivos** no seu computador

**2. No PowerShell, digitar:**
```
git add .
git commit -m "Descrição da mudança"
git push
```

**3. Render detecta a mudança e faz o redeploy automaticamente!**

Você vê na página do Render "Building..." novamente, e em poucos minutos a atualização está ao vivo! 🚀

---

## 🆘 DÚVIDAS FREQUENTES

### "Meu programa dormiu e está lento"

**É normal!** No plano gratuito do Render, o servidor "dorme" depois de 15 minutos sem uso.

Solução:
- Primeira requisição demora 30-60 segundos (acordar o servidor)
- Depois fica rápido

### "Quero meu próprio domínio (ex: meusite.com)"

Render permite adicionar domínio customizado:
1. Clique em "Custom Domain" no painel
2. Digite seu domínio
3. Siga as instruções de DNS

(Mas isso é avançado, é opcional!)

### "Onde meus dados estão armazenados?"

No banco de dados PostgreSQL que Render criou automaticamente!

- Todos os seus projetos, equipamentos e cálculos estão guardados lá
- Render faz backups automáticos
- Seus dados estão seguros!

### "Quanto custa?"

**GRÁTIS!** 🎉

Plano gratuito do Render inclui:
- ✅ 1 aplicação web
- ✅ 250 MB de banco de dados PostgreSQL
- ✅ Uptime de ~99%
- ✅ Domínio automático `.onrender.com`

Se quiser remover o "dormir do servidor" (sempre ligado), aí sim custa $7/mês.

### "Posso compartilhar meu programa com outras pessoas?"

**Sim!** 🎉

Basta enviar a URL:
```
https://seu-app.onrender.com
```

Qualquer pessoa com o link pode usar seu programa no navegador!

Não precisa instalar nada, não precisa de Python, é só abrir o link.

---

## ✅ CHECKLIST FINAL

Antes de começar:
- [ ] Email criado
- [ ] Pasta do programa em `C:\Users\Rafael Castro\Downloads\files`

Passo 1:
- [ ] Conta GitHub criada
- [ ] Email confirmado no GitHub

Passo 2:
- [ ] Git instalado e configurado
- [ ] Código enviado para GitHub (git push)
- [ ] Token do GitHub criado e guardado

Passo 3:
- [ ] Conta Render criada com GitHub

Passo 4:
- [ ] Repositório conectado no Render

Passo 5:
- [ ] Deploy concluído (visto a mensagem de sucesso)

Passo 6:
- [ ] URL do programa funcionando
- [ ] Testou criar projeto
- [ ] Testou exportar relatório

---

## 🎉 PARABÉNS!

**Seu programa agora está na INTERNET! 🌐**

Você pode:
- ✅ Acessar de qualquer computador
- ✅ Compartilhar o link com outras pessoas
- ✅ Usar 24/7 sem deixar seu PC ligado
- ✅ Atualizar o código a qualquer hora

---

## 📞 PRECISA DE AJUDA?

Se algo não funcionou ou você tem dúvidas:

1. **Procure pela mensagem de erro** na aba "Logs" do Render
2. **Tire uma screenshot** da mensagem de erro
3. **Envie para Claude**

Claude vai ajudar a resolver! 💪

---

**Boa sorte! 🚀**
