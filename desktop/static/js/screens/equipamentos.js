const TelaEquipamentos = (() => {
  let cache = [];
  let paineisCache = [];

  async function render(el) {
    const pid = State.getProjetoAtivo().id;
    [cache, paineisCache] = await Promise.all([Api.listarEquipamentos(pid), Api.listarPaineis(pid)]);
    el.innerHTML = `
      <div class="card">
        <div class="toolbar">
          <h2 style="margin:0">Equipamentos (cargas)</h2>
          <input type="text" id="filtro" placeholder="Filtrar por TAG, descrição ou painel…">
          <div class="spacer"></div>
          <button class="btn" id="btn-novo">+ Novo equipamento</button>
        </div>
        <div class="wrap-table">
          <table class="grid">
            <thead><tr>
              <th>TAG</th><th>Descrição</th><th>Tipo</th><th>Potência</th><th>η</th><th class="num">P (kW)</th><th class="num">Q (kvar)</th>
              <th class="num">S (kVA)</th><th class="num">V (V)</th><th>Fases</th><th class="num">cos φ</th><th class="num">In (A)</th>
              <th class="num">FD</th><th class="num">Pd (kW)</th><th>Painel/Transf.</th><th>Ações</th>
            </tr></thead>
            <tbody id="corpo-tabela"></tbody>
          </table>
        </div>
      </div>
    `;
    desenharTabela(el, cache);
    el.querySelector("#btn-novo").addEventListener("click", () => abrirForm());
    el.querySelector("#filtro").addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      desenharTabela(el, cache.filter((x) => [x.tag, x.descricao, x.painel_transformador_tag].join(" ").toLowerCase().includes(q)));
    });
  }

  function fases(e) {
    let s = `${e.num_fases}F`;
    if (e.possui_neutro) s += "+N";
    if (e.possui_terra) s += "+PE";
    return s;
  }

  function desenharTabela(el, lista) {
    const corpo = el.querySelector("#corpo-tabela");
    corpo.innerHTML = lista.length ? lista.map(linha).join("") : `<tr><td colspan="16" class="vazio">Nenhum equipamento cadastrado.</td></tr>`;
    corpo.querySelectorAll("[data-editar]").forEach((b) => b.addEventListener("click", () => abrirForm(cache.find((x) => x.id === Number(b.dataset.editar)))));
    corpo.querySelectorAll("[data-duplicar]").forEach((b) => b.addEventListener("click", () => duplicar(cache.find((x) => x.id === Number(b.dataset.duplicar)))));
    corpo.querySelectorAll("[data-excluir]").forEach((b) => b.addEventListener("click", () => excluir(Number(b.dataset.excluir))));
  }

  function linha(e) {
    return `<tr>
      <td><strong>${Util.esc(e.tag)}</strong></td>
      <td>${Util.esc(e.descricao || "-")}</td>
      <td>${Util.esc(e.tipo_carga || "-")}</td>
      <td>${Util.fmt(e.potencia_valor)} ${Util.esc(e.potencia_unidade)}</td>
      <td>${Util.fmt(e.rendimento)}</td>
      <td class="num">${Util.fmt(e.potencia_ativa_calc_kw)}</td>
      <td class="num">${Util.fmt(e.potencia_reativa_calc_kvar)}</td>
      <td class="num">${Util.fmt(e.potencia_aparente_calc_kva)}</td>
      <td class="num">${Util.fmt(e.tensao_v, 0)}</td>
      <td>${fases(e)}</td>
      <td class="num">${Util.fmt(e.fator_potencia)}</td>
      <td class="num"><strong>${Util.fmt(e.corrente_nominal_a)}</strong></td>
      <td class="num">${Util.fmt(e.fator_demanda)}</td>
      <td class="num">${Util.fmt(e.potencia_demanda_kw)}</td>
      <td>${Util.esc(e.painel_transformador_tag || "-")}</td>
      <td class="acoes-col">
        <button class="link" data-editar="${e.id}">editar</button> ·
        <button class="link" data-duplicar="${e.id}">duplicar</button> ·
        <button class="link perigo" data-excluir="${e.id}">excluir</button>
      </td>
    </tr>`;
  }

  function abrirForm(e) {
    const editando = !!e;
    const pid = State.getProjetoAtivo().id;
    const v = (campo, def = "") => (editando ? (e[campo] ?? def) : def);
    const unidades = ["kW", "W", "CV", "HP", "kVA"];
    Util.abrirModal(`
      ${Util.cabecalhoModal(editando ? `Editar equipamento ${e.tag}` : "Novo equipamento")}
      <form id="form-equip">
        <div class="form-grid">
          <div class="campo"><label>TAG *</label><input name="tag" required value="${Util.esc(v("tag"))}"></div>
          <div class="campo span2"><label>Descrição</label><input name="descricao" value="${Util.esc(v("descricao"))}"></div>
          <div class="campo">
            <label>Tipo de carga</label>
            <select name="tipo_carga">
              ${["motor", "iluminação", "tomada", "climatização", "aquecimento", "painel/quadro", "outro"].map((t) => `<option ${v("tipo_carga", "motor") === t ? "selected" : ""}>${t}</option>`).join("")}
            </select>
          </div>
          <div class="campo">
            <label>Potência *</label>
            <div class="linha">
              <input name="potencia_valor" type="text" inputmode="decimal" required value="${v("potencia_valor", "") ?? ""}" placeholder="ex.: 30">
              <select name="potencia_unidade">${unidades.map((u) => `<option ${v("potencia_unidade", "kW") === u ? "selected" : ""}>${u}</option>`).join("")}</select>
            </div>
            <small class="ajuda">kW/W/CV/HP = potência nominal (no eixo, para motores); kVA = potência aparente absorvida.</small>
          </div>
          <div class="campo">
            <label>Rendimento η (0–1)</label>
            <input name="rendimento" type="text" inputmode="decimal" value="${v("rendimento", 1.0)}">
            <small class="ajuda">P elétrica = P nominal / η. Use 1,0 se não se aplica.</small>
          </div>
          <div class="campo"><label>Fator de potência cos φ</label><input name="fator_potencia" type="text" inputmode="decimal" value="${v("fator_potencia", 0.92)}"></div>
          <div class="campo"><label>Tensão do circuito (V) *</label><input name="tensao_v" type="text" inputmode="decimal" required value="${v("tensao_v", 380)}"></div>
          <div class="campo">
            <label>Nº de fases</label>
            <select name="num_fases">
              <option value="1" ${v("num_fases", 3) == 1 ? "selected" : ""}>1 — monofásico (fase-neutro)</option>
              <option value="2" ${v("num_fases", 3) == 2 ? "selected" : ""}>2 — bifásico (fase-fase)</option>
              <option value="3" ${v("num_fases", 3) == 3 ? "selected" : ""}>3 — trifásico</option>
            </select>
          </div>
          <div class="campo">
            <label>Condutores adicionais</label>
            <div class="checks">
              <label><input type="checkbox" name="possui_neutro" ${v("possui_neutro", false) ? "checked" : ""}> Neutro (N)</label>
              <label><input type="checkbox" name="possui_terra" ${v("possui_terra", true) ? "checked" : ""}> Terra (PE)</label>
            </div>
            <small class="ajuda">Define o nº de vias do cabo: fases + N + PE.</small>
          </div>
          <div class="campo"><label>Fator de demanda FD (0–1)</label><input name="fator_demanda" type="text" inputmode="decimal" value="${v("fator_demanda", 1.0)}"></div>
          <div class="campo">
            <label>Alimentado pelo painel/transformador (TAG)</label>
            <input name="painel_transformador_tag" list="lista-paineis" value="${Util.esc(v("painel_transformador_tag"))}" placeholder="TAG existente ou nova">
            <datalist id="lista-paineis">${paineisCache.map((p) => `<option value="${Util.esc(p.tag)}">`).join("")}</datalist>
            <small class="ajuda">Se a TAG não existir, o painel é criado automaticamente.</small>
          </div>
          <div class="campo"><label>Dimensões (C×L×A)</label><input name="dimensoes" value="${Util.esc(v("dimensoes"))}"></div>
          <div class="campo"><label>Peso (kg)</label><input name="peso_kg" type="text" inputmode="decimal" value="${v("peso_kg", "") ?? ""}"></div>
          <div class="campo"><label>Folha de dados (nº documento)</label><input name="folha_dados_numero" value="${Util.esc(v("folha_dados_numero"))}"></div>
          <div class="campo"><label>Diagrama elétrico (nº documento)</label><input name="diagrama_eletrico_numero" value="${Util.esc(v("diagrama_eletrico_numero"))}"></div>
          <div class="campo"><label>Fornecedor</label><input name="fornecedor" value="${Util.esc(v("fornecedor"))}"></div>
          <div class="campo span2"><label>Observação</label><textarea name="observacao" rows="2">${Util.esc(v("observacao"))}</textarea></div>
        </div>

        ${editando ? `
        <div class="kpi-row" style="margin-top:12px">
          <div class="kpi"><div class="valor">${Util.fmt(e.potencia_ativa_calc_kw)}</div><div class="rotulo">P (kW)</div></div>
          <div class="kpi"><div class="valor">${Util.fmt(e.potencia_reativa_calc_kvar)}</div><div class="rotulo">Q (kvar)</div></div>
          <div class="kpi"><div class="valor">${Util.fmt(e.potencia_aparente_calc_kva)}</div><div class="rotulo">S (kVA)</div></div>
          <div class="kpi"><div class="valor">${Util.fmt(e.corrente_nominal_a)}</div><div class="rotulo">In (A)</div></div>
          <div class="kpi"><div class="valor">${Util.fmt(e.potencia_demanda_kw)}</div><div class="rotulo">Pd (kW)</div></div>
        </div>` : `<div class="info-box" style="margin-top:12px">As potências P, Q, S e a corrente In são calculadas ao salvar.</div>`}

        <div class="modal-footer">
          <button type="button" class="btn secundario" data-fechar>Cancelar</button>
          <button type="submit" class="btn">Salvar e calcular</button>
        </div>
      </form>
    `, (root) => {
      root.querySelector("#form-equip").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const obj = Util.formToObj(ev.target);
        ["potencia_valor", "rendimento", "tensao_v", "fator_potencia", "fator_demanda", "peso_kg"].forEach((c) => obj[c] = Util.paraNumero(obj[c]));
        obj.num_fases = Number(obj.num_fases);
        if (obj.potencia_valor === null) { Util.toast("Informe a potência.", "erro"); return; }
        try {
          const equip = editando ? await Api.atualizarEquipamento(pid, e.id, obj) : await Api.criarEquipamento(pid, obj);
          Util.fecharModal();
          Util.toast(`Equipamento salvo. In = ${Util.fmt(equip.corrente_nominal_a)} A`, "ok");
          App.irPara("equipamentos");
        } catch (err) { Util.erro(err); }
      });
    });
  }

  async function duplicar(e) {
    const novaTag = prompt(`Nova TAG para a cópia de "${e.tag}":`, `${e.tag}-COPIA`);
    if (!novaTag) return;
    try {
      await Api.duplicarEquipamento(State.getProjetoAtivo().id, e.id, novaTag);
      Util.toast("Equipamento duplicado.", "ok");
      App.irPara("equipamentos");
    } catch (err) { Util.erro(err); }
  }

  async function excluir(id) {
    if (!Util.confirmar("Excluir este equipamento?")) return;
    const pid = State.getProjetoAtivo().id;
    try {
      await Api.removerEquipamento(pid, id);
      Util.toast("Equipamento excluído.", "ok");
      App.irPara("equipamentos");
    } catch (err) {
      if (String(err.message).includes("referenciado")) {
        if (Util.confirmar(err.message + "\n\nOs cabos ligados a ele também serão excluídos. Deseja continuar?")) {
          try { await Api.removerEquipamento(pid, id, true); Util.toast("Equipamento excluído.", "ok"); App.irPara("equipamentos"); }
          catch (err2) { Util.erro(err2); }
        }
      } else Util.erro(err);
    }
  }

  return { render };
})();
