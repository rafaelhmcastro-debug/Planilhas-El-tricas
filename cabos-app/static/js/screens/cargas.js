const TelaCargas = (() => {
  let paineisCache = [];

  async function render(el) {
    const pid = State.getProjetoAtivo().id;
    const [arvore, paineis] = await Promise.all([Api.arvorePaineis(pid), Api.listarPaineis(pid)]);
    paineisCache = paineis;
    el.innerHTML = `
      <div class="card">
        <div class="toolbar">
          <h2 style="margin:0">Cargas e Demanda</h2>
          <div class="spacer"></div>
          <button class="btn" id="btn-novo-painel">+ Novo painel / transformador</button>
        </div>
        <p style="color:var(--cinza);font-size:13px;margin:0 0 6px">
          As cargas são somadas automaticamente pela TAG do painel informada em cada equipamento. Informe em cada painel
          quem o alimenta ("Alimentado por") para que sua demanda seja somada no painel a montante, até o painel TOP.
        </p>
      </div>
      <div id="arvore">${arvore.length ? "" : '<div class="card"><div class="vazio">Nenhum painel/transformador ainda. Informe a TAG do painel nos equipamentos ou cadastre um painel TOP acima.</div></div>'}</div>
    `;
    el.querySelector("#btn-novo-painel").addEventListener("click", () => abrirNovoPainel());
    const cont = el.querySelector("#arvore");
    for (const no of arvore) desenharNo(cont, no, 0);
  }

  function desenharNo(cont, no, nivel) {
    const card = document.createElement("div");
    card.className = `card painel-card nivel-${Math.min(nivel, 3)}`;
    card.innerHTML = painelHtml(no, nivel);
    cont.appendChild(card);
    ligarEventos(card, no.painel);
    for (const filho of no.filhos) desenharNo(cont, filho, nivel + 1);
  }

  function fases(e) {
    let s = `${e.num_fases}F`;
    if (e.possui_neutro) s += "+N";
    if (e.possui_terra) s += "+PE";
    return s;
  }

  function painelHtml(no, nivel) {
    const p = no.painel;
    const outros = paineisCache.filter((x) => x.id !== p.id);
    const ehTop = !p.painel_alimentador_tag;
    return `
      <div class="toolbar">
        <h3 style="margin:0">${nivel > 0 ? "↳ " : ""}${Util.esc(p.tag)} ${ehTop ? '<span class="badge info">TOP</span>' : ""} <span class="badge info">${Util.esc(p.tipo)}</span></h3>
        <div class="spacer"></div>
        <button class="btn pequeno secundario" data-salvar="${p.id}">Salvar alterações</button>
        <button class="btn pequeno perigo" data-excluir-painel="${p.id}">excluir</button>
      </div>
      <div class="form-grid painel-inline" style="margin-bottom:10px">
        <div class="campo"><label>TAG</label><input data-campo="tag" value="${Util.esc(p.tag)}"></div>
        <div class="campo"><label>Tipo</label>
          <select data-campo="tipo">${["painel", "quadro", "CCM", "transformador"].map((t) => `<option ${p.tipo === t ? "selected" : ""}>${t}</option>`).join("")}</select></div>
        <div class="campo"><label>Tensão (V)</label><input data-campo="tensao_v" value="${p.tensao_v}"></div>
        <div class="campo"><label>Fases</label>
          <select data-campo="num_fases">${[1, 2, 3].map((n) => `<option value="${n}" ${(p.num_fases || 3) === n ? "selected" : ""}>${n}F</option>`).join("")}</select></div>
        <div class="campo"><label>Fator de diversidade</label><input data-campo="fator_diversidade" value="${p.fator_diversidade}"></div>
        <div class="campo"><label>Alimentado por (painel a montante)</label>
          <select data-campo="painel_alimentador_tag">
            <option value="">— nenhum (painel TOP) —</option>
            ${outros.map((o) => `<option value="${Util.esc(o.tag)}" ${p.painel_alimentador_tag === o.tag ? "selected" : ""}>${Util.esc(o.tag)}</option>`).join("")}
          </select></div>
      </div>
      <div class="kpi-row">
        <div class="kpi"><div class="valor">${Util.fmt(p.potencia_instalada_kw)}</div><div class="rotulo">P instalada (kW)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(p.potencia_reativa_instalada_kvar)}</div><div class="rotulo">Q instalada (kvar)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(p.demanda_total_kw)}</div><div class="rotulo">Demanda P (kW)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(p.demanda_reativa_kvar)}</div><div class="rotulo">Demanda Q (kvar)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(p.demanda_aparente_kva)}</div><div class="rotulo">Demanda S (kVA)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(p.fator_potencia_calc)}</div><div class="rotulo">cos φ resultante</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(p.corrente_total_a)}</div><div class="rotulo">I alimentador (A)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(p.corrente_instalada_a)}</div><div class="rotulo">Σ In a jusante (A)</div></div>
      </div>
      <div class="wrap-table compacta" style="margin-top:10px">
        <table class="grid">
          <thead><tr><th>Carga</th><th>Descrição</th><th>Fases</th><th class="num">P (kW)</th><th class="num">Q (kvar)</th><th class="num">S (kVA)</th><th class="num">In (A)</th><th class="num">FD</th><th class="num">Pd (kW)</th></tr></thead>
          <tbody>
            ${no.equipamentos.map((e) => `<tr><td>${Util.esc(e.tag)}</td><td>${Util.esc(e.descricao || "-")}</td><td>${fases(e)}</td>
              <td class="num">${Util.fmt(e.potencia_ativa_calc_kw)}</td><td class="num">${Util.fmt(e.potencia_reativa_calc_kvar)}</td>
              <td class="num">${Util.fmt(e.potencia_aparente_calc_kva)}</td><td class="num">${Util.fmt(e.corrente_nominal_a)}</td>
              <td class="num">${Util.fmt(e.fator_demanda)}</td><td class="num">${Util.fmt(e.potencia_demanda_kw)}</td></tr>`).join("")}
            ${no.filhos.map((f) => `<tr class="subtotal"><td>↳ ${Util.esc(f.painel.tag)}</td><td>painel a jusante (${Util.esc(f.painel.tipo)})</td><td>${f.painel.num_fases || 3}F</td>
              <td class="num">${Util.fmt(f.painel.potencia_instalada_kw)}</td><td class="num">${Util.fmt(f.painel.potencia_reativa_instalada_kvar)}</td>
              <td class="num">${Util.fmt(f.painel.demanda_aparente_kva)}</td><td class="num">${Util.fmt(f.painel.corrente_total_a)}</td>
              <td class="num">${Util.fmt(f.painel.fator_diversidade)}</td><td class="num">${Util.fmt(f.painel.demanda_total_kw)}</td></tr>`).join("")}
            ${!no.equipamentos.length && !no.filhos.length ? '<tr><td colspan="9" class="vazio">Nenhuma carga associada a este painel.</td></tr>' : ""}
            <tr class="total"><td colspan="3">TOTAL ${Util.esc(p.tag)} (× fator de diversidade ${Util.fmt(p.fator_diversidade)})</td>
              <td class="num">${Util.fmt(p.potencia_instalada_kw)}</td><td class="num">${Util.fmt(p.potencia_reativa_instalada_kvar)}</td>
              <td class="num">${Util.fmt(p.demanda_aparente_kva)}</td><td class="num">${Util.fmt(p.corrente_total_a)}</td><td></td>
              <td class="num">${Util.fmt(p.demanda_total_kw)}</td></tr>
          </tbody>
        </table>
      </div>
    `;
  }

  function ligarEventos(card, p) {
    const pid = State.getProjetoAtivo().id;
    card.querySelector(`[data-salvar="${p.id}"]`).addEventListener("click", async () => {
      const ler = (campo) => card.querySelector(`[data-campo="${campo}"]`).value;
      const payload = {
        tag: ler("tag").trim(), tipo: ler("tipo"), tensao_v: Util.paraNumero(ler("tensao_v")) || 380,
        num_fases: Number(ler("num_fases")), fator_diversidade: Util.paraNumero(ler("fator_diversidade")) ?? 1.0,
        painel_alimentador_tag: ler("painel_alimentador_tag"),
      };
      try {
        await Api.atualizarPainel(pid, p.id, payload);
        Util.toast("Painel atualizado e demandas recalculadas.", "ok");
        App.irPara("cargas");
      } catch (err) { Util.erro(err); }
    });
    card.querySelector("[data-excluir-painel]").addEventListener("click", async () => {
      if (!Util.confirmar(`Excluir o painel "${p.tag}"?`)) return;
      try { await Api.removerPainel(pid, p.id); Util.toast("Painel excluído.", "ok"); App.irPara("cargas"); }
      catch (err) { Util.erro(err); }
    });
  }

  function abrirNovoPainel() {
    const pid = State.getProjetoAtivo().id;
    Util.abrirModal(`
      ${Util.cabecalhoModal("Novo painel / transformador")}
      <form id="form-painel">
        <div class="form-grid">
          <div class="campo"><label>TAG *</label><input name="tag" required placeholder="ex.: TR-01, QGBT-01"></div>
          <div class="campo"><label>Tipo</label><select name="tipo">${["painel", "quadro", "CCM", "transformador"].map((t) => `<option>${t}</option>`).join("")}</select></div>
          <div class="campo"><label>Tensão (V)</label><input name="tensao_v" value="380"></div>
          <div class="campo"><label>Fases</label><select name="num_fases"><option value="3">3F</option><option value="2">2F</option><option value="1">1F</option></select></div>
          <div class="campo"><label>Fator de diversidade</label><input name="fator_diversidade" value="1"></div>
          <div class="campo"><label>Alimentado por</label>
            <select name="painel_alimentador_tag"><option value="">— nenhum (painel TOP) —</option>${paineisCache.map((o) => `<option value="${Util.esc(o.tag)}">${Util.esc(o.tag)}</option>`).join("")}</select></div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn secundario" data-fechar>Cancelar</button>
          <button type="submit" class="btn">Salvar</button>
        </div>
      </form>
    `, (root) => {
      root.querySelector("#form-painel").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const obj = Util.formToObj(ev.target);
        obj.tensao_v = Util.paraNumero(obj.tensao_v) || 380;
        obj.num_fases = Number(obj.num_fases);
        obj.fator_diversidade = Util.paraNumero(obj.fator_diversidade) ?? 1;
        obj.painel_alimentador_tag = obj.painel_alimentador_tag || "";
        try { await Api.criarPainel(pid, obj); Util.fecharModal(); Util.toast("Painel criado.", "ok"); App.irPara("cargas"); }
        catch (err) { Util.erro(err); }
      });
    });
  }

  return { render };
})();
