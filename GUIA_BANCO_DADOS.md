# 🗄️ Guia: Conectar a um Banco de Dados PostgreSQL

## 📋 Índice
1. [Criar banco de dados no Render](#passo-1-criar-banco-de-dados)
2. [Conectar ao serviço web](#passo-2-conectar-ao-serviço)
3. [Testar a conexão](#passo-3-testar-conexão)
4. [Usar dados persistentes](#passo-4-dados-persistentes)

---

## PASSO 1: Criar Banco de Dados

### 1.1 - Ir para o Painel do Render

1. Acesse https://render.com
2. Faça login com sua conta GitHub
3. Clique em **"Dashboard"**

### 1.2 - Criar novo PostgreSQL

No painel:

1. Clique no botão **"New +"** (canto superior direito)
2. Selecione **"PostgreSQL"**

### 1.3 - Preencher Informações

Uma página abrirá com opções:

**Name:** (Nome do banco)
- Digite: `cabos-db` (ou outro nome que quiser)

**Database:** (Nome do banco de dados)
- Deixe vazio (Render preencherá automaticamente)

**User:** (Usuário do banco)
- Deixe vazio (Render criará automaticamente)

**Region:** (Localização)
- Escolha **`Ohio (us-east)`** (mesma região do seu serviço web)

**PostgreSQL Version:**
- Deixe a versão padrão (geralmente a mais recente)

**Pricing Plan:**
- Escolha **`Free`** (plano gratuito)

### 1.4 - Criar o Banco

Clique no botão **"Create Database"** (roxo)

Render vai criar o banco (leva 1-2 minutos). Aguarde aparecer uma tela com as informações de conexão.

---

## PASSO 2: Conectar ao Serviço Web

### 2.1 - Copiar a String de Conexão

Quando o banco for criado, você verá uma tela com:

```
External Database URL: postgresql://user:password@host:port/database
```

**IMPORTANTE:** Não compartilhe essa URL com ninguém! Contém senha!

### 2.2 - Conectar o Banco ao Seu Serviço

1. Acesse o painel do Render
2. Clique no seu serviço **`cabos-app`** (a aplicação web)
3. Clique em **"Environment"**
4. Procure pela variável de ambiente **`DATABASE_URL`**

Se não existir:
1. Clique em **"Add Environment Variable"**
2. **Key:** `DATABASE_URL`
3. **Value:** Cole a URL do banco (postgresql://...)
4. Clique em **"Save"**

Se já existir:
1. Clique em **"Edit"**
2. Cole a nova URL
3. Clique em **"Save"**

### 2.3 - Redeploy Automático

Render vai fazer redeploy automaticamente (leva 2-3 minutos).

Você verá:
```
Redeploying...
Building...
Your service is live 🎉
```

Pronto! Seu programa agora está conectado ao banco de dados! ✅

---

## PASSO 3: Testar Conexão

### 3.1 - Acessar a Aplicação

1. Abra https://planilhas-el-tricas.onrender.com
2. A página deve carregar normalmente

### 3.2 - Criar um Projeto

1. Clique em **"Novo Projeto"**
2. Digite um nome (por exemplo: "Projeto Teste")
3. Clique em **"Salvar"**

Se o projeto for salvo com sucesso, a conexão com o banco está funcionando! ✅

### 3.3 - Verificar Dados no Banco

Para ver os dados armazenados no banco:

1. No painel do Render, clique no banco **`cabos-db`**
2. Clique na aba **"Connect"**
3. Procure por **"PSQL Command"**
4. Copie o comando

No seu terminal/PowerShell:
```bash
psql postgresql://user:password@host:5432/database
```

Depois digite:
```sql
SELECT * FROM projetos;
```

Você verá os projetos que criou! 🎉

---

## PASSO 4: Dados Persistentes

### Dados Salvos Automaticamente

Quando você:
- ✅ Cria um projeto
- ✅ Adiciona equipamento
- ✅ Calcula cabos
- ✅ Exporta relatório

Todos esses dados são **salvos no PostgreSQL** e **persistem para sempre**.

### Backup Automático

Render faz backup automático do banco:
- ✅ Diário
- ✅ Sem custo adicional
- ✅ Armazenado por 7 dias

Você pode restaurar um backup no painel do Render se necessário.

---

## ⚠️ Limites do Plano Gratuito

**Banco de Dados PostgreSQL Free:**
- ✅ Até 1 GB de armazenamento
- ✅ Backups automáticos
- ✅ Sem limite de requisições
- ❌ Não usa sleep (servidor sempre ligado)

**Se precisar de mais:**
- Upgrade para o plano pago ($15/mês)
- Ou usar outro serviço (AWS, Azure, etc)

---

## 🔒 Segurança

### ✅ Boas Práticas

1. **Nunca compartilhe** a URL do banco
2. **Nunca commit** a URL no Git
3. Use variáveis de ambiente (como você está fazendo)
4. Altere a senha periodicamente

### Arquivo `.env` Local

Se quiser testar localmente:

1. Crie um arquivo `.env` na pasta `cabos-app/`:

```
DATABASE_URL=postgresql://user:password@host:port/database
ENVIRONMENT=development
DEBUG=true
```

2. Adicione ao `.gitignore`:

```
.env
.env.local
```

Seu código já lê automaticamente a variável `DATABASE_URL`! ✅

---

## 📝 Resumo

| Passo | O que fazer | Status |
|-------|------------|--------|
| 1 | Criar banco PostgreSQL no Render | ✅ |
| 2 | Copiar URL de conexão | ✅ |
| 3 | Adicionar `DATABASE_URL` no serviço web | ✅ |
| 4 | Render faz redeploy automático | ✅ |
| 5 | Testar criando um projeto | ✅ |
| 6 | Verificar dados no banco | ✅ |

---

## 🎉 Parabéns!

Sua aplicação agora tem **banco de dados em produção**! 

Todos os dados estão salvos e persistem mesmo se:
- ❌ Você desligar seu PC
- ❌ O servidor "dormir" (no plano pago)
- ❌ Você fazer redeploy da aplicação

Os dados estão **seguros e sempre disponíveis** no PostgreSQL do Render! 🚀

---

## 💡 Próximos Passos (Opcional)

### Usar com SQLite Local (desenvolvimento)

Se quiser testar localmente sem banco:

```bash
# Instalar dependências
pip install -r cabos-app/requirements.txt

# Executar localmente
cd cabos-app
uvicorn app.main:app --reload
```

Seu código **detecta automaticamente** e usa SQLite em `cabos.db`.

### Domínio Customizado

Se quiser mudar a URL de `planilhas-el-tricas.onrender.com` para seu próprio domínio:

1. No painel do Render, clique no seu serviço
2. Vá para **"Settings"**
3. Procure por **"Custom Domain"**
4. Siga as instruções

---

## 🆘 Dúvidas Frequentes

### "Meu programa não consegue conectar ao banco"

Verifique:
1. ✅ A variável `DATABASE_URL` está definida no Render
2. ✅ O banco PostgreSQL está **online** (status verde)
3. ✅ Você fez redeploy após adicionar `DATABASE_URL`

### "Perdi os dados"

Se deletou o banco acidentalmente:
1. Crie um novo banco PostgreSQL
2. Copie a nova URL
3. Atualize `DATABASE_URL`
4. Render vai redeploy
5. Dados antigos podem estar em backup (contacte Render)

### "Quanto custa?"

**Plano Free:**
- ✅ 1 Aplicação web
- ✅ 1 Banco PostgreSQL (1GB)
- ✅ Total: **GRÁTIS** 🎉

Se precisar de mais, upgrade individual custa $7-15/mês.

### "Posso usar MySQL em vez de PostgreSQL?"

Sim! Mas precisa mudar:
1. Criar banco MySQL no Render
2. Atualizar `DATABASE_URL`
3. Atualizar driver em `requirements.txt`:

```
# Em vez de psycopg2-binary, use:
mysql-connector-python==8.0.33
# ou
PyMySQL==1.1.0
```

4. Atualizar `database.py` se necessário

Mas **PostgreSQL é recomendado** para produção.

---

**Sucesso com seu banco de dados! 🚀**
