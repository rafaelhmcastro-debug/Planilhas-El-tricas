const TelaProjetos = (() => {
  async function render(el) {
    const projetos = await Api.listarProjetos();
    State.setProjetos(projetos);
    const ativo = State.getProjetoAtivo();
    el.innerHTML = `
      <div class="card">
        <div class="toolbar">
          <h2 style="margin:0">Projetos</h2>
          <div class="spacer"></div>
          <button class="btn" id="btn-novo-projeto">+ Novo projeto</button>
        </div>
        <div class="wrap-table">
          <table class="grid">
            <thead><tr><th>Número</th><th>Nome</th><th>Cliente</th><th>Revisão</th><th>Criado em</th><th>Ações</th></tr></thead>
            <tbody>
              ${projetos.length ? projetos.map((p) => linha(p, ativo)).join("") : `<tr><td colspan="6" class="vazio">Nenhum projeto cadastrado. Clique em "+ Novo projeto".</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    `;
    el.querySelector("#btn-novo-projeto").addEventListener("click", () => abrirForm());
    el.querySelectorAll("[data-abrir]").forEach((b) => b.addEventListener("click", async () => {
      const p = projetos.find((x) => x.id === Number(b.dataset.abrir));
      State.setProjetoAtivo(p);
      await App.recarregarProjetosERender();
      App.irPara("equipamentos");
    }));
    el.querySelectorAll("[data-editar]").forEach((b) => b.addEventListener("click", () => abrirForm(projetos.find((x) => x.id === Number(b.dataset.editar)))));
    el.querySelectorAll("[data-excluir]").forEach((b) => b.addEventListener("click", () => excluir(Number(b.dataset.excluir))));
  }

  function linha(p, ativo) {
    const ehAtivo = ativo && ativo.id === p.id;
    return `<tr>
      <td><strong>${Util.esc(p.numero_projeto)}</strong> ${ehAtivo ? '<span class="badge info">ativo</span>' : ""}</td>
      <td>${Util.esc(p.nome_projeto)}</td>
      <td>${Util.esc(p.cliente || "-")}</td>
      <td>${Util.esc(p.revisao || "-")}</td>
      <td>${p.data_criacao ? new Date(p.data_criacao).toLocaleDateString("pt-BR") : "-"}</td>
      <td class="acoes-col">
        <button class="link" data-abrir="${p.id}">abrir</button> ·
        <button class="link" data-editar="${p.id}">editar</button> ·
        <button class="link perigo" data-excluir="${p.id}">excluir</button>
      </td>
    </tr>`;
  }

  function abrirForm(p) {
    const editando = !!p;
    Util.abrirModal(`
      ${Util.cabecalhoModal(editando ? "Editar projeto" : "Novo projeto")}
      <form id="form-projeto">
        <div class="form-grid">
          <div class="campo">
            <label>Número do projeto *</label>
            <input name="numero_projeto" placeholder="9999-99-9999" pattern="\\d{4}-\\d{2}-\\d{4}" required value="${editando ? Util.esc(p.numero_projeto) : ""}">
            <small class="ajuda">Formato obrigatório: 9999-99-9999 (somente números)</small>
          </div>
          <div class="campo"><label>Nome do projeto *</label><input name="nome_projeto" required value="${editando ? Util.esc(p.nome_projeto) : ""}"></div>
          <div class="campo"><label>Cliente</label><input name="cliente" value="${editando ? Util.esc(p.cliente || "") : ""}"></div>
          <div class="campo"><label>Revisão</label><input name="revisao" value="${editando ? Util.esc(p.revisao || "Rev. 0") : "Rev. 0"}"></div>
          <div class="campo span2"><label>Descrição</label><textarea name="descricao" rows="2">${editando ? Util.esc(p.descricao || "") : ""}</textarea></div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn secundario" data-fechar>Cancelar</button>
          <button type="submit" class="btn">Salvar</button>
        </div>
      </form>
    `, (root) => {
      root.querySelector("#form-projeto").addEventListener("submit", async (e) => {
        e.preventDefault();
        const obj = Util.formToObj(e.target);
        try {
          const salvo = editando ? await Api.atualizarProjeto(p.id, obj) : await Api.criarProjeto(obj);
          Util.fecharModal();
          Util.toast("Projeto salvo.", "ok");
          if (!editando) State.setProjetoAtivo(salvo);
          await App.recarregarProjetosERender();
          App.irPara("projetos");
        } catch (err) { Util.erro(err); }
      });
    });
  }

  async function excluir(id) {
    if (!Util.confirmar("Excluir este projeto e TODOS os seus dados (equipamentos, cabos, eletrodutos)? Esta ação não pode ser desfeita.")) return;
    try {
      await Api.removerProjeto(id);
      Util.toast("Projeto excluído.", "ok");
      if (State.getProjetoAtivo() && State.getProjetoAtivo().id === id) State.setProjetoAtivo(null);
      await App.recarregarProjetosERender();
      App.irPara("projetos");
    } catch (err) { Util.erro(err); }
  }

  return { render };
})();
