const TelaConfig = (() => {
  let subtela = "cabos";

  async function render(el) {
    el.innerHTML = `
      <div class="card">
        <h2>Configurações / Normas</h2>
        <p style="color:var(--cinza);font-size:13px;margin-top:-6px">Tabelas e catálogos globais, compartilhados entre todos os projetos.</p>
        <div class="tab-interna" id="subtabs">
          ${sub("cabos", "Catálogo de Cabos")}
          ${sub("infra", "Catálogo de Infraestrutura (Elecon)")}
          ${sub("normas", "Tabelas Normativas (NBR 5410)")}
        </div>
        <div id="subconteudo"></div>
      </div>
    `;
    el.querySelectorAll("#subtabs button").forEach((b) => b.addEventListener("click", () => { subtela = b.dataset.sub; render(el); }));
    const cont = el.querySelector("#subconteudo");
    if (subtela === "cabos") await renderCabos(cont);
    else if (subtela === "infra") await renderInfra(cont);
    else await renderNormas(cont);
  }

  function sub(id, label) {
    return `<button class="${subtela === id ? "ativo" : ""}" data-sub="${id}">${label}</button>`;
  }

  // ---------------- Catálogo de cabos ----------------
  async function renderCabos(cont) {
    const itens = await Api.catalogoCabos();
    cont.innerHTML = `
      <div class="toolbar">
        <span>${itens.length} cabos cadastrados</span>
        <input type="text" id="filtro-cabos" placeholder="Filtrar por linha, isolação…">
        <div class="spacer"></div>
        <button class="btn pequeno" id="btn-novo-cabo-cat">+ Cadastrar cabo manualmente</button>
        <a class="btn secundario pequeno" href="${Api.urlModeloCabos}">Baixar planilha-modelo</a>
        <label class="btn secundario pequeno" style="cursor:pointer">Importar planilha
          <input type="file" id="arquivo-import-cabos" accept=".xlsx" style="display:none">
        </label>
      </div>
      <div class="wrap-table">
        <table class="grid">
          <thead><tr><th>Fabricante</th><th>Linha</th><th>Aplicação</th><th>Isolação</th><th>Tensão isol.</th><th>Construção</th><th class="num">Vias</th><th class="num">Seção (mm²)</th><th class="num">Ø ext. (mm)</th><th class="num">Peso (kg/km)</th><th class="num">R (Ω/km)</th><th class="num">X (Ω/km)</th><th>Fonte</th><th>Ações</th></tr></thead>
          <tbody id="corpo-cabos"></tbody>
        </table>
      </div>
    `;
    const desenhar = (lista) => {
      cont.querySelector("#corpo-cabos").innerHTML = lista.map((i) => `<tr>
        <td>${Util.esc(i.fabricante)}</td><td>${Util.esc(i.linha_produto)}</td><td>${Util.esc(i.aplicacao || "")}</td><td>${Util.esc(i.tipo_isolacao)}</td>
        <td>${Util.esc(i.tensao_isolamento || "")}</td><td>${Util.esc(i.construcao_basica || "")}</td><td class="num">${i.num_condutores}</td>
        <td class="num">${Util.fmt(i.secao_nominal_mm2, 1)}</td><td class="num">${Util.fmt(i.diametro_externo_nominal_mm, 2)}</td>
        <td class="num">${Util.fmt(i.peso_kg_km, 0)}</td><td class="num">${Util.fmt(i.resistencia_condutor_20c_ohm_km, 4)}</td><td class="num">${Util.fmt(i.reatancia_ohm_km, 3)}</td>
        <td><small>${Util.esc(i.fonte_datasheet || "")}</small></td>
        <td class="acoes-col"><button class="link" data-editar="${i.id}">editar</button> · <button class="link perigo" data-excluir="${i.id}">excluir</button></td></tr>`).join("") || '<tr><td colspan="14" class="vazio">Nenhum cabo no catálogo.</td></tr>';
      cont.querySelectorAll("[data-editar]").forEach((b) => b.addEventListener("click", () => formCabo(itens.find((x) => x.id === Number(b.dataset.editar)))));
      cont.querySelectorAll("[data-excluir]").forEach((b) => b.addEventListener("click", async () => {
        if (!Util.confirmar("Excluir este cabo do catálogo?")) return;
        try { await Api.removerCatalogoCabo(Number(b.dataset.excluir)); Util.toast("Removido.", "ok"); App.irPara("config"); } catch (err) { Util.erro(err); }
      }));
    };
    desenhar(itens);
    cont.querySelector("#filtro-cabos").addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      desenhar(itens.filter((i) => [i.fabricante, i.linha_produto, i.tipo_isolacao, i.construcao_basica, i.aplicacao].join(" ").toLowerCase().includes(q)));
    });
    cont.querySelector("#btn-novo-cabo-cat").addEventListener("click", () => formCabo());
    cont.querySelector("#arquivo-import-cabos").addEventListener("change", async (e) => {
      const f = e.target.files[0]; if (!f) return;
      const substituir = Util.confirmar("Substituir TODO o catálogo de cabos pelo conteúdo da planilha?\n\nOK = substituir tudo · Cancelar = apenas acrescentar os itens da planilha");
      const fd = new FormData(); fd.append("arquivo", f);
      try {
        const r = await Api.importarCatalogoCabos(fd, substituir);
        Util.toast(`${r.importados} cabos importados.`, "ok");
        App.irPara("config");
      } catch (err) { Util.erro(err); }
    });
  }

  function formCabo(item) {
    const editando = !!item;
    const v = (c, d = "") => (editando ? (item[c] ?? d) : d);
    Util.abrirModal(`
      ${Util.cabecalhoModal(editando ? "Editar cabo do catálogo" : "Cadastrar cabo no catálogo")}
      <form id="form-cabo-cat">
        <div class="form-grid">
          <div class="campo"><label>Fabricante *</label><input name="fabricante" required value="${Util.esc(v("fabricante", "Prysmian"))}"></div>
          <div class="campo"><label>Linha / produto *</label><input name="linha_produto" required value="${Util.esc(v("linha_produto"))}" placeholder="ex.: Afumex Green 1kV"></div>
          <div class="campo"><label>Aplicação</label><input name="aplicacao" value="${Util.esc(v("aplicacao"))}" placeholder="energia BT, controle…"></div>
          <div class="campo"><label>Material do condutor</label><select name="material_condutor"><option ${v("material_condutor", "cobre") === "cobre" ? "selected" : ""}>cobre</option><option ${v("material_condutor") === "alumínio" ? "selected" : ""}>alumínio</option></select></div>
          <div class="campo"><label>Tipo de isolação *</label><select name="tipo_isolacao">${["PVC", "EPR", "XLPE", "HEPR"].map((t) => `<option ${v("tipo_isolacao", "PVC") === t ? "selected" : ""}>${t}</option>`).join("")}</select></div>
          <div class="campo"><label>Tensão de isolamento</label><input name="tensao_isolamento" value="${Util.esc(v("tensao_isolamento", "0,6/1 kV"))}"></div>
          <div class="campo"><label>Nº de condutores (vias) *</label><input name="num_condutores" type="text" inputmode="numeric" required value="${v("num_condutores", 1)}"><small class="ajuda">1 = singelo; 2 a 5 = multipolar</small></div>
          <div class="campo"><label>Seção nominal (mm²) *</label><input name="secao_nominal_mm2" type="text" inputmode="decimal" required value="${v("secao_nominal_mm2", "")}"></div>
          <div class="campo"><label>Diâmetro externo nominal (mm) *</label><input name="diametro_externo_nominal_mm" type="text" inputmode="decimal" required value="${v("diametro_externo_nominal_mm", "")}"><small class="ajuda">Usado na ocupação de eletrodutos/bandejas.</small></div>
          <div class="campo"><label>Peso (kg/km)</label><input name="peso_kg_km" type="text" inputmode="decimal" value="${v("peso_kg_km", "") ?? ""}"></div>
          <div class="campo"><label>Resistência a 20 °C (Ω/km)</label><input name="resistencia_condutor_20c_ohm_km" type="text" inputmode="decimal" value="${v("resistencia_condutor_20c_ohm_km", "") ?? ""}"><small class="ajuda">Vazio = usa a tabela de resistividade padrão.</small></div>
          <div class="campo"><label>Reatância (Ω/km)</label><input name="reatancia_ohm_km" type="text" inputmode="decimal" value="${v("reatancia_ohm_km", "") ?? ""}"><small class="ajuda">Vazio = 0,08 Ω/km (referência).</small></div>
          <div class="campo"><label>Capacidade de condução (A) — datasheet</label><input name="capacidade_conducao_a" type="text" inputmode="decimal" value="${v("capacidade_conducao_a", "") ?? ""}"></div>
          <div class="campo"><label>Construção (texto do datasheet)</label><input name="construcao_basica" value="${Util.esc(v("construcao_basica"))}" placeholder="ex.: 3x2.5"></div>
          <div class="campo"><label>Blindagem</label><div class="checks"><label><input type="checkbox" name="possui_blindagem" ${v("possui_blindagem", false) ? "checked" : ""}> possui blindagem</label></div></div>
          <div class="campo"><label>Norma de referência</label><input name="norma_referencia" value="${Util.esc(v("norma_referencia"))}"></div>
          <div class="campo span2"><label>Fonte (datasheet)</label><input name="fonte_datasheet" value="${Util.esc(v("fonte_datasheet", "Cadastro manual"))}"></div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn secundario" data-fechar>Cancelar</button>
          <button type="submit" class="btn">Salvar</button>
        </div>
      </form>
    `, (root) => {
      root.querySelector("#form-cabo-cat").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const obj = Util.formToObj(ev.target);
        ["secao_nominal_mm2", "diametro_externo_nominal_mm", "peso_kg_km", "resistencia_condutor_20c_ohm_km", "reatancia_ohm_km", "capacidade_conducao_a"].forEach((c) => obj[c] = Util.paraNumero(obj[c]));
        obj.num_condutores = Number(obj.num_condutores) || 1;
        if (!obj.construcao_basica) obj.construcao_basica = `${obj.num_condutores}x${obj.secao_nominal_mm2}`;
        try {
          if (editando) await Api.atualizarCatalogoCabo(item.id, obj); else await Api.criarCatalogoCabo(obj);
          Util.fecharModal(); Util.toast("Cabo salvo no catálogo.", "ok"); App.irPara("config");
        } catch (err) { Util.erro(err); }
      });
    }, { larga: true });
  }

  // ---------------- Catálogo de infraestrutura ----------------
  async function renderInfra(cont) {
    const itens = await Api.catalogoInfra();
    cont.innerHTML = `
      <div class="toolbar">
        <span>${itens.length} itens cadastrados</span>
        <input type="text" id="filtro-infra" placeholder="Filtrar por linha ou tipo…">
        <div class="spacer"></div>
        <button class="btn secundario pequeno" id="btn-nova-eletrocalha">+ Eletrocalha customizada</button>
        <a class="btn secundario pequeno" href="${Api.urlModeloInfra}">Baixar planilha-modelo</a>
        <label class="btn secundario pequeno" style="cursor:pointer">Importar planilha
          <input type="file" id="arquivo-import-infra" accept=".xlsx" style="display:none">
        </label>
      </div>
      <div class="wrap-table">
        <table class="grid">
          <thead><tr><th>Linha</th><th>Tipo</th><th>DN (pol)</th><th class="num">DN (mm)</th><th class="num">Parede (mm)</th><th class="num">Ø ext. (mm)</th><th class="num">Ø int. (mm)</th><th class="num">Área útil (mm²)</th><th class="num">Largura (mm)</th><th class="num">Altura (mm)</th><th class="num">Largura útil (mm)</th><th>Fonte</th></tr></thead>
          <tbody id="corpo-infra"></tbody>
        </table>
      </div>
    `;
    const desenhar = (lista) => {
      cont.querySelector("#corpo-infra").innerHTML = lista.map((i) => `<tr>
        <td>${Util.esc(i.linha_produto)}</td><td>${Util.esc(i.tipo)}</td><td>${Util.esc(i.diametro_nominal_pol || "")}</td>
        <td class="num">${Util.fmt(i.diametro_nominal_mm, 0)}</td><td class="num">${Util.fmt(i.parede_mm, 2)}</td><td class="num">${Util.fmt(i.diametro_externo_mm, 2)}</td>
        <td class="num">${Util.fmt(i.diametro_interno_mm, 2)}</td><td class="num">${Util.fmt(i.area_util_mm2, 0)}</td>
        <td class="num">${Util.fmt(i.largura_nominal_mm, 0)}</td><td class="num">${Util.fmt(i.altura_nominal_mm, 0)}</td><td class="num">${Util.fmt(i.largura_util_mm, 0)}</td>
        <td><small>${Util.esc(i.fonte_datasheet || "")}</small></td></tr>`).join("") || '<tr><td colspan="12" class="vazio">Nenhum item.</td></tr>';
    };
    desenhar(itens);
    cont.querySelector("#filtro-infra").addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      desenhar(itens.filter((i) => [i.linha_produto, i.tipo].join(" ").toLowerCase().includes(q)));
    });
    cont.querySelector("#arquivo-import-infra").addEventListener("change", async (e) => {
      const f = e.target.files[0]; if (!f) return;
      const substituir = Util.confirmar("Substituir TODO o catálogo de infraestrutura pelo conteúdo da planilha?\n\nOK = substituir tudo · Cancelar = apenas acrescentar");
      const fd = new FormData(); fd.append("arquivo", f);
      try {
        const r = await Api.importarCatalogoInfra(fd, substituir);
        Util.toast(`${r.importados} itens importados.`, "ok");
        App.irPara("config");
      } catch (err) { Util.erro(err); }
    });
    cont.querySelector("#btn-nova-eletrocalha").addEventListener("click", () => {
      Util.abrirModal(`
        ${Util.cabecalhoModal("Nova eletrocalha customizada")}
        <form id="form-eletrocalha">
          <div class="form-grid">
            <div class="campo"><label>Descrição *</label><input name="linha_produto" required placeholder="Eletrocalha Perfurada 450mm"></div>
            <div class="campo"><label>Largura nominal (mm) *</label><input name="largura_nominal_mm" type="text" inputmode="decimal" required></div>
            <div class="campo"><label>Altura nominal (mm)</label><input name="altura_nominal_mm" type="text" inputmode="decimal"></div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn secundario" data-fechar>Cancelar</button>
            <button type="submit" class="btn">Salvar</button>
          </div>
        </form>
      `, (root) => {
        root.querySelector("#form-eletrocalha").addEventListener("submit", async (ev) => {
          ev.preventDefault();
          const obj = Util.formToObj(ev.target);
          obj.tipo = "eletrocalha";
          obj.largura_nominal_mm = Util.paraNumero(obj.largura_nominal_mm);
          obj.altura_nominal_mm = Util.paraNumero(obj.altura_nominal_mm);
          obj.largura_util_mm = obj.largura_nominal_mm;
          try { await Api.criarInfraCustomizada(obj); Util.fecharModal(); Util.toast("Eletrocalha cadastrada.", "ok"); App.irPara("config"); }
          catch (err) { Util.erro(err); }
        });
      });
    });
  }

  // ---------------- Normas ----------------
  async function renderNormas(cont) {
    const [cap, temp, agr, resist, limite] = await Promise.all([
      Api.tabCapacidade(), Api.tabTemperatura(), Api.tabAgrupamento(), Api.tabResistividade(), Api.tabLimiteEletroduto(),
    ]);
    const metodos = [...new Set(cap.map((r) => r.metodo_instalacao))];
    const secoes = [...new Set(cap.map((r) => r.secao_mm2))].sort((a, b) => a - b);
    const capMatriz = (grupo) => `
      <div class="wrap-table compacta" style="max-height:420px">
        <table class="grid">
          <thead><tr><th>Seção (mm²)</th>${metodos.map((m) => `<th class="num" colspan="2">${m}</th>`).join("")}</tr>
                 <tr><th></th>${metodos.map(() => `<th class="num">2 cond.</th><th class="num">3 cond.</th>`).join("")}</tr></thead>
          <tbody>${secoes.map((s) => `<tr><td><strong>${s}</strong></td>${metodos.map((m) => {
            const c2 = cap.find((r) => r.isolacao_grupo === grupo && r.metodo_instalacao === m && r.secao_mm2 === s && r.num_condutores_carregados === 2);
            const c3 = cap.find((r) => r.isolacao_grupo === grupo && r.metodo_instalacao === m && r.secao_mm2 === s && r.num_condutores_carregados === 3);
            return `<td class="num">${c2 ? c2.capacidade_a : "-"}</td><td class="num">${c3 ? c3.capacidade_a : "-"}</td>`;
          }).join("")}</tr>`).join("")}</tbody>
        </table>
      </div>`;

    cont.innerHTML = `
      <div class="aviso-box">Os valores abaixo são de referência (NBR 5410, tabelas 36 a 42). Confira com a edição vigente da norma antes de liberar projetos.
        A tabela de capacidade de condução pode ser substituída por planilha:
        <a href="${Api.urlModeloCapacidade}">baixar planilha-modelo</a> ·
        <label style="cursor:pointer;text-decoration:underline">importar planilha<input type="file" id="arquivo-import-cap" accept=".xlsx" style="display:none"></label>
      </div>

      <h3>Capacidade de condução (A) — isolação PVC (70 °C), condutor de cobre — métodos A1 a G</h3>
      ${capMatriz("PVC")}
      <h3 style="margin-top:18px">Capacidade de condução (A) — isolação EPR / XLPE / HEPR (90 °C), condutor de cobre — métodos A1 a G</h3>
      ${capMatriz("EPR_XLPE")}

      <div class="form-grid" style="margin-top:18px">
        <div>
          <h3>Limite de ocupação de eletrodutos</h3>
          <div class="wrap-table compacta"><table class="grid"><thead><tr><th>Nº de cabos</th><th class="num">Taxa máxima</th></tr></thead>
          <tbody>${limite.map((r) => `<tr><td>${r.num_cabos}</td><td class="num">${r.taxa_max_pct}%</td></tr>`).join("")}</tbody></table></div>
        </div>
        <div>
          <h3>Fator de agrupamento</h3>
          <div class="wrap-table compacta"><table class="grid"><thead><tr><th>Nº de circuitos</th><th class="num">Fator</th></tr></thead>
          <tbody>${agr.map((r) => `<tr><td>${r.num_circuitos}</td><td class="num">${r.fator}</td></tr>`).join("")}</tbody></table></div>
        </div>
        <div>
          <h3>Fator de temperatura ambiente</h3>
          <div class="wrap-table compacta"><table class="grid"><thead><tr><th>Isolação</th><th class="num">Temp. (°C)</th><th class="num">Fator</th></tr></thead>
          <tbody>${temp.map((r) => `<tr><td>${r.isolacao_grupo}</td><td class="num">${r.temperatura_c}</td><td class="num">${r.fator}</td></tr>`).join("")}</tbody></table></div>
        </div>
        <div>
          <h3>Resistência do condutor de cobre (20 °C)</h3>
          <div class="wrap-table compacta"><table class="grid"><thead><tr><th class="num">Seção (mm²)</th><th class="num">R (Ω/km)</th></tr></thead>
          <tbody>${resist.map((r) => `<tr><td class="num">${r.secao_mm2}</td><td class="num">${r.resistencia_ohm_km}</td></tr>`).join("")}</tbody></table></div>
        </div>
      </div>
    `;
    cont.querySelector("#arquivo-import-cap").addEventListener("change", async (e) => {
      const f = e.target.files[0]; if (!f) return;
      if (!Util.confirmar("Substituir TODA a tabela de capacidade de condução pela planilha?")) return;
      const fd = new FormData(); fd.append("arquivo", f);
      try { const r = await Api.importarCapacidade(fd); Util.toast(`${r.importados} linhas importadas.`, "ok"); App.irPara("config"); }
      catch (err) { Util.erro(err); }
    });
  }

  return { render };
})();
