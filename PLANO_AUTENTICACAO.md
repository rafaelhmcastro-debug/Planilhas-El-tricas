# 🔐 Plano: Sistema de Autenticação e Administração

## 📋 Visão Geral

Sistema de login com aprovação de usuários e painel administrativo para:
- ✅ Autenticação (username, senha, email, empresa)
- ✅ Aprovação de novos usuários pelo admin
- ✅ Painel de controle administrativo
- ✅ Logs de acesso com relatórios
- ✅ Rastreamento de ações (criar/alterar projetos)

---

## 🏗️ Arquitetura

### 1. Banco de Dados (PostgreSQL)

#### Tabela: `usuarios`
```sql
- id (PK)
- username (UNIQUE)
- email (UNIQUE)
- senha_hash
- empresa
- ativo (true/false)
- aprovado_por (FK admin)
- data_criacao
- data_aprovacao
- role (admin/user)
```

#### Tabela: `solicitacoes_usuario`
```sql
- id (PK)
- username
- email
- empresa
- senha_hash
- status (pendente/aprovado/rejeitado)
- data_solicitacao
- data_decisao
- decidido_por (FK admin)
- motivo_rejeicao
```

#### Tabela: `access_logs`
```sql
- id (PK)
- usuario_id (FK)
- ip_address
- data_hora
- acao (login/logout/criar_projeto/alterar_projeto/etc)
- projeto_id (FK - NULL se não houver)
- detalhes (JSON com informações)
```

#### Tabela: `sessoes`
```sql
- id (PK)
- usuario_id (FK)
- token (JWT)
- criada_em
- expira_em
- ativa
```

---

## 🎯 Funcionalidades Principais

### A. Tela de Login
- [ ] Form com username + senha
- [ ] Validação
- [ ] Mensagens de erro
- [ ] Link "Criar conta" → tela de cadastro

### B. Tela de Cadastro
- [ ] Form: username, email, senha, confirmar senha, empresa
- [ ] Validações (email válido, senha forte, etc)
- [ ] Salva como "solicitação pendente"
- [ ] Mensagem: "Aguarde aprovação do administrador"

### C. Painel Admin
#### C.1 - Dashboard
- [ ] Total de usuários ativos
- [ ] Total de acessos hoje
- [ ] Usuários online agora
- [ ] Solicitações pendentes (com notificação)

#### C.2 - Solicitações de Usuários
- [ ] Lista de solicitações pendentes
- [ ] Card com: username, email, empresa, data
- [ ] Botão "Aprovar" (verde)
- [ ] Botão "Rejeitar" (vermelho)
- [ ] Campo de motivo de rejeição (opcional)

#### C.3 - Gerenciar Usuários
- [ ] Lista de todos os usuários
- [ ] Info: username, email, empresa, data_acesso_último
- [ ] Status (ativo/inativo)
- [ ] Botão "Desativar"
- [ ] Botão "Ver logs"

#### C.4 - Logs de Acesso
- [ ] Filtros: data, usuário, tipo de ação
- [ ] Tabela: data_hora | usuário | ação | projeto | IP
- [ ] Botão "Exportar CSV/PDF"
- [ ] Gráfico: acessos por dia (últimos 30 dias)

### D. Middleware de Autenticação
- [ ] Verificar token JWT
- [ ] Registrar cada acesso em access_logs
- [ ] Detectar IP do usuário
- [ ] Verificar ativo/aprovado

---

## 📁 Mudanças no Código

### Arquivos a Criar

```
cabos-app/
├── app/
│   ├── models/
│   │   ├── usuario.py          (NEW)
│   │   ├── access_log.py        (NEW)
│   │   └── solicitacao.py       (NEW)
│   ├── routers/
│   │   ├── auth.py              (NEW)
│   │   ├── admin.py             (NEW)
│   │   └── logs.py              (NEW)
│   ├── schemas/
│   │   ├── usuario_schema.py    (NEW)
│   │   └── login_schema.py      (NEW)
│   ├── utils/
│   │   ├── auth.py              (NEW - JWT, hashing)
│   │   ├── email.py             (NEW - enviar emails)
│   │   └── logs.py              (NEW - registrar ações)
│   ├── middleware/
│   │   └── auth_middleware.py   (NEW)
│   └── main.py                  (MODIFY)
├── static/
│   ├── login.html               (NEW)
│   ├── cadastro.html            (NEW)
│   ├── admin/
│   │   ├── dashboard.html       (NEW)
│   │   ├── solicitacoes.html    (NEW)
│   │   ├── usuarios.html        (NEW)
│   │   └── logs.html            (NEW)
│   ├── css/
│   │   └── auth.css             (NEW)
│   └── js/
│       ├── auth.js              (NEW)
│       └── admin.js             (NEW)
```

### Arquivos a Modificar

```
cabos-app/
├── app/
│   ├── models.py                (ADD: Usuario, AccessLog)
│   ├── database.py              (ADD: Base.metadata.create_all)
│   ├── main.py                  (ADD: middleware, rota /admin)
│   └── routers/
│       └── projetos.py          (MODIFY: registrar ações em logs)
```

---

## 🔐 Segurança

### Implementar

- [ ] **Hashing de Senha**: bcrypt (não salvar em plain text)
- [ ] **JWT Token**: expires em 24 horas
- [ ] **HTTPS Only**: cookies com flag secure
- [ ] **CORS**: apenas origem do seu app
- [ ] **Rate Limiting**: máx 5 tentativas de login
- [ ] **SQL Injection**: usar ORM (SQLAlchemy)
- [ ] **CSRF Token**: em formulários
- [ ] **Validação de Email**: enviar link de confirmação

