const App = (() => {
  async function init() {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      window.location.href = '/login.html';
      return;
    }

    try {
      await carregarProjetos();
    } catch (e) {
      document.getElementById("conteudo").innerHTML = `<div class="alerta-box">Não foi possível conectar ao servidor: ${Util.esc(e.message)}</div>`;
      return;
    }
    renderTopbar();
    await renderTabs();
    await irPara(State.getProjetoAtivo() ? "equipamentos" : "projetos");
  }

  async function carregarProjetos() {
    const lista = await Api.listarProjetos();
    State.setProjetos(lista);
    let salvoId = null;
    try { salvoId = Number(localStorage.getItem("projeto_ativo_id")); } catch (e) { /* ignore */ }
    const atual = State.getProjetoAtivo();
    const alvo = lista.find((p) => p.id === (atual ? atual.id : salvoId));
    State.setProjetoAtivo(alvo || null);
  }

  function renderTopbar() {
    const el = document.getElementById("projeto-ativo");
    const projetos = State.getProjetos();
    const ativo = State.getProjetoAtivo();
    el.innerHTML = `
      <label style="font-size:12.5px;opacity:.85">Projeto ativo:</label>
      <select id="sel-projeto">
        <option value="">— selecione um projeto —</option>
        ${projetos.map((p) => `<option value="${p.id}" ${ativo && ativo.id === p.id ? "selected" : ""}>${Util.esc(p.numero_projeto)} — ${Util.esc(p.nome_projeto)}</option>`).join("")}
      </select>
      ${ativo ? `<span class="tag">${Util.esc(ativo.revisao || "")}</span>` : ""}
      <button id="btn-logout" style="margin-left: auto; padding: 6px 12px; background: #ef4444; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Sair</button>
    `;
    document.getElementById("sel-projeto").addEventListener("change", (e) => {
      const id = Number(e.target.value);
      const p = projetos.find((x) => x.id === id) || null;
      State.setProjetoAtivo(p);
      renderTopbar();
      irPara(p ? "equipamentos" : "projetos");
    });
    document.getElementById("btn-logout").addEventListener("click", () => {
      if (confirm("Tem certeza que deseja sair?")) {
        localStorage.removeItem('auth_token');
        window.location.href = '/login.html';
      }
    });
  }

  async function renderTabs() {
    const nav = document.getElementById("tabs");
    const ativa = State.getTelaAtiva();
    const ativo = State.getProjetoAtivo();

    let usuarioRole = null;
    try {
      const token = localStorage.getItem('auth_token');
      if (token) {
        const resp = await fetch('/api/auth/perfil', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resp.ok) {
          const user = await resp.json();
          usuarioRole = user.role;
        }
      }
    } catch (e) { /* ignore */ }

    nav.innerHTML = State.TELAS
      .filter(t => !t.apenasAdmin || usuarioRole === 'admin')
      .map((t) => `
      <button data-tela="${t.id}" class="${t.id === ativa ? "ativo" : ""}" ${t.exigeProjeto && !ativo ? "disabled title='Selecione um projeto primeiro'" : ""}>
        ${t.label}
      </button>
    `).join("");
    nav.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => irPara(b.dataset.tela)));
  }

  async function irPara(telaId) {
    const tela = State.TELAS.find((t) => t.id === telaId) || State.TELAS[0];
    if (tela.exigeProjeto && !State.getProjetoAtivo()) {
      Util.toast("Selecione ou crie um projeto para continuar.", "erro");
      telaId = "projetos";
    }
    State.setTelaAtiva(telaId);
    await renderTabs();
    const conteudo = document.getElementById("conteudo");
    conteudo.innerHTML = '<div class="vazio">Carregando…</div>';
    try {
      const modulos = {
        projetos: TelaProjetos, equipamentos: TelaEquipamentos, infraestrutura: TelaInfraestrutura,
        cabos: TelaCabos, cargas: TelaCargas, relatorios: TelaRelatorios, config: TelaConfig,
        admin: TelaAdmin,
      };
      await modulos[telaId].render(conteudo);
    } catch (e) {
      conteudo.innerHTML = `<div class="alerta-box">Erro ao carregar a tela: ${Util.esc(e.message)}</div>`;
      console.error(e);
    }
  }

  async function recarregarProjetosERender() {
    await carregarProjetos();
    renderTopbar();
    await renderTabs();
  }

  return { init, irPara, recarregarProjetosERender };
})();

document.addEventListener("DOMContentLoaded", App.init);
