const TelaPerfil = (() => {
  let usuarioAtual = null;

  async function render(container) {
    container.innerHTML = '<div class="vazio">Carregando perfil...</div>';

    try {
      usuarioAtual = await obterUsuarioAtual();
      container.innerHTML = renderPerfil(usuarioAtual);
      setupEventListeners();
    } catch (e) {
      container.innerHTML = `<div class="alerta-box">Erro ao carregar perfil: ${Util.esc(e.message)}</div>`;
      console.error(e);
    }
  }

  function renderPerfil(usuario) {
    return `
      <div class="perfil-container">
        <div class="perfil-header">
          <h2>Meu Perfil</h2>
          <p class="perfil-subtitle">Gerenciar informações de conta</p>
        </div>

        <div class="perfil-grid">
          <!-- Seção: Informações Pessoais -->
          <div class="perfil-card">
            <h3>📋 Informações Pessoais</h3>
            <div class="info-group">
              <label>Usuário</label>
              <input type="text" value="${Util.esc(usuario.username)}" disabled>
            </div>
            <div class="info-group">
              <label>Email</label>
              <input type="email" value="${Util.esc(usuario.email)}" disabled>
            </div>
            <div class="info-group">
              <label>Empresa</label>
              <input type="text" value="${Util.esc(usuario.empresa)}" disabled>
            </div>
            <div class="info-group">
              <label>Role</label>
              <input type="text" value="${usuario.role === 'admin' ? 'Administrador' : 'Usuário'}" disabled>
            </div>
            <div class="info-group">
              <label>Data de Cadastro</label>
              <input type="text" value="${new Date(usuario.data_criacao).toLocaleDateString('pt-BR')} ${new Date(usuario.data_criacao).toLocaleTimeString('pt-BR')}" disabled>
            </div>
            ${usuario.data_aprovacao ? `
              <div class="info-group">
                <label>Data de Aprovação</label>
                <input type="text" value="${new Date(usuario.data_aprovacao).toLocaleDateString('pt-BR')} ${new Date(usuario.data_aprovacao).toLocaleTimeString('pt-BR')}" disabled>
              </div>
            ` : ''}
          </div>

          <!-- Seção: Segurança -->
          <div class="perfil-card">
            <h3>🔐 Segurança</h3>
            <div class="security-section">
              <h4>Alterar Senha</h4>
              <div class="info-group">
                <label for="senhaAtual">Senha Atual</label>
                <div class="password-wrapper">
                  <input type="password" id="senhaAtual" placeholder="Digite sua senha atual">
                  <button type="button" class="toggle-password-btn" onclick="togglePasswordField('senhaAtual')">👁️</button>
                </div>
              </div>
              <div class="info-group">
                <label for="novaSenha">Nova Senha</label>
                <div class="password-wrapper">
                  <input type="password" id="novaSenha" placeholder="Digite uma nova senha">
                  <button type="button" class="toggle-password-btn" onclick="togglePasswordField('novaSenha')">👁️</button>
                </div>
                <small>Mínimo 8 caracteres</small>
              </div>
              <div class="info-group">
                <label for="confirmarSenha">Confirmar Nova Senha</label>
                <div class="password-wrapper">
                  <input type="password" id="confirmarSenha" placeholder="Confirme a nova senha">
                  <button type="button" class="toggle-password-btn" onclick="togglePasswordField('confirmarSenha')">👁️</button>
                </div>
              </div>
              <div id="senhaError" class="error-message"></div>
              <button id="btn-alterar-senha" class="btn btn-primary">Alterar Senha</button>
              <div id="senhaSucesso" class="success-message hidden"></div>
            </div>
          </div>

          <!-- Seção: Atividade -->
          <div class="perfil-card perfil-card-full">
            <h3>📊 Minha Atividade Recente</h3>
            <div id="atividade-container" class="vazio">Carregando atividade...</div>
          </div>
        </div>
      </div>
    `;
  }

  function setupEventListeners() {
    document.getElementById('btn-alterar-senha').addEventListener('click', alterarSenha);
    carregarAtividade();
  }

  function togglePasswordField(fieldId) {
    const input = document.getElementById(fieldId);
    input.type = input.type === 'password' ? 'text' : 'password';
  }

  async function alterarSenha() {
    const senhaAtual = document.getElementById('senhaAtual').value;
    const novaSenha = document.getElementById('novaSenha').value;
    const confirmarSenha = document.getElementById('confirmarSenha').value;
    const errorEl = document.getElementById('senhaError');
    const successEl = document.getElementById('senhaSucesso');

    errorEl.textContent = '';
    successEl.textContent = '';

    if (!senhaAtual) {
      errorEl.textContent = 'Digite sua senha atual';
      return;
    }

    if (!novaSenha || novaSenha.length < 8) {
      errorEl.textContent = 'Nova senha deve ter no mínimo 8 caracteres';
      return;
    }

    if (novaSenha !== confirmarSenha) {
      errorEl.textContent = 'As novas senhas não conferem';
      return;
    }

    try {
      const response = await fetch('/api/auth/alterar-senha', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          senha_atual: senhaAtual,
          nova_senha: novaSenha
        })
      });

      const resultado = await response.json();

      if (!response.ok) {
        errorEl.textContent = resultado.detail || 'Erro ao alterar senha';
        return;
      }

      successEl.textContent = '✓ Senha alterada com sucesso!';
      successEl.classList.remove('hidden');

      document.getElementById('senhaAtual').value = '';
      document.getElementById('novaSenha').value = '';
      document.getElementById('confirmarSenha').value = '';

      setTimeout(() => {
        successEl.classList.add('hidden');
      }, 3000);
    } catch (e) {
      errorEl.textContent = `Erro ao alterar senha: ${e.message}`;
      console.error(e);
    }
  }

  async function carregarAtividade() {
    try {
      const response = await fetch('/api/auth/minhas-atividades?limit=20', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
      });

      if (!response.ok) throw new Error('Erro ao carregar logs');

      const logs = await response.json();

      const container = document.getElementById('atividade-container');

      if (logs.length === 0) {
        container.innerHTML = '<div class="vazio">Nenhuma atividade registrada</div>';
        return;
      }

      container.innerHTML = `
        <div class="atividade-list">
          ${logs.map(l => `
            <div class="atividade-item">
              <div class="atividade-time">
                ${new Date(l.data_hora).toLocaleDateString('pt-BR')} ${new Date(l.data_hora).toLocaleTimeString('pt-BR')}
              </div>
              <div class="atividade-action">
                <span class="badge badge-acao">${l.acao}</span>
                ${l.projeto_id ? ` Projeto #${l.projeto_id}` : ''}
              </div>
              <div class="atividade-ip">${l.ip_address}</div>
            </div>
          `).join('')}
        </div>
      `;
    } catch (e) {
      document.getElementById('atividade-container').innerHTML = `<div class="alerta-box">Erro ao carregar atividade: ${Util.esc(e.message)}</div>`;
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

function togglePasswordField(fieldId) {
  const input = document.getElementById(fieldId);
  if (input) {
    input.type = input.type === 'password' ? 'text' : 'password';
  }
}