---

## 📊 Fluxo de Usuário

### Novo Usuário

```
1. Acessa /login
2. Clica "Criar Conta"
3. Preenche formulário (username, email, senha, empresa)
4. Submete
5. Entra como "solicitação pendente"
6. Recebe email: "Aguarde aprovação"
7. Admin vê em "Solicitações"
8. Admin aprova
9. Email: "Conta aprovada! Faça login"
10. Usuário faz login
11. Acesso ao sistema registrado em logs
```

### Admin

```
1. Faz login (único usuário inicial com role=admin)
2. Vê dashboard com estatísticas
3. Vai para "Solicitações"
4. Aprova/Rejeita usuários
5. Vai para "Logs"
6. Filtra por data/usuário
7. Exporta relatório
```

---

## 🎨 Design das Telas

### Login
```
┌─────────────────────────────┐
│  Planilhas Elétricas        │
│                             │
│  ┌───────────────────────┐  │
│  │ 🔐 Login              │  │
│  ├───────────────────────┤  │
│  │ Usuário:              │  │
│  │ [____________]        │  │
│  │ Senha:                │  │
│  │ [____________]        │  │
│  │ [✓] Lembrar-me        │  │
│  │ [Entrar]              │  │
│  │ Não tem conta?        │  │
│  │ [Criar conta]         │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

### Cadastro
```
┌─────────────────────────────┐
│  Criar Conta                │
├─────────────────────────────┤
│ Usuário:   [____________]   │
│ Email:     [____________]   │
│ Empresa:   [____________]   │
│ Senha:     [____________]   │
│ Confirmar: [____________]   │
│ [Cadastrar] [Voltar]        │
└─────────────────────────────┘
```

### Admin - Dashboard
```
┌─────────────────────────────────────┐
│  Admin > Dashboard                  │
├─────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐     │
│ │ 👥 Usuários │ │ 📊 Acessos  │     │
│ │     42      │ │    1.2K     │     │
│ └─────────────┘ └─────────────┘     │
│ ┌─────────────┐ ┌─────────────┐     │
│ │ 🟢 Online   │ │ ⏳ Pendente │     │
│ │      8      │ │      3      │     │
│ └─────────────┘ └─────────────┘     │
│                                     │
│ [Solicitações] [Usuários] [Logs]    │
└─────────────────────────────────────┘
```

### Admin - Solicitações
```
┌─────────────────────────────────────┐
│  Admin > Solicitações (3)           │
├─────────────────────────────────────┤
│ ┌───────────────────────────────┐   │
│ │ 👤 joao_silva                 │   │
│ │ 📧 joao@email.com             │   │
│ │ 🏢 Empresa XYZ                │   │
│ │ 📅 10/09/2026                 │   │
│ │ [✓ Aprovar] [✗ Rejeitar]      │   │
│ └───────────────────────────────┘   │
│ ... mais solicitações ...            │
└─────────────────────────────────────┘
```

### Admin - Logs
```
┌──────────────────────────────────────────┐
│  Admin > Logs de Acesso                  │
├──────────────────────────────────────────┤
│ Filtros:                                 │
│ Data: [____] a [____]                    │
│ Usuário: [________________]              │
│ Ação: [Todas ▼]                          │
│ [Filtrar] [Exportar CSV] [Exportar PDF]  │
├──────────────────────────────────────────┤
│ Data/Hora    │ Usuário │ Ação           │
├──────────────┼─────────┼────────────────┤
│ 15/09 14:23  │ joao    │ LOGIN          │
│ 15/09 14:25  │ joao    │ Criar Projeto  │
│ 15/09 14:30  │ maria   │ LOGIN          │
│ ...          │ ...     │ ...            │
└──────────────────────────────────────────┘
```

---

## 📅 Cronograma de Implementação

**Fase 1: Backend Autenticação** (Etapa 1)
- [ ] Modelos de banco (Usuario, AccessLog)
- [ ] Rotas de auth (login, cadastro, logout)
- [ ] JWT e hashing de senha
- [ ] Middleware de autenticação

**Fase 2: Frontend Login** (Etapa 2)
- [ ] Tela de login
- [ ] Tela de cadastro
- [ ] Validações

**Fase 3: Painel Admin** (Etapa 3)
- [ ] Dashboard
- [ ] Solicitações de usuários
- [ ] Gerenciar usuários

**Fase 4: Logs e Relatórios** (Etapa 4)
- [ ] Sistema de logs
- [ ] Tela de logs
- [ ] Exportação CSV/PDF

---

## ✅ Resumo do Que Será Implementado

| Item | Descrição | Status |
|------|-----------|--------|
| 🔐 Autenticação | Login/Logout com JWT | Fase 1 |
| 📝 Cadastro | Com aprovação admin | Fase 1 |
| 👤 Perfis | Admin/User | Fase 1 |
| 📊 Dashboard Admin | Estatísticas | Fase 3 |
| ✅ Solicitações | Aprovar/Rejeitar usuários | Fase 3 |
| 📋 Logs | Registrar todos os acessos | Fase 4 |
| 📈 Relatórios | Exportar dados | Fase 4 |
| 🔒 Segurança | Bcrypt, JWT, CSRF | Todas as fases |

---

## 🚀 Começar?

Responda:

1. **Começar pela Fase 1 (Backend)?** 
   - Criar modelos, rotas, autenticação

2. **Ou quer um resumo primeiro?**
   - Explicar a arquitetura com mais detalhes

**Recomendação**: Começar pela **Fase 1** agora mesmo!

---

**Próximo passo**: Vou implementar a Fase 1 (Backend) se você aprovar! 🚀
