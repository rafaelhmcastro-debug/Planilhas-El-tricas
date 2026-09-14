const TelaInfraestrutura = (() => {
  let cache = [];
  let catalogoCache = [];

  async function render(el) {
    const pid = State.getProjetoAtivo().id;
    [cache, catalogoCache] = await Promise.all([Api.listarInfra(pid), Api.catalogoInfra()]);
    el.innerHTML = `
      <div class="card">
        <div class="toolbar">
          <h2 style="margin:0">Eletrodutos e Bandejas</h2>
          <input type="text" id="filtro" placeholder="Filtrar por TAG…">
          <div class="spacer"></div>
          <button class="btn" id="btn-novo">+ Novo item</button>
        </div>
        <div class="wrap-table">
          <table class="grid">
            <thead><tr>
              <th>TAG</th><th>Tipo</th><th>Item do catálogo adotado</th><th>De</th><th>Para</th><th class="num">Compr. (m)</th>
              <th class="num">Cabos</th><th>Ocupação efetiva</th><th>Item sugerido pelo cálculo</th><th>Ações</th>
            </tr></thead>
            <tbody id="corpo-tabela"><tr><td colspan="10" class="vazio">Calculando ocupação…</td></tr></tbody>
          </table>
        </div>
      </div>
    `;
    el.querySelector("#btn-novo").addEventListener("click", () => abrirForm());
    el.querySelector("#filtro").addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      desenharTabela(el, cache.filter((x) => x.tag.toLowerCase().includes(q)));
    });
    await desenharTabela(el, cache);
  }

  async function desenharTabela(el, lista) {
    const corpo = el.querySelector("#corpo-tabela");
    if (!lista.length) { corpo.innerHTML = `<tr><td colspan="10" class="vazio">Nenhum item cadastrado.</td></tr>`; return; }
    const pid = State.getProjetoAtivo().id;
    const ocupacoes = await Promise.all(lista.map((i) => Api.ocupacaoInfra(pid, i.id).catch(() => null)));
    corpo.innerHTML = lista.map((it, idx) => linha(it, ocupacoes[idx])).join("");
    corpo.querySelectorAll("[data-editar]").forEach((b) => b.addEventListener("click", () => abrirForm(cache.find((x) => x.id === Number(b.dataset.editar)))));
    corpo.querySelectorAll("[data-excluir]").forEach((b) => b.addEventListener("click", () => excluir(Number(b.dataset.excluir))));
    corpo.querySelectorAll("[data-detalhe]").forEach((b) => b.addEventListener("click", () => verDetalhe(Number(b.dataset.detalhe))));
  }

  function linha(it, oc) {
    let ocupacaoTxt = "-", sugestaoTxt = "-", badge = "", cabos = "-";
    if (oc) {
      cabos = oc.num_cabos_fisicos ?? 0;
      if (oc.ocupacao_pct != null) {
        ocupacaoTxt = `<strong>${Util.fmt(oc.ocupacao_pct, 1)}%</strong>`;
        ocupacaoTxt += it.tipo === "eletroduto"
          ? ` <small>(${Util.fmt(oc.area_ocupada_mm2, 0)} / ${Util.fmt(oc.area_util_mm2, 0)} mm² · limite ${oc.limite_pct ?? "-"}%)</small>`
          : ` <small>(Σ Ø ${Util.fmt(oc.soma_diametros_mm, 1)} / ${Util.fmt(oc.largura_util_mm, 0)} mm)</small>`;
      } else if (!it.catalogo_infraestrutura_id) {
        ocupacaoTxt = `<small>selecione um item do catálogo</small>`;
      }
      sugestaoTxt = oc.dimensao_sugerida_desc || (cabos ? "nenhum item comporta" : "-");
      if (cabos) badge = oc.alerta ? `<span class="badge alerta">acima do limite</span>` : `<span class="badge ok">ok</span>`;
    }
    return `<tr>
      <td><strong>${Util.esc(it.tag)}</strong></td>
      <td>${Util.esc(it.tipo)}</td>
      <td>${Util.esc(oc?.item_escolhido || "(não definido)")} ${it.dimensao_definida_manualmente ? '<span class="badge manual">manual</span>' : ""}</td>
      <td>${Util.esc(it.no_origem || "-")}</td>
      <td>${Util.esc(it.no_destino || "-")}</td>
      <td class="num">${Util.fmt(it.comprimento_m, 1)}</td>
      <td class="num">${cabos}</td>
      <td>${ocupacaoTxt} ${badge}</td>
      <td>${Util.esc(sugestaoTxt)}</td>
      <td class="acoes-col">
        <button class="link" data-detalhe="${it.id}">cabos</button> ·
        <button class="link" data-editar="${it.id}">editar</button> ·
        <button class="link perigo" data-excluir="${it.id}">excluir</button>
      </td>
    </tr>`;
  }

  async function verDetalhe(infraId) {
    const pid = State.getProjetoAtivo().id;
    let oc;
    try { oc = await Api.ocupacaoInfra(pid, infraId); } catch (err) { Util.erro(err); return; }
    const linhas = oc.cabos.map((c) => `<tr>
      <td>${Util.esc(c.tag)}</td><td>${Util.esc(c.de)} → ${Util.esc(c.para)}</td>
      <td>${Util.esc(c.tipo_construcao || "-")}</td>
      <td class="num">${Util.fmt(c.secao_mm2, 1)}</td><td class="num">${Util.fmt(c.diametro_externo_mm, 1)}</td>
      <td class="num">${c.num_cabos_fisicos}</td><td class="num">${Util.fmt(c.area_total_mm2, 1)}</td></tr>`).join("");
    const resumo = oc.tipo === "eletroduto"
      ? `Área ocupada ${Util.fmt(oc.area_ocupada_mm2, 1)} mm² de ${Util.fmt(oc.area_util_mm2, 1)} mm² úteis → <strong>${Util.fmt(oc.ocupacao_pct, 1)}%</strong> (limite NBR 5410 para ${oc.num_cabos_fisicos} cabo(s): ${oc.limite_pct ?? "-"}%).`
      : `Soma dos diâmetros ${Util.fmt(oc.soma_diametros_mm, 1)} mm em ${Util.fmt(oc.largura_util_mm, 0)} mm de largura útil → <strong>${Util.fmt(oc.ocupacao_pct, 1)}%</strong> (cabos lado a lado, camada única).`;
    Util.abrirModal(`
      ${Util.cabecalhoModal(`Cabos que passam por ${oc.tag}`)}
      <div class="info-box">Item adotado: ${Util.esc(oc.item_escolhido || "(não definido)")}. Sugestão do cálculo: ${Util.esc(oc.dimensao_sugerida_desc || "-")}.</div>
      ${oc.num_cabos_fisicos ? `<div class="${oc.alerta ? "alerta-box" : "info-box"}">${resumo}</div>` : ""}
      <div class="wrap-table compacta">
      <table class="grid"><thead><tr><th>Cabo</th><th>De → Para</th><th>Construção</th><th class="num">Seção (mm²)</th><th class="num">Ø ext. (mm)</th><th class="num">Cabos físicos</th><th class="num">Área total (mm²)</th></tr></thead>
      <tbody>${linhas || '<tr><td colspan="7" class="vazio">Nenhum cabo passa por este trecho. Adicione este trecho ao percurso na tela "Cabos".</td></tr>'}</tbody></table>
      </div>
      <div class="modal-footer"><button class="btn secundario" data-fechar>Fechar</button></div>
    `, null, { larga: true });
  }

  function abrirForm(it) {
    const editando = !!it;
    const pid = State.getProjetoAtivo().id;
    const v = (campo, def = "") => (editando ? (it[campo] ?? def) : def);
    const tipos = ["eletroduto", "eletrocalha", "perfilado", "leito"];

    function opcoesCatalogo(tipoSelecionado) {
      return catalogoCache.filter((c) => c.tipo === tipoSelecionado).map((c) => {
        const desc = c.tipo === "eletroduto"
          ? `${c.linha_produto} — DN ${c.diametro_nominal_mm} mm (${c.diametro_nominal_pol || ""}) — área útil ${Util.fmt(c.area_util_mm2, 0)} mm²`
          : `${c.linha_produto} — ${c.largura_nominal_mm} mm`;
        return `<option value="${c.id}" ${editando && it.catalogo_infraestrutura_id === c.id ? "selected" : ""}>${Util.esc(desc)}</option>`;
      }).join("");
    }

    Util.abrirModal(`
      ${Util.cabecalhoModal(editando ? `Editar ${it.tag}` : "Novo eletroduto/bandeja")}
      <form id="form-infra">
        <div class="form-grid">
          <div class="campo"><label>TAG *</label><input name="tag" required value="${Util.esc(v("tag"))}"></div>
          <div class="campo">
            <label>Tipo *</label>
            <select name="tipo" id="sel-tipo">${tipos.map((t) => `<option value="${t}" ${v("tipo", "eletroduto") === t ? "selected" : ""}>${t}</option>`).join("")}</select>
          </div>
          <div class="campo span2">
            <label>Item do catálogo Elecon</label>
            <select name="catalogo_infraestrutura_id" id="sel-catalogo">
              <option value="">— nenhum —</option>
              ${opcoesCatalogo(v("tipo", "eletroduto"))}
            </select>
            <small class="ajuda">Após atribuir cabos ao trecho, o sistema sugere o menor item que atende à ocupação.</small>
          </div>
          <div class="campo"><label>Nó de origem</label><input name="no_origem" value="${Util.esc(v("no_origem"))}"></div>
          <div class="campo"><label>Nó de destino</label><input name="no_destino" value="${Util.esc(v("no_destino"))}"></div>
          <div class="campo"><label>Comprimento (m) *</label><input name="comprimento_m" type="text" inputmode="decimal" required value="${v("comprimento_m", 0)}"></div>
          <div class="campo">
            <label>Dimensão definida manualmente</label>
            <select name="dimensao_definida_manualmente">
              <option value="false" ${!v("dimensao_definida_manualmente", false) ? "selected" : ""}>Não</option>
              <option value="true" ${v("dimensao_definida_manualmente", false) ? "selected" : ""}>Sim (mantém minha escolha)</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn secundario" data-fechar>Cancelar</button>
          <button type="submit" class="btn">Salvar</button>
        </div>
      </form>
    `, (root) => {
      root.querySelector("#sel-tipo").addEventListener("change", (e) => {
        root.querySelector("#sel-catalogo").innerHTML = `<option value="">— nenhum —</option>${opcoesCatalogo(e.target.value)}`;
      });
      root.querySelector("#form-infra").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const obj = Util.formToObj(ev.target);
        obj.comprimento_m = Util.paraNumero(obj.comprimento_m) || 0;
        obj.catalogo_infraestrutura_id = obj.catalogo_infraestrutura_id ? Number(obj.catalogo_infraestrutura_id) : null;
        obj.dimensao_definida_manualmente = obj.dimensao_definida_manualmente === "true";
        try {
          if (editando) await Api.atualizarInfra(pid, it.id, obj);
          else await Api.criarInfra(pid, obj);
          Util.fecharModal();
          Util.toast("Item salvo.", "ok");
          App.irPara("infraestrutura");
        } catch (err) { Util.erro(err); }
      });
    });
  }

  async function excluir(id) {
    if (!Util.confirmar("Excluir este item de infraestrutura?")) return;
    try {
      await Api.removerInfra(State.getProjetoAtivo().id, id);
      Util.toast("Item excluído.", "ok");
      App.irPara("infraestrutura");
    } catch (err) { Util.erro(err); }
  }

  return { render };
})();
