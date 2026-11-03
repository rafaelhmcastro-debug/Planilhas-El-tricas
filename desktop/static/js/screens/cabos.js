const TelaCabos = (() => {
  let cache = [];
  let equipamentosCache = [];
  let paineisCache = [];
  let infraCache = [];

  const METODOS = [
    ["A1", "A1 — condutores isolados em eletroduto embutido em parede termicamente isolante"],
    ["A2", "A2 — cabo multipolar em eletroduto embutido em parede termicamente isolante"],
    ["B1", "B1 — condutores isolados/cabos unipolares em eletroduto aparente ou embutido em alvenaria"],
    ["B2", "B2 — cabo multipolar em eletroduto aparente ou embutido em alvenaria"],
    ["C", "C — cabos fixados diretamente em parede/teto ou em bandeja não perfurada"],
    ["D", "D — cabos em eletroduto enterrado no solo"],
    ["E", "E — cabo multipolar ao ar livre, em bandeja perfurada, leito ou suporte"],
    ["F", "F — cabos unipolares justapostos ao ar livre, em bandeja perfurada ou leito"],
    ["G", "G — cabos unipolares espaçados ao ar livre"],
  ];

  async function render(el) {
    const pid = State.getProjetoAtivo().id;
    [cache, equipamentosCache, paineisCache, infraCache] = await Promise.all([
      Api.listarCabos(pid), Api.listarEquipamentos(pid), Api.listarPaineis(pid), Api.listarInfra(pid),
    ]);
    el.innerHTML = `
      <div class="card">
        <div class="toolbar">
          <h2 style="margin:0">Cabos</h2>
          <input type="text" id="filtro" placeholder="Filtrar por TAG, De ou Para…">
          <div class="spacer"></div>
          <button class="btn secundario" id="btn-recalcular">Recalcular todos</button>
          <button class="btn" id="btn-novo">+ Novo cabo</button>
        </div>
        <div class="wrap-table">
          <table class="grid">
            <thead><tr>
              <th>TAG</th><th>De</th><th>Para</th><th>Config.</th><th>Isolação</th><th>Método</th><th class="num">Ib (A)</th>
              <th class="num">Seção sugerida</th><th>Cabo adotado</th><th class="num">ΔV (%)</th><th class="num">Dist. (m)</th><th>Ações</th>
            </tr></thead>
            <tbody id="corpo-tabela"></tbody>
          </table>
        </div>
      </div>
    `;
    desenharTabela(el, cache);
    el.querySelector("#btn-novo").addEventListener("click", () => abrirForm());
    el.querySelector("#btn-recalcular").addEventListener("click", async () => {
      try { await Api.recalcularTodosCabos(pid); Util.toast("Todos os cabos foram recalculados.", "ok"); App.irPara("cabos"); }
      catch (err) { Util.erro(err); }
    });
    el.querySelector("#filtro").addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      desenharTabela(el, cache.filter((x) => [x.tag, x.de_tag, x.para_tag].join(" ").toLowerCase().includes(q)));
    });
  }

  function desenharTabela(el, lista) {
    const corpo = el.querySelector("#corpo-tabela");
    corpo.innerHTML = lista.length ? lista.map(linha).join("") : `<tr><td colspan="12" class="vazio">Nenhum cabo cadastrado.</td></tr>`;
    corpo.querySelectorAll("[data-editar]").forEach((b) => b.addEventListener("click", () => abrirForm(cache.find((x) => x.id === Number(b.dataset.editar)))));
    corpo.querySelectorAll("[data-memoria]").forEach((b) => b.addEventListener("click", () => abrirMemoria(Number(b.dataset.memoria))));
    corpo.querySelectorAll("[data-excluir]").forEach((b) => b.addEventListener("click", () => excluir(Number(b.dataset.excluir))));
  }

  function descConstrucao(c) {
    if (!c.secao_mm2) return "-";
    if (c.tipo_construcao === "unipolar") return `${c.num_condutores_calc}× 1x${Util.fmt(c.secao_mm2, 1)} mm² (singelos)`;
    return `${c.num_condutores_calc}x${Util.fmt(c.secao_mm2, 1)} mm² (multipolar)`;
  }

  function linha(c) {
    const alerta = c.alerta_secao_insuficiente ? `<span class="badge alerta" title="Seção adotada menor que a sugerida">abaixo</span>` : "";
    const manual = c.secao_definida_manualmente ? `<span class="badge manual">manual</span>` : "";
    const dv = c.queda_tensao_calc_pct != null && c.queda_tensao_calc_pct > c.queda_tensao_admissivel_pct ? `<span class="badge alerta">ΔV</span>` : "";
    return `<tr>
      <td><strong>${Util.esc(c.tag)}</strong></td>
      <td>${Util.esc(c.de_tag)}</td>
      <td>${Util.esc(c.para_tag)}</td>
      <td>${c.num_fases ? `${c.num_fases}F / ${c.num_condutores_calc} vias` : "-"}</td>
      <td>${Util.esc(c.tipo_isolacao)}</td>
      <td>${Util.esc(c.metodo_instalacao)}</td>
      <td class="num">${Util.fmt(c.corrente_projeto_a)}</td>
      <td class="num">${Util.fmt(c.secao_sugerida_mm2, 1)}</td>
      <td>${descConstrucao(c)} ${c.num_cabos_paralelo > 1 ? `×${c.num_cabos_paralelo} paral.` : ""} ${alerta} ${manual}</td>
      <td class="num">${Util.fmt(c.queda_tensao_calc_pct)} ${dv}</td>
      <td class="num">${Util.fmt(c.distancia_total_m, 1)}</td>
      <td class="acoes-col">
        <button class="link" data-memoria="${c.id}">memória</button> ·
        <button class="link" data-editar="${c.id}">editar</button> ·
        <button class="link perigo" data-excluir="${c.id}">excluir</button>
      </td>
    </tr>`;
  }

  function opcoesPontas(selecionado) {
    const grupoP = paineisCache.map((p) => `<option value="P:${p.id}" ${selecionado === `P:${p.id}` ? "selected" : ""}>${Util.esc(p.tag)} — ${Util.esc(p.tipo)} (${Util.fmt(p.tensao_v, 0)} V, I=${Util.fmt(p.corrente_total_a, 1)} A)</option>`).join("");
    const grupoE = equipamentosCache.map((e) => `<option value="E:${e.id}" ${selecionado === `E:${e.id}` ? "selected" : ""}>${Util.esc(e.tag)} — ${Util.esc(e.descricao || "")} (${Util.fmt(e.tensao_v, 0)} V, In=${Util.fmt(e.corrente_nominal_a, 1)} A)</option>`).join("");
    return `<option value="">— selecione —</option>
      <optgroup label="Painéis / transformadores">${grupoP || "<option disabled>nenhum</option>"}</optgroup>
      <optgroup label="Equipamentos (cargas)">${grupoE || "<option disabled>nenhum</option>"}</optgroup>`;
  }

  function pontaAtual(c, lado) {
    if (!c) return "";
    if (c[`painel_${lado}_id`]) return `P:${c[`painel_${lado}_id`]}`;
    if (c[`equipamento_${lado}_id`]) return `E:${c[`equipamento_${lado}_id`]}`;
    return "";
  }

  function abrirForm(c) {
    const editando = !!c;
    const pid = State.getProjetoAtivo().id;
    const v = (campo, def = "") => (editando ? (c[campo] ?? def) : def);
    let trechos = [];
    let catalogoOpcoes = [];

    function renderTrechos(root) {
      const ul = root.querySelector("#lista-trechos");
      ul.innerHTML = trechos.length ? trechos.map((id, idx) => {
        const infra = infraCache.find((i) => i.id === id);
        return `<li class="trecho-item">
          <span class="grip">${idx + 1}.</span>
          <span class="info">${infra ? `${Util.esc(infra.tag)} — ${Util.esc(infra.tipo)} — ${Util.fmt(infra.comprimento_m, 1)} m` : "item removido"}</span>
          <button type="button" class="btn pequeno secundario" data-subir="${idx}" title="subir">↑</button>
          <button type="button" class="btn pequeno secundario" data-descer="${idx}" title="descer">↓</button>
          <button type="button" class="btn pequeno perigo" data-remover="${idx}">remover</button>
        </li>`;
      }).join("") : `<li class="vazio">Nenhum trecho no percurso. Selecione um eletroduto/bandeja acima e clique em "adicionar".</li>`;
      const distancia = trechos.reduce((s, id) => s + (infraCache.find((i) => i.id === id)?.comprimento_m || 0), 0);
      root.querySelector("#distancia-total").textContent = Util.fmt(distancia, 1) + " m";
      ul.querySelectorAll("[data-subir]").forEach((b) => b.addEventListener("click", () => {
        const i = Number(b.dataset.subir);
        if (i > 0) { [trechos[i - 1], trechos[i]] = [trechos[i], trechos[i - 1]]; renderTrechos(root); }
      }));
      ul.querySelectorAll("[data-descer]").forEach((b) => b.addEventListener("click", () => {
        const i = Number(b.dataset.descer);
        if (i < trechos.length - 1) { [trechos[i + 1], trechos[i]] = [trechos[i], trechos[i + 1]]; renderTrechos(root); }
      }));
      ul.querySelectorAll("[data-remover]").forEach((b) => b.addEventListener("click", () => { trechos.splice(Number(b.dataset.remover), 1); renderTrechos(root); }));
    }

    async function atualizarCatalogo(root, tipoIsolacao) {
      catalogoOpcoes = await Api.catalogoCabos({ tipo_isolacao: tipoIsolacao });
      const sel = root.querySelector("#sel-catalogo-cabo");
      const atual = editando && c.secao_definida_manualmente ? c.catalogo_cabo_id : null;
      sel.innerHTML = `<option value="">— sugestão automática do cálculo —</option>` +
        catalogoOpcoes.map((cc) => `<option value="${cc.id}" ${atual === cc.id ? "selected" : ""}>${Util.esc(cc.linha_produto)} ${cc.num_condutores}x${cc.secao_nominal_mm2} mm² (Ø ${cc.diametro_externo_nominal_mm} mm)</option>`).join("");
    }

    Util.abrirModal(`
      ${Util.cabecalhoModal(editando ? `Editar cabo ${c.tag}` : "Novo cabo")}
      <form id="form-cabo">
        <div class="form-grid">
          <div class="campo"><label>TAG *</label><input name="tag" required value="${Util.esc(v("tag"))}"></div>
          <div class="campo"><label>De (origem) *</label><select name="de" required>${opcoesPontas(pontaAtual(c, "de"))}</select></div>
          <div class="campo">
            <label>Para (destino = carga alimentada) *</label>
            <select name="para" required>${opcoesPontas(pontaAtual(c, "para"))}</select>
            <small class="ajuda">Tensão, corrente, fases e cos φ são herdados da carga (ponta "Para").</small>
          </div>
          <div class="campo">
            <label>Tipo de isolação</label>
            <select name="tipo_isolacao" id="sel-isolacao">
              ${["PVC", "EPR", "XLPE", "HEPR"].map((t) => `<option ${v("tipo_isolacao", "PVC") === t ? "selected" : ""}>${t}</option>`).join("")}
            </select>
          </div>
          <div class="campo span2">
            <label>Método de instalação (NBR 5410)</label>
            <select name="metodo_instalacao">
              ${METODOS.map(([k, d]) => `<option value="${k}" ${v("metodo_instalacao", "B1") === k ? "selected" : ""}>${d}</option>`).join("")}
            </select>
          </div>
          <div class="campo"><label>Temperatura ambiente (°C)</label><input name="temperatura_ambiente_c" type="text" inputmode="decimal" value="${v("temperatura_ambiente_c", 30)}"><small class="ajuda">Fator de correção obtido da tabela NBR 5410.</small></div>
          <div class="campo"><label>Fator de agrupamento (manual)</label><input name="fator_agrupamento_manual" type="text" inputmode="decimal" value="${v("fator_agrupamento_manual", "") ?? ""}" placeholder="vazio = automático"><small class="ajuda">Automático = pelo nº de circuitos que dividem os trechos.</small></div>
          <div class="campo"><label>Queda de tensão admissível (%)</label><input name="queda_tensao_admissivel_pct" type="text" inputmode="decimal" value="${v("queda_tensao_admissivel_pct", 3.0)}"></div>
          <div class="campo"><label>Nº de cabos em paralelo por fase</label><input name="num_cabos_paralelo" type="text" inputmode="numeric" value="${v("num_cabos_paralelo", 1)}"></div>
          <div class="campo span2"><label>Observação</label><textarea name="observacao" rows="2">${Util.esc(v("observacao"))}</textarea></div>
        </div>

        <h3 style="margin-top:16px">Percurso (eletrodutos/bandejas)</h3>
        <div class="toolbar">
          <select id="sel-add-trecho">${infraCache.map((i) => `<option value="${i.id}">${Util.esc(i.tag)} — ${Util.esc(i.tipo)} (${Util.fmt(i.comprimento_m, 1)} m)</option>`).join("") || "<option value=''>nenhum eletroduto/bandeja cadastrado</option>"}</select>
          <button type="button" class="btn secundario pequeno" id="btn-add-trecho">+ adicionar ao percurso</button>
          <div class="spacer"></div>
          <span>Distância total: <strong id="distancia-total">0 m</strong></span>
        </div>
        <ul class="trecho-lista" id="lista-trechos"></ul>

        <h3 style="margin-top:16px">Cabo comercial</h3>
        <div class="campo">
          <label>Cabo do catálogo</label>
          <select name="catalogo_cabo_id" id="sel-catalogo-cabo"><option value="">carregando…</option></select>
          <small class="ajuda">Deixe em "sugestão automática" para o sistema escolher (multipolar até 35 mm², singelos a partir de 50 mm²), ou escolha manualmente outro cabo.</small>
        </div>

        ${editando ? resumoCalculo(c) : `<div class="info-box" style="margin-top:12px">Ao salvar, o sistema calcula Ib, seção, queda de tensão e gera a memória de cálculo.</div>`}

        <div class="modal-footer">
          <button type="button" class="btn secundario" data-fechar>Cancelar</button>
          <button type="submit" class="btn">Salvar e calcular</button>
        </div>
      </form>
    `, async (root) => {
      if (editando) {
        try {
          const trechosApi = await Api.trechosDoCabo(pid, c.id);
          trechos = trechosApi.sort((a, b) => a.ordem - b.ordem).map((t) => t.eletroduto_bandeja_id);
        } catch (e) { trechos = []; }
      }
      renderTrechos(root);
      root.querySelector("#btn-add-trecho").addEventListener("click", () => {
        const id = Number(root.querySelector("#sel-add-trecho").value);
        if (id) { trechos.push(id); renderTrechos(root); }
      });
      await atualizarCatalogo(root, root.querySelector("#sel-isolacao").value);
      root.querySelector("#sel-isolacao").addEventListener("change", (e) => atualizarCatalogo(root, e.target.value));

      root.querySelector("#form-cabo").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const obj = Util.formToObj(ev.target);
        const de = String(obj.de || ""), para = String(obj.para || "");
        delete obj.de; delete obj.para;
        obj.painel_de_id = de.startsWith("P:") ? Number(de.slice(2)) : null;
        obj.equipamento_de_id = de.startsWith("E:") ? Number(de.slice(2)) : null;
        obj.painel_para_id = para.startsWith("P:") ? Number(para.slice(2)) : null;
        obj.equipamento_para_id = para.startsWith("E:") ? Number(para.slice(2)) : null;
        obj.temperatura_ambiente_c = Util.paraNumero(obj.temperatura_ambiente_c) ?? 30;
        obj.fator_agrupamento_manual = Util.paraNumero(obj.fator_agrupamento_manual);
        obj.queda_tensao_admissivel_pct = Util.paraNumero(obj.queda_tensao_admissivel_pct) || 3.0;
        obj.num_cabos_paralelo = Number(obj.num_cabos_paralelo) || 1;
        obj.catalogo_cabo_id = obj.catalogo_cabo_id ? Number(obj.catalogo_cabo_id) : null;
        obj.trechos = trechos.map((id, idx) => ({ eletroduto_bandeja_id: id, ordem: idx }));
        try {
          const salvo = editando ? await Api.atualizarCabo(pid, c.id, obj) : await Api.criarCabo(pid, obj);
          Util.fecharModal();
          Util.toast(`Cabo calculado: Ib = ${Util.fmt(salvo.corrente_projeto_a)} A, seção ${Util.fmt(salvo.secao_mm2, 1)} mm², ΔV = ${Util.fmt(salvo.queda_tensao_calc_pct)} %`, "ok");
          if (salvo.alerta_secao_insuficiente) Util.toast("Atenção: a seção adotada é menor que a seção sugerida pelo cálculo.", "erro");
          App.irPara("cabos");
        } catch (err) { Util.erro(err); }
      });
    }, { larga: true });
  }

  function resumoCalculo(c) {
    return `
      <div class="kpi-row" style="margin-top:16px">
        <div class="kpi"><div class="valor">${Util.fmt(c.corrente_projeto_a)}</div><div class="rotulo">Ib (A)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(c.secao_por_capacidade_mm2, 1)}</div><div class="rotulo">Seção p/ capacidade (mm²)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(c.secao_por_queda_mm2, 1)}</div><div class="rotulo">Seção p/ queda ΔV (mm²)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(c.secao_sugerida_mm2, 1)}</div><div class="rotulo">Seção sugerida (mm²)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(c.secao_mm2, 1)}</div><div class="rotulo">Seção adotada (mm²)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(c.queda_tensao_calc_pct)}</div><div class="rotulo">ΔV calculada (%)</div></div>
        <div class="kpi"><div class="valor">${Util.fmt(c.fator_temperatura_calc)} / ${Util.fmt(c.fator_agrupamento_calc)}</div><div class="rotulo">Fatores temp. / agrup.</div></div>
      </div>
      ${c.alerta_secao_insuficiente ? '<div class="alerta-box" style="margin-top:10px">A seção adotada é menor que a seção sugerida pelo cálculo.</div>' : ""}
    `;
  }

  async function abrirMemoria(caboId) {
    const pid = State.getProjetoAtivo().id;
    let memoria;
    try { memoria = await Api.memoriaCalculo(pid, caboId); } catch (err) { Util.erro(err); return; }
    const passos = (memoria.passos || []).map((p) => `
      <div class="memoria-passo">
        <h4>${Util.esc(p.titulo)} ${p.resultado ? `<span class="resultado">${Util.esc(p.resultado)}</span>` : ""}</h4>
        <ul>${(p.linhas || []).map((l) => `<li class="${l.startsWith("  ") ? "tentativa" : ""}">${Util.esc(l.trim())}</li>`).join("")}</ul>
      </div>`).join("");
    Util.abrirModal(`
      ${Util.cabecalhoModal(`Memória de cálculo — cabo ${memoria.cabo_tag} (${memoria.de} → ${memoria.para})`)}
      <div style="max-height:65vh;overflow-y:auto;padding-right:6px">${passos || '<div class="vazio">Sem memória de cálculo — salve o cabo novamente.</div>'}</div>
      <div class="modal-footer">
        <a class="btn secundario" href="${Api.urlRelatorio(pid, "memoria-calculo.xlsx", { cabo_id: caboId })}">Exportar este cabo (Excel)</a>
        <button class="btn" data-fechar>Fechar</button>
      </div>
    `, null, { larga: true });
  }

  async function excluir(id) {
    if (!Util.confirmar("Excluir este cabo?")) return;
    try {
      await Api.removerCabo(State.getProjetoAtivo().id, id);
      Util.toast("Cabo excluído.", "ok");
      App.irPara("cabos");
    } catch (err) { Util.erro(err); }
  }

  return { render };
})();
