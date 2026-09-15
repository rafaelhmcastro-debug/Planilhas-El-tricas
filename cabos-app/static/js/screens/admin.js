const TelaAdmin = (() => {
  async function render(container) {
    const usuario = await obterUsuarioAtual();
    if (usuario.role !== 'admin') {
      container.innerHTML = '<div class="alerta-box" style="color: red;">Acesso negado. Apenas administradores podem acessar esta página.</div>';
      return;
    }

    container.innerHTML = '<div class="admin-container"><div class="vazio">Carregando dashboard...</div></div>';

    try {
      const dashboard = await fetch('/api/admin/dashboard', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
      }).then(r => r.json());

      container.innerHTML = renderDashboard(dashboard);
      setupEventListeners();
    } catch (e) {
      container.innerHTML = `<div class="alerta-box">Erro ao carregar admin: ${Util.esc(e.message)}</div>`;
      console.error(e);
    }
  }

  function renderDashboard(data) {
    return `
      <div class="admin-container">
        <h2>Dashboard Administrativo</h2>

        <!-- Cards de Estatísticas -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-number">${data.total_usuarios}</div>
            <div class="stat-label">Usuários Totais</div>
          </div>
          <div class="stat-card">
            <div class="stat-number">${data.usuarios_online}</div>
            <div class="stat-label">Usuários Online</div>
          </div>
          <div class="stat-card">
            <div class="stat-number">${data.total_acessos}</div>
            <div class="stat-label">Total de Acessos</div>
          </div>
          <div class="stat-card">
            <div class="stat-number" style="color: #f59e0b;">${data.solicitacoes_pendentes}</div>
            <div class="stat-label">Solicitações Pendentes</div>
          </div>
        </div>

        <!-- Tabs de Navegação -->
        <div class="admin-tabs">
          <button class="admin-tab-btn active" data-tab="solicitacoes">
            Solicitações (${data.solicitacoes_pendentes})
          </button>
          <button class="admin-tab-btn" data-tab="usuarios">
            Usuários
          </button>
          <button class="admin-tab-btn" data-tab="logs">
            Logs de Acesso
          </button>
        </div>

        <!-- Tab: Solicitações -->
        <div id="tab-solicitacoes" class="admin-tab-content active">
          <div class="vazio">Carregando solicitações...</div>
        </div>

        <!-- Tab: Usuários -->
        <div id="tab-usuarios" class="admin-tab-content">
          <div class="vazio">Carregando usuários...</div>
        </div>

        <!-- Tab: Logs -->
        <div id="tab-logs" class="admin-tab-content">
          <div class="vazio">Carregando logs...</div>
        </div>
      </div>
    `;
  }

  function setupEventListeners() {
    document.querySelectorAll('.admin-tab-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        document.querySelectorAll('.admin-tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.admin-tab-content').forEach(c => c.classList.remove('active'));

        e.target.classList.add('active');
        const tab = e.target.dataset.tab;
        document.getElementById(`tab-${tab}`).classList.add('active');

        if (tab === 'solicitacoes') {
          carregarSolicitacoes();
        } else if (tab === 'usuarios') {
          carregarUsuarios();
        } else if (tab === 'logs') {
          carregarLogs();
        }
      });
    });

    carregarSolicitacoes();
  }

  async function carregarSolicitacoes() {
    const container = document.getElementById('tab-solicitacoes');
    container.innerHTML = '<div class="vazio">Carregando...</div>';

    try {
      const response = await fetch('/api/admin/solicitacoes?status_filtro=pendente', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
      });

      if (!response.ok) throw new Error('Erro ao carregar solicitações');

      const solicitacoes = await response.json();

      if (solicitacoes.length === 0) {
        container.innerHTML = '<div class="vazio">Nenhuma solicitação pendente</div>';
        return;
      }

      container.innerHTML = `
        <table class="admin-table">
          <thead>
            <tr>
              <th>Usuário</th>
              <th>Email</th>
              <th>Empresa</th>
              <th>Data Solicitação</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            ${solicitacoes.map(s => `
              <tr>
                <td>${Util.esc(s.username)}</td>
                <td>${Util.esc(s.email)}</td>
                <td>${Util.esc(s.empresa)}</td>
                <td>${new Date(s.data_solicitacao).toLocaleDateString('pt-BR')} ${new Date(s.data_solicitacao).toLocaleTimeString('pt-BR')}</td>
                <td>
                  <button class="btn-aprovar" data-id="${s.id}">✓ Aprovar</button>
                  <button class="btn-rejeitar" data-id="${s.id}">✗ Rejeitar</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;

      document.querySelectorAll('.btn-aprovar').forEach(btn => {
        btn.addEventListener('click', () => abrirDialogoAprovacao(btn.dataset.id, true));
      });

      document.querySelectorAll('.btn-rejeitar').forEach(btn => {
        btn.addEventListener('click', () => abrirDialogoAprovacao(btn.dataset.id, false));
      });
    } catch (e) {
      container.innerHTML = `<div class="alerta-box">Erro ao carregar solicitações: ${Util.esc(e.message)}</div>`;
      console.error(e);
    }
  }

  async function carregarUsuarios() {
    const container = document.getElementById('tab-usuarios');
    container.innerHTML = '<div class="vazio">Carregando...</div>';

    try {
      const response = await fetch('/api/admin/usuarios?limit=100', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
      });

      if (!response.ok) throw new Error('Erro ao carregar usuários');

      const usuarios = await response.json();

      if (usuarios.length === 0) {
        container.innerHTML = '<div class="vazio">Nenhum usuário encontrado</div>';
        return;
      }

      container.innerHTML = `
        <table class="admin-table">
          <thead>
            <tr>
              <th>Usuário</th>
              <th>Email</th>
              <th>Empresa</th>
              <th>Role</th>
              <th>Status</th>
              <th>Data Criação</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            ${usuarios.map(u => `
              <tr>
                <td>${Util.esc(u.username)}</td>
                <td>${Util.esc(u.email)}</td>
                <td>${Util.esc(u.empresa)}</td>
                <td><span class="badge ${u.role === 'admin' ? 'badge-admin' : 'badge-user'}">${u.role}</span></td>
                <td>
                  <span class="badge ${u.ativo && u.aprovado ? 'badge-ativo' : 'badge-inativo'}">
                    ${u.ativo && u.aprovado ? 'Ativo' : u.ativo ? 'Pendente' : 'Desativado'}
                  </span>
                </td>
                <td>${new Date(u.data_criacao).toLocaleDateString('pt-BR')}</td>
                <td>
                  ${u.ativo ? `<button class="btn-desativar" data-id="${u.id}">Desativar</button>` : '<span style="color: #999;">Inativo</span>'}
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;

      document.querySelectorAll('.btn-desativar').forEach(btn => {
        btn.addEventListener('click', () => {
          const id = btn.dataset.id;
          if (confirm('Tem certeza que deseja desativar este usuário?')) {
            desativarUsuario(id);
          }
        });
      });
    } catch (e) {
      container.innerHTML = `<div class="alerta-box">Erro ao carregar usuários: ${Util.esc(e.message)}</div>`;
      console.error(e);
    }
  }

  async function carregarLogs() {
    const container = document.getElementById('tab-logs');
    container.innerHTML = `
      <div class="logs-filtros">
        <input type="text" id="filtro-usuario" placeholder="Filtrar por usuário...">
        <select id="filtro-acao">
          <option value="">Todas as ações</option>
          <option value="login">Login</option>
          <option value="logout">Logout</option>
          <option value="criar_projeto">Criar Projeto</option>
          <option value="alterar_projeto">Alterar Projeto</option>
        </select>
        <button id="btn-filtrar-logs">Filtrar</button>
        <button id="btn-exportar-logs">📥 Exportar CSV</button>
      </div>
      <div class="vazio">Carregando logs...</div>
    `;

    try {
      await atualizarTabelaLogs();

      document.getElementById('btn-filtrar-logs').addEventListener('click', atualizarTabelaLogs);
      document.getElementById('btn-exportar-logs').addEventListener('click', exportarLogs);
    } catch (e) {
      container.innerHTML = `<div class="alerta-box">Erro ao carregar logs: ${Util.esc(e.message)}</div>`;
      console.error(e);
    }
  }

  async function atualizarTabelaLogs() {
    const usuario = document.getElementById('filtro-usuario')?.value || '';
    const acao = document.getElementById('filtro-acao')?.value || '';

    const params = new URLSearchParams();
    if (acao) params.append('acao', acao);

    try {
      const response = await fetch(`/api/admin/logs?${params.toString()}&limit=100`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
      });

      if (!response.ok) throw new Error('Erro ao carregar logs');

      let logs = await response.json();

      if (usuario) {
        logs = logs.filter(l => l.username?.toLowerCase().includes(usuario.toLowerCase()));
      }

      const container = document.getElementById('tab-logs');

      if (logs.length === 0) {
        const html = container.querySelector('.logs-filtros').outerHTML;
        container.innerHTML = html + '<div class="vazio">Nenhum log encontrado</div>';
        document.getElementById('btn-filtrar-logs').addEventListener('click', atualizarTabelaLogs);
        document.getElementById('btn-exportar-logs').addEventListener('click', exportarLogs);
        return;
      }

      const html = `
        ${container.querySelector('.logs-filtros').outerHTML}
        <table class="admin-table">
          <thead>
            <tr>
              <th>Data/Hora</th>
              <th>Usuário</th>
              <th>Ação</th>
              <th>Projeto</th>
              <th>IP Address</th>
              <th>Detalhes</th>
            </tr>
          </thead>
          <tbody>
            ${logs.map(l => `
              <tr>
                <td>${new Date(l.data_hora).toLocaleDateString('pt-BR')} ${new Date(l.data_hora).toLocaleTimeString('pt-BR')}</td>
                <td>${Util.esc(l.username || '—')}</td>
                <td><span class="badge badge-acao">${l.acao}</span></td>
                <td>${l.projeto_id || '—'}</td>
                <td><code>${Util.esc(l.ip_address)}</code></td>
                <td>${l.detalhes ? `<code style="font-size: 11px;">${Util.esc(JSON.stringify(l.detalhes))}</code>` : '—'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;

      container.innerHTML = html;
      document.getElementById('btn-filtrar-logs').addEventListener('click', atualizarTabelaLogs);
      document.getElementById('btn-exportar-logs').addEventListener('click', exportarLogs);
    } catch (e) {
      const container = document.getElementById('tab-logs');
      container.innerHTML = `${container.querySelector('.logs-filtros').outerHTML}<div class="alerta-box">Erro: ${Util.esc(e.message)}</div>`;
    }
  }

  async function abrirDialogoAprovacao(solicitacaoId, aprovar) {
    let motivo = '';
    if (!aprovar) {
      motivo = prompt('Motivo da rejeição (opcional):');
      if (motivo === null) return;
    }

    try {
      const response = await fetch('/api/admin/solicitacoes/aprovar', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          solicitacao_id: parseInt(solicitacaoId),
          aprovar: aprovar,
          motivo_rejeicao: motivo
        })
      });

      const resultado = await response.json();

      if (!response.ok) {
        alert(`Erro: ${resultado.detail || 'Erro ao processar solicitação'}`);
        return;
      }

      alert(resultado.mensagem);
      carregarSolicitacoes();
    } catch (e) {
      alert(`Erro: ${e.message}`);
      console.error(e);
    }
  }

  async function desativarUsuario(usuarioId) {
    try {
      const response = await fetch(`/api/admin/usuarios/${usuarioId}/desativar`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
      });

      const resultado = await response.json();

      if (!response.ok) {
        alert(`Erro: ${resultado.detail || 'Erro ao desativar usuário'}`);
        return;
      }

      alert(resultado.mensagem);
      carregarUsuarios();
    } catch (e) {
      alert(`Erro: ${e.message}`);
      console.error(e);
    }
  }

  async function exportarLogs() {
    try {
      const response = await fetch('/api/admin/logs?limit=10000', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
      });

      if (!response.ok) throw new Error('Erro ao carregar logs');

      const logs = await response.json();

      const csv = [
        ['Data/Hora', 'Usuário', 'Ação', 'Projeto ID', 'IP Address', 'Detalhes'].join(','),
        ...logs.map(l => [
          new Date(l.data_hora).toLocaleString('pt-BR'),
          l.username || '',
          l.acao,
          l.projeto_id || '',
          l.ip_address,
          l.detalhes ? JSON.stringify(l.detalhes) : ''
        ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(','))
      ].join('\n');

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `logs_${new Date().toISOString().split('T')[0]}.csv`);
      link.click();
    } catch (e) {
      alert(`Erro ao exportar: ${e.message}`);
      console.error(e);
    }
  }

  async function obterUsuarioAtual() {
    const response = await fetch('/api/auth/perfil', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
    });
    if (!response.ok) throw new Error('Não autenticado');
    return response.json();
  }

  return { render };
})();
