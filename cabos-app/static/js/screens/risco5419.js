const TelaRisco5419 = (() => {
  const NOMES_TABELA = {
    fator_localizacao: "anexo_a_tabela_a1_cd", tipo_construcao: "anexo_c_tabela_c7_rs",
    tipo_piso: "anexo_c_tabela_c3_rt_piso", providencias_incendio: "anexo_c_tabela_c4_rp",
    risco_incendio: "anexo_c_tabela_c5_rf", perigo_especial: "anexo_c_tabela_c6_hz",
    perdas_r1: "anexo_c_tabela_c2_perdas_r1",
    tipo_instalacao: "anexo_a_tabela_a2_ci", ambiente: "anexo_a_tabela_a4_ce",
    categoria_blindagem: "anexo_b_tabela_b4_cld_cli", categoria_pld: "anexo_b_tabela_b8_pld",
    classe_spda: "anexo_b_tabela_b2_pb", medidas_pta: "anexo_b_tabela_b1_pta",
    dps_coordenado: "anexo_b_tabela_b3_pspd", dps_classe_i: "anexo_b_tabela_b7_peb",
    medida_ptu: "anexo_b_tabela_b6_ptu", fiacao_interna: "anexo_b_tabela_b5_ks3",
  };

  let opcoesCache = null;

  async function carregarOpcoes() {
    if (opcoesCache) return opcoesCache;
    const entradas = await Promise.all(Object.entries(NOMES_TABELA).map(async ([campo, tabela]) => [campo, await Api.opcoesTabelaRisco(tabela)]));
    opcoesCache = Object.fromEntries(entradas);
    return opcoesCache;
  }

  function optionsHtml(lista, grupo, valorAtual) {
    const filtradas = grupo ? lista.filter((o) => o.grupo === grupo) : lista;
    return filtradas.map((o) => `<option value="${Util.esc(o.chave)}" ${o.chave === valorAtual ? "selected" : ""}>${Util.esc(o.descricao)}</option>`).join("");
  }

  // ---------------- Lista de análises ----------------

  async function render(el) {
    const pid = State.getProjetoAtivo().id;
    el.innerHTML = '<div class="vazio">Carregando…</div>';
    const analises = await Api.listarAnalisesRisco(pid);
    desenharLista(el, analises);
  }

  function desenharLista(el, analises) {
    const pid = State.getProjetoAtivo().id;
    el.innerHTML = `
      <div class="card">
        <div class="toolbar">
          <h2 style="margin:0">Análise de Risco de Descargas Atmosféricas (NBR 5419-2)</h2>
          <div class="spacer"></div>
          <button class="btn" id="btn-nova-analise">+ Nova análise</button>
        </div>
        <div class="info-box">
          Cálculo de risco (R1, R3) e frequência de danos (F) conforme o Projeto de Revisão
          ABNT NBR 5419-2 (JUL/2025). Clique numa análise para cadastrar a estrutura, zonas,
          linhas elétricas e medidas de proteção, e calcular o resultado. R4 (perda de valor
          econômico, uso opcional na norma) ainda não está implementado.
        </div>
        ${analises.length === 0 ? '<div class="vazio">Nenhuma análise cadastrada para este projeto.</div>' : `
        <div class="wrap-table">
          <table class="grid">
            <thead><tr>
              <th>TAG / Estrutura</th><th>Origem do NG</th><th class="num">NG (raios/km²·ano)</th>
              <th class="num">R1</th><th class="num">R3</th><th class="num">F</th><th>Situação</th><th class="acoes-col">Ações</th>
            </tr></thead>
            <tbody>
              ${analises.map((a) => `
                <tr class="linha-analise" data-abrir="${a.id}" style="cursor:pointer">
                  <td>${Util.esc(a.tag)}</td>
                  <td>${a.ng_modo === "municipio" ? `Município: ${Util.esc(a.ng_municipio)}/${Util.esc(a.ng_uf)}` : "Manual"}</td>
                  <td class="num">${Util.fmt(a.ng_valor, 1)}</td>
                  <td class="num">-</td><td class="num">-</td><td class="num">-</td>
                  <td><span class="badge ${a.situacao === "emitida" ? "ok" : "info"}">${Util.esc(a.situacao)}</span></td>
                  <td class="acoes-col"><button class="link perigo" data-remover="${a.id}">excluir</button></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>`}
      </div>
    `;

    el.querySelector("#btn-nova-analise").addEventListener("click", () => abrirModalNovaAnalise());
    el.querySelectorAll("[data-abrir]").forEach((tr) => tr.addEventListener("click", () => abrirWorkspace(Number(tr.dataset.abrir))));
    el.querySelectorAll("[data-remover]").forEach((b) => b.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      if (!Util.confirmar("Excluir esta análise de risco?")) return;
      try {
        await Api.removerAnaliseRisco(pid, Number(b.dataset.remover));
        Util.toast("Análise removida.", "ok");
        render(document.getElementById("conteudo"));
      } catch (err) { Util.erro(err); }
    }));
  }

  async function abrirModalNovaAnalise() {
    const ufs = await Api.ngUfs();
    let modo = "municipio";
    let municipioEscolhido = null;

    Util.abrirModal(`
      ${Util.cabecalhoModal("Nova análise de risco")}
      <form id="form-analise-risco">
        <div class="form-grid">
          <div class="campo span2">
            <label>TAG / Descrição da estrutura *</label>
            <input name="tag" required placeholder="Ex.: GALPAO-PRINCIPAL">
          </div>
          <div class="campo span2">
            <label>Origem da densidade de descargas atmosféricas (NG)</label>
            <div class="checks">
              <label><input type="radio" name="ng_modo" value="municipio" checked> Por município (Anexo F)</label>
              <label><input type="radio" name="ng_modo" value="manual"> Informar manualmente</label>
            </div>
          </div>
        </div>

        <div id="bloco-municipio">
          <div class="form-grid">
            <div class="campo">
              <label>UF</label>
              <select id="sel-uf">
                <option value="">— selecione —</option>
                ${ufs.map((uf) => `<option value="${uf}">${uf}</option>`).join("")}
              </select>
            </div>
            <div class="campo span2">
              <label>Município</label>
              <input id="busca-municipio" placeholder="Digite ao menos 2 letras…" autocomplete="off" disabled>
              <small class="ajuda">Busca ignora acentos e maiúsculas/minúsculas.</small>
            </div>
          </div>
          <div id="lista-municipios" class="trecho-lista" style="max-height:180px;overflow:auto;margin-top:6px"></div>
          <div id="municipio-selecionado" class="info-box" style="display:none;margin-top:10px"></div>
        </div>

        <div id="bloco-manual" style="display:none">
          <div class="form-grid">
            <div class="campo">
              <label>NG informado (raios/km²·ano) *</label>
              <input name="ng_valor_manual" type="text" inputmode="decimal" placeholder="Ex.: 14">
            </div>
            <div class="campo span2">
              <label>Fonte / justificativa</label>
              <input name="ng_fonte_manual" placeholder="Ex.: laudo meteorológico local, estudo X">
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn secundario" data-fechar>Cancelar</button>
          <button type="submit" class="btn">Salvar</button>
        </div>
      </form>
    `, (root) => {
      const blocoMunicipio = root.querySelector("#bloco-municipio");
      const blocoManual = root.querySelector("#bloco-manual");
      const selUf = root.querySelector("#sel-uf");
      const buscaMunicipio = root.querySelector("#busca-municipio");
      const listaMunicipios = root.querySelector("#lista-municipios");
      const municipioSelecionadoBox = root.querySelector("#municipio-selecionado");

      root.querySelectorAll('input[name=ng_modo]').forEach((r) => r.addEventListener("change", (e) => {
        modo = e.target.value;
        blocoMunicipio.style.display = modo === "municipio" ? "" : "none";
        blocoManual.style.display = modo === "manual" ? "" : "none";
      }));

      selUf.addEventListener("change", () => {
        buscaMunicipio.disabled = !selUf.value;
        buscaMunicipio.value = "";
        listaMunicipios.innerHTML = "";
        municipioEscolhido = null;
        municipioSelecionadoBox.style.display = "none";
      });

      let timer = null;
      buscaMunicipio.addEventListener("input", () => {
        clearTimeout(timer);
        const q = buscaMunicipio.value.trim();
        municipioEscolhido = null;
        municipioSelecionadoBox.style.display = "none";
        if (q.length < 2) { listaMunicipios.innerHTML = ""; return; }
        timer = setTimeout(async () => {
          try {
            const resultados = await Api.ngBuscarMunicipios(selUf.value, q);
            listaMunicipios.innerHTML = resultados.length === 0
              ? '<div class="vazio" style="padding:10px">Nenhum município encontrado.</div>'
              : resultados.map((m) => `
                  <div class="trecho-item" data-municipio="${Util.esc(m.municipio)}" data-ng="${m.ng}" style="cursor:pointer">
                    <div class="info">${Util.esc(m.municipio)}</div>
                    <div class="num">NG = ${Util.fmt(m.ng, 1)}</div>
                  </div>
                `).join("");
            listaMunicipios.querySelectorAll("[data-municipio]").forEach((li) => li.addEventListener("click", () => {
              municipioEscolhido = { municipio: li.dataset.municipio, uf: selUf.value, ng: Number(li.dataset.ng) };
              buscaMunicipio.value = li.dataset.municipio;
              listaMunicipios.innerHTML = "";
              municipioSelecionadoBox.style.display = "";
              municipioSelecionadoBox.innerHTML = `NG selecionado: <strong>${Util.fmt(municipioEscolhido.ng, 1)} raios/km²·ano</strong> (${Util.esc(municipioEscolhido.municipio)}/${Util.esc(municipioEscolhido.uf)}, Anexo F)`;
            }));
          } catch (err) { Util.erro(err); }
        }, 300);
      });

      root.querySelector("#form-analise-risco").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const obj = Util.formToObj(ev.target);
        const payload = { tag: obj.tag, ng_modo: modo };
        if (modo === "manual") {
          payload.ng_valor_manual = Util.paraNumero(obj.ng_valor_manual);
          payload.ng_fonte_manual = obj.ng_fonte_manual;
        } else {
          if (!municipioEscolhido) { Util.toast("Selecione um município na lista.", "erro"); return; }
          payload.ng_municipio = municipioEscolhido.municipio;
          payload.ng_uf = municipioEscolhido.uf;
        }
        try {
          await Api.criarAnaliseRisco(State.getProjetoAtivo().id, payload);
          Util.fecharModal();
          Util.toast("Análise criada.", "ok");
          render(document.getElementById("conteudo"));
        } catch (err) { Util.erro(err); }
      });
    }, { larga: false });
  }

  // ---------------- Workspace de uma análise (abas) ----------------

  async function abrirWorkspace(analiseId, abaAtiva) {
    const el = document.getElementById("conteudo");
    el.innerHTML = '<div class="vazio">Carregando…</div>';
    const pid = State.getProjetoAtivo().id;
    const [analise] = await Promise.all([Api.obterAnaliseRisco(pid, analiseId), carregarOpcoes()]);
    desenharWorkspace(el, analise, abaAtiva || "estrutura");
  }

  const ABAS = [
    { id: "estrutura", label: "1. Estrutura" },
    { id: "zonas", label: "2. Zonas de Estudo" },
    { id: "linhas", label: "3. Linhas Elétricas" },
    { id: "medidas", label: "4. Medidas de Proteção" },
    { id: "resultado", label: "5. Resultado" },
  ];

  function desenharWorkspace(el, analise, abaAtiva) {
    el.innerHTML = `
      <div class="card">
        <div class="toolbar">
          <button class="btn secundario pequeno" id="btn-voltar-lista">← Voltar à lista</button>
          <h2 style="margin:0">${Util.esc(analise.tag)}</h2>
        </div>
        <div class="tab-interna">
          ${ABAS.map((a) => `<button data-aba="${a.id}" class="${a.id === abaAtiva ? "ativo" : ""}">${a.label}</button>`).join("")}
        </div>
        <div id="aba-conteudo"><div class="vazio">Carregando…</div></div>
      </div>
    `;
    el.querySelector("#btn-voltar-lista").addEventListener("click", () => render(el));
    el.querySelectorAll("[data-aba]").forEach((b) => b.addEventListener("click", () => abrirWorkspace(analise.id, b.dataset.aba)));

    const abaEl = el.querySelector("#aba-conteudo");
    const renderizadores = {
      estrutura: renderAbaEstrutura, zonas: renderAbaZonas, linhas: renderAbaLinhas,
      medidas: renderAbaMedidas, resultado: renderAbaResultado,
    };
    renderizadores[abaAtiva](abaEl, analise);
  }

  // ---------------- Aba 1: Estrutura ----------------

  async function renderAbaEstrutura(el, analise) {
    const pid = State.getProjetoAtivo().id;
    let estrutura = null;
    try { estrutura = await Api.obterEstruturaRisco(pid, analise.id); } catch (e) { /* ainda não cadastrada */ }
    const op = opcoesCache;
    const v = (campo, padrao) => (estrutura ? estrutura[campo] : padrao);

    el.innerHTML = `
      <form id="form-estrutura">
        <div class="form-grid">
          <div class="campo"><label>Comprimento L (m) *</label><input name="comprimento_m" type="text" inputmode="decimal" required value="${v("comprimento_m", "") ?? ""}"></div>
          <div class="campo"><label>Largura W (m) *</label><input name="largura_m" type="text" inputmode="decimal" required value="${v("largura_m", "") ?? ""}"></div>
          <div class="campo"><label>Altura H (m) *</label><input name="altura_m" type="text" inputmode="decimal" required value="${v("altura_m", "") ?? ""}"></div>
          <div class="campo"><label>Nº total de pessoas na estrutura (nt) *</label><input name="num_pessoas_total" type="text" inputmode="numeric" required value="${v("num_pessoas_total", "") ?? ""}"></div>
          <div class="campo span2"><label>Localização relativa da estrutura (CD — Tabela A.1)</label>
            <select name="fator_localizacao">${optionsHtml(op.fator_localizacao, null, v("fator_localizacao"))}</select>
          </div>
          <div class="campo span2"><label>Tipo construtivo (rs — Tabela C.7)</label>
            <select name="tipo_construcao">${optionsHtml(op.tipo_construcao, null, v("tipo_construcao"))}</select>
          </div>
          <div class="campo span2">
            <div class="checks">
              <label><input type="checkbox" name="risco_explosao" ${v("risco_explosao") ? "checked" : ""}> Estrutura com risco de explosão</label>
              <label><input type="checkbox" name="falha_sistema_interno_risco_vida" ${v("falha_sistema_interno_risco_vida") ? "checked" : ""}> Falha de sistema interno pode colocar vida em risco imediatamente</label>
              <label><input type="checkbox" name="sistema_critico" ${v("sistema_critico") ? "checked" : ""}> Sistema crítico (define FT = 0,1/ano)</label>
            </div>
            <small class="ajuda">As duas primeiras opções habilitam RC, RM, RW e RZ no cálculo de R1 (Equação 1, nota).</small>
          </div>
        </div>
        <div class="modal-footer" style="justify-content:flex-start;padding-left:0">
          <button type="submit" class="btn">Salvar estrutura</button>
        </div>
      </form>
    `;

    el.querySelector("#form-estrutura").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const obj = Util.formToObj(ev.target);
      const payload = {
        comprimento_m: Util.paraNumero(obj.comprimento_m), largura_m: Util.paraNumero(obj.largura_m),
        altura_m: Util.paraNumero(obj.altura_m), num_pessoas_total: Math.round(Util.paraNumero(obj.num_pessoas_total)),
        fator_localizacao: obj.fator_localizacao, tipo_construcao: obj.tipo_construcao,
        risco_explosao: obj.risco_explosao, falha_sistema_interno_risco_vida: obj.falha_sistema_interno_risco_vida,
        sistema_critico: obj.sistema_critico,
      };
      try {
        await Api.salvarEstruturaRisco(pid, analise.id, payload);
        Util.toast("Estrutura salva.", "ok");
      } catch (err) { Util.erro(err); }
    });
  }

  // ---------------- Aba 2: Zonas de Estudo ----------------

  async function renderAbaZonas(el, analise) {
    const pid = State.getProjetoAtivo().id;
    const zonas = await Api.listarZonasRisco(pid, analise.id);
    el.innerHTML = `
      <div class="toolbar"><div class="spacer"></div><button class="btn" id="btn-nova-zona">+ Nova zona de estudo</button></div>
      ${zonas.length === 0 ? '<div class="vazio">Nenhuma zona cadastrada. Se a estrutura inteira tem características homogêneas, cadastre uma única zona representando toda a estrutura.</div>' : `
      <div class="wrap-table compacta"><table class="grid">
        <thead><tr><th>Nome</th><th class="num">Pessoas (nz)</th><th class="num">Horas/ano (tz)</th><th>Patrimônio cultural (cz)</th><th class="acoes-col">Ações</th></tr></thead>
        <tbody>${zonas.map((z) => `
          <tr>
            <td>${Util.esc(z.nome)}</td>
            <td class="num">${z.num_pessoas_zona}</td>
            <td class="num">${Util.fmt(z.tempo_pessoas_horas_ano, 0)}</td>
            <td class="num">${z.valor_patrimonio_cultural ? Util.fmt(z.valor_patrimonio_cultural, 2) : "-"}</td>
            <td class="acoes-col"><button class="link perigo" data-remover-zona="${z.id}">excluir</button></td>
          </tr>
        `).join("")}</tbody>
      </table></div>`}
    `;

    el.querySelector("#btn-nova-zona").addEventListener("click", () => abrirModalZona(analise));
    el.querySelectorAll("[data-remover-zona]").forEach((b) => b.addEventListener("click", async () => {
      if (!Util.confirmar("Excluir esta zona de estudo?")) return;
      try { await Api.removerZonaRisco(pid, analise.id, Number(b.dataset.removerZona)); renderAbaZonas(el, analise); }
      catch (err) { Util.erro(err); }
    }));
  }

  function abrirModalZona(analise) {
    const op = opcoesCache;
    Util.abrirModal(`
      ${Util.cabecalhoModal("Nova zona de estudo")}
      <form id="form-zona">
        <div class="form-grid">
          <div class="campo span2"><label>Nome da zona *</label><input name="nome" required value="Zona única"></div>
          <div class="campo"><label>Nº de pessoas na zona (nz) *</label><input name="num_pessoas_zona" type="text" inputmode="numeric" required></div>
          <div class="campo"><label>Horas/ano com pessoas presentes (tz) *</label><input name="tempo_pessoas_horas_ano" type="text" inputmode="decimal" required value="8760"></div>
          <div class="campo span2"><label>Tipo de piso (rt — Tabela C.3)</label><select name="tipo_piso">${optionsHtml(op.tipo_piso)}</select></div>
          <div class="campo span2"><label>Providências contra incêndio (rp — Tabela C.4)</label><select name="providencias_incendio">${optionsHtml(op.providencias_incendio)}</select></div>
          <div class="campo span2"><label>Risco de incêndio/explosão (rf — Tabela C.5)</label><select name="risco_incendio">${optionsHtml(op.risco_incendio)}</select></div>
          <div class="campo span2"><label>Perigo especial / pânico (hz — Tabela C.6)</label><select name="perigo_especial">${optionsHtml(op.perigo_especial)}</select></div>
          <div class="campo span2"><label>Tipo de estrutura p/ dano físico (LF — Tabela C.2)</label><select name="categoria_dano_fisico_lf">${optionsHtml(op.perdas_r1, "LF")}</select></div>
          <div class="campo span2"><label>Tipo de estrutura p/ falha de sistema interno (LO — Tabela C.2)</label><select name="categoria_falha_sistema_lo">${optionsHtml(op.perdas_r1, "LO")}</select></div>
          <div class="campo span2"><label>Valor do patrimônio cultural nesta zona (cz)</label><input name="valor_patrimonio_cultural" type="text" inputmode="decimal" placeholder="Vazio = zona não participa de R3"></div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn secundario" data-fechar>Cancelar</button>
          <button type="submit" class="btn">Salvar</button>
        </div>
      </form>
    `, (root) => {
      root.querySelector("#form-zona").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const obj = Util.formToObj(ev.target);
        const payload = {
          nome: obj.nome, num_pessoas_zona: Math.round(Util.paraNumero(obj.num_pessoas_zona)),
          tempo_pessoas_horas_ano: Util.paraNumero(obj.tempo_pessoas_horas_ano),
          tipo_piso: obj.tipo_piso, providencias_incendio: obj.providencias_incendio,
          risco_incendio: obj.risco_incendio, perigo_especial: obj.perigo_especial,
          categoria_dano_fisico_lf: obj.categoria_dano_fisico_lf, categoria_falha_sistema_lo: obj.categoria_falha_sistema_lo,
          valor_patrimonio_cultural: obj.valor_patrimonio_cultural ? Util.paraNumero(obj.valor_patrimonio_cultural) : null,
        };
        try {
          await Api.criarZonaRisco(State.getProjetoAtivo().id, analise.id, payload);
          Util.fecharModal();
          Util.toast("Zona criada.", "ok");
          renderAbaZonas(document.getElementById("aba-conteudo"), analise);
        } catch (err) { Util.erro(err); }
      });
    });
  }

  // ---------------- Aba 3: Linhas Elétricas ----------------

  async function renderAbaLinhas(el, analise) {
    const pid = State.getProjetoAtivo().id;
    const linhas = await Api.listarLinhasRisco(pid, analise.id);
    el.innerHTML = `
      <div class="toolbar"><div class="spacer"></div><button class="btn" id="btn-nova-linha">+ Nova linha elétrica</button></div>
      ${linhas.length === 0 ? '<div class="vazio">Nenhuma linha cadastrada. Cadastre as linhas de energia e sinal que se conectam à estrutura.</div>' : `
      <div class="wrap-table compacta"><table class="grid">
        <thead><tr><th>TAG</th><th>Tipo</th><th>Transf. AT/BT</th><th class="num">UW (kV)</th><th>Trechos</th><th class="acoes-col">Ações</th></tr></thead>
        <tbody>${linhas.map((l) => `
          <tr>
            <td>${Util.esc(l.tag)}</td><td>${l.tipo}</td><td>${l.tem_transformador_at_bt ? "sim" : "não"}</td>
            <td class="num">${l.tensao_suportavel_kv}</td><td>${l.trechos.length} trecho(s), ${l.trechos.reduce((s, t) => s + t.comprimento_m, 0)} m total</td>
            <td class="acoes-col"><button class="link perigo" data-remover-linha="${l.id}">excluir</button></td>
          </tr>
        `).join("")}</tbody>
      </table></div>`}
    `;
    el.querySelector("#btn-nova-linha").addEventListener("click", () => abrirModalLinha(analise));
    el.querySelectorAll("[data-remover-linha]").forEach((b) => b.addEventListener("click", async () => {
      if (!Util.confirmar("Excluir esta linha (e todos os seus trechos)?")) return;
      try { await Api.removerLinhaRisco(pid, analise.id, Number(b.dataset.removerLinha)); renderAbaLinhas(el, analise); }
      catch (err) { Util.erro(err); }
    }));
  }

  function abrirModalLinha(analise) {
    const op = opcoesCache;
    let trechos = [];

    function renderTrechos(root) {
      const ul = root.querySelector("#lista-trechos-linha");
      ul.innerHTML = trechos.length ? trechos.map((t, i) => `
        <div class="trecho-item">
          <div class="info">${Util.fmt(t.comprimento_m, 0)} m — ${op.tipo_instalacao.find((o) => o.chave === t.tipo_instalacao)?.descricao} — ${op.ambiente.find((o) => o.chave === t.ambiente)?.descricao}</div>
          <button type="button" class="link perigo" data-remover-trecho="${i}">remover</button>
        </div>
      `).join("") : '<div class="vazio" style="padding:8px">Nenhum trecho adicionado ainda.</div>';
      ul.querySelectorAll("[data-remover-trecho]").forEach((b) => b.addEventListener("click", () => {
        trechos.splice(Number(b.dataset.removerTrecho), 1);
        renderTrechos(root);
      }));
    }

    Util.abrirModal(`
      ${Util.cabecalhoModal("Nova linha elétrica")}
      <form id="form-linha">
        <div class="form-grid">
          <div class="campo"><label>TAG *</label><input name="tag" required placeholder="Ex.: ALIMENTADOR-BT"></div>
          <div class="campo"><label>Tipo *</label><select name="tipo"><option value="energia">Energia</option><option value="sinal">Sinal</option></select></div>
          <div class="campo"><label>Tensão suportável do equipamento UW (kV) *</label><input name="tensao_suportavel_kv" type="text" inputmode="decimal" required placeholder="Ex.: 1.5"></div>
          <div class="campo span2"><label class="checks"><input type="checkbox" name="tem_transformador_at_bt"> Linha de energia em AT com transformador AT/BT</label></div>
        </div>

        <h3>Trechos da linha (SL)</h3>
        <div class="form-grid">
          <div class="campo"><label>Comprimento (m)</label><input id="tr-comprimento" type="text" inputmode="decimal" value="1000"></div>
          <div class="campo"><label>Instalação (CI)</label><select id="tr-instalacao">${optionsHtml(op.tipo_instalacao)}</select></div>
          <div class="campo"><label>Ambiente (CE)</label><select id="tr-ambiente">${optionsHtml(op.ambiente)}</select></div>
          <div class="campo span2"><label>Blindagem/aterramento (CLD, CLI — Tabela B.4)</label><select id="tr-blindagem">${optionsHtml(op.categoria_blindagem)}</select></div>
          <div class="campo span2"><label>Condições de roteamento/blindagem para PLD (Tabela B.8)</label><select id="tr-pld">${optionsHtml(op.categoria_pld)}</select></div>
        </div>
        <button type="button" class="btn secundario pequeno" id="btn-add-trecho">+ adicionar trecho</button>
        <div id="lista-trechos-linha" style="margin-top:10px"></div>

        <div class="modal-footer">
          <button type="button" class="btn secundario" data-fechar>Cancelar</button>
          <button type="submit" class="btn">Salvar linha</button>
        </div>
      </form>
    `, (root) => {
      renderTrechos(root);
      root.querySelector("#btn-add-trecho").addEventListener("click", () => {
        const comprimento_m = Util.paraNumero(root.querySelector("#tr-comprimento").value);
        if (!comprimento_m || comprimento_m <= 0) { Util.toast("Informe um comprimento válido para o trecho.", "erro"); return; }
        trechos.push({
          comprimento_m,
          tipo_instalacao: root.querySelector("#tr-instalacao").value,
          ambiente: root.querySelector("#tr-ambiente").value,
          categoria_blindagem: root.querySelector("#tr-blindagem").value,
          categoria_pld: root.querySelector("#tr-pld").value,
        });
        renderTrechos(root);
      });

      root.querySelector("#form-linha").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        if (trechos.length === 0) { Util.toast("Adicione ao menos um trecho.", "erro"); return; }
        const obj = Util.formToObj(ev.target);
        const payload = {
          tag: obj.tag, tipo: obj.tipo, tem_transformador_at_bt: obj.tem_transformador_at_bt,
          tensao_suportavel_kv: Util.paraNumero(obj.tensao_suportavel_kv), trechos,
        };
        try {
          await Api.criarLinhaRisco(State.getProjetoAtivo().id, analise.id, payload);
          Util.fecharModal();
          Util.toast("Linha criada.", "ok");
          renderAbaLinhas(document.getElementById("aba-conteudo"), analise);
        } catch (err) { Util.erro(err); }
      });
    }, { larga: true });
  }

  // ---------------- Aba 4: Medidas de Proteção ----------------

  async function renderAbaMedidas(el, analise) {
    const pid = State.getProjetoAtivo().id;
    let medidas = null;
    try { medidas = await Api.obterMedidasRisco(pid, analise.id); } catch (e) { /* ainda não cadastradas */ }
    const op = opcoesCache;
    const v = (campo, padrao) => (medidas ? medidas[campo] : padrao);
    const ptaAtuais = medidas ? medidas.medidas_pta : [];

    el.innerHTML = `
      <form id="form-medidas">
        <div class="form-grid">
          <div class="campo span2"><label>Classe do SPDA (PB — Tabela B.2)</label><select name="classe_spda">${optionsHtml(op.classe_spda, null, v("classe_spda", "sem_spda"))}</select></div>
          <div class="campo span2"><label>Medidas contra tensão de toque/passo na estrutura (PTA — Tabela B.1)</label>
            <div class="checks" style="flex-direction:column;align-items:flex-start;gap:6px">
              ${op.medidas_pta.map((o) => `<label><input type="checkbox" name="medidas_pta" value="${o.chave}" ${ptaAtuais.includes(o.chave) ? "checked" : ""}> ${Util.esc(o.descricao)}</label>`).join("")}
            </div>
            <small class="ajuda">Se mais de uma for marcada, PTA = produto dos valores (B.2.2).</small>
          </div>
          <div class="campo span2"><label>DPS coordenado (PSPD — Tabela B.3)</label><select name="dps_coordenado">${optionsHtml(op.dps_coordenado, null, v("dps_coordenado", "nenhum_sistema_coordenado_dps"))}</select></div>
          <div class="campo span2"><label>DPS classe I / ligação equipotencial (PEB — Tabela B.7)</label><select name="dps_classe_i">${optionsHtml(op.dps_classe_i, null, v("dps_classe_i", "sem_dps_classe_i"))}</select></div>
          <div class="campo span2"><label>Proteção contra toque em linha elétrica (PTU — Tabela B.6)</label><select name="medida_ptu">${optionsHtml(op.medida_ptu, null, v("medida_ptu"))}</select></div>
          <div class="campo span2"><label>Fiação interna (KS3 — Tabela B.5)</label><select name="fiacao_interna">${optionsHtml(op.fiacao_interna, null, v("fiacao_interna"))}</select></div>
          <div class="campo"><label>Largura da malha de blindagem externa wm1 (m)</label><input name="largura_malha_externa_m" type="text" inputmode="decimal" value="${v("largura_malha_externa_m", "") ?? ""}" placeholder="Vazio = sem blindagem (KS1=1)"></div>
          <div class="campo"><label>Largura da malha de blindagem interna wm2 (m)</label><input name="largura_malha_interna_m" type="text" inputmode="decimal" value="${v("largura_malha_interna_m", "") ?? ""}" placeholder="Vazio = sem blindagem (KS2=1)"></div>
          <div class="campo span2"><label>Tensão suportável do sistema interno a proteger (kV) *</label><input name="tensao_suportavel_sistema_interno_kv" type="text" inputmode="decimal" required value="${v("tensao_suportavel_sistema_interno_kv", "") ?? ""}"></div>
        </div>
        <div class="modal-footer" style="justify-content:flex-start;padding-left:0">
          <button type="submit" class="btn">Salvar medidas de proteção</button>
        </div>
      </form>
    `;

    el.querySelector("#form-medidas").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(ev.target);
      const payload = {
        classe_spda: fd.get("classe_spda"),
        medidas_pta: fd.getAll("medidas_pta"),
        dps_coordenado: fd.get("dps_coordenado"),
        dps_classe_i: fd.get("dps_classe_i"),
        medida_ptu: fd.get("medida_ptu"),
        fiacao_interna: fd.get("fiacao_interna"),
        largura_malha_externa_m: fd.get("largura_malha_externa_m") ? Util.paraNumero(fd.get("largura_malha_externa_m")) : null,
        largura_malha_interna_m: fd.get("largura_malha_interna_m") ? Util.paraNumero(fd.get("largura_malha_interna_m")) : null,
        tensao_suportavel_sistema_interno_kv: Util.paraNumero(fd.get("tensao_suportavel_sistema_interno_kv")),
      };
      try {
        await Api.salvarMedidasRisco(pid, analise.id, payload);
        Util.toast("Medidas de proteção salvas.", "ok");
      } catch (err) { Util.erro(err); }
    });
  }

  // ---------------- Aba 5: Resultado ----------------

  function badgeAtende(atende) {
    if (atende === null || atende === undefined) return '<span class="badge info">não avaliado</span>';
    return atende ? '<span class="badge ok">atende</span>' : '<span class="badge alerta">NÃO atende</span>';
  }

  async function renderAbaResultado(el, analise) {
    const pid = State.getProjetoAtivo().id;
    let resultado = null;
    try { resultado = await Api.obterResultadoRisco(pid, analise.id); } catch (e) { /* ainda não calculado */ }

    el.innerHTML = `
      <div class="toolbar"><button class="btn" id="btn-calcular">Calcular / Recalcular</button>
        ${resultado ? '<button class="btn secundario" id="btn-memoria">Ver memória de cálculo</button>' : ""}
      </div>
      <div id="resultado-conteudo">
        ${resultado ? renderResultadoHtml(resultado) : '<div class="vazio">Ainda não calculado. Cadastre estrutura, ao menos uma zona e as medidas de proteção, depois clique em Calcular.</div>'}
      </div>
    `;

    el.querySelector("#btn-calcular").addEventListener("click", async () => {
      try {
        const novoResultado = await Api.calcularRisco(pid, analise.id);
        Util.toast("Cálculo concluído.", "ok");
        renderAbaResultado(el, analise);
      } catch (err) { Util.erro(err); }
    });
    const btnMemoria = el.querySelector("#btn-memoria");
    if (btnMemoria) btnMemoria.addEventListener("click", () => abrirModalMemoria(pid, analise.id));
  }

  function renderResultadoHtml(r) {
    return `
      <div class="kpi-row">
        <div class="kpi"><div class="rotulo">R1 (perda de vida humana)</div><div class="valor">${Util.fmt(r.r1, 8)}</div><div>RT1 = ${Util.fmt(r.rt1, 8)} ${badgeAtende(r.r1_atende)}</div></div>
        <div class="kpi"><div class="rotulo">R3 (patrimônio cultural)</div><div class="valor">${r.r3 !== null ? Util.fmt(r.r3, 8) : "-"}</div><div>${r.r3 !== null ? `RT3 = ${Util.fmt(r.rt3, 8)} ${badgeAtende(r.r3_atende)}` : "nenhuma zona com valor de patrimônio cultural"}</div></div>
        <div class="kpi"><div class="rotulo">F (frequência de danos, Seção 7)</div><div class="valor">${Util.fmt(r.f_total, 6)}</div><div>FT = ${Util.fmt(r.ft, 3)} ${badgeAtende(r.f_atende)}</div></div>
      </div>
      <p style="font-size:12px;color:var(--cinza);margin-top:10px">Calculado em ${new Date(r.data_calculo).toLocaleString("pt-BR")}. R4 (perda de valor econômico) ainda não implementado nesta versão.</p>
    `;
  }

  async function abrirModalMemoria(pid, analiseId) {
    const mem = await Api.obterMemoriaRisco(pid, analiseId);
    Util.abrirModal(`
      ${Util.cabecalhoModal("Memória de cálculo")}
      <div style="max-height:70vh;overflow:auto">
        ${mem.passos.map((p) => `
          <div class="memoria-passo">
            <h4>${Util.esc(p.titulo)}</h4>
            <ul>${p.linhas.map((l) => `<li>${Util.esc(l)}</li>`).join("")}</ul>
            ${p.resultado !== null && p.resultado !== undefined ? `<span class="resultado">${typeof p.resultado === "number" ? Util.fmt(p.resultado, 8) : Util.esc(p.resultado)}</span>` : ""}
          </div>
        `).join("")}
      </div>
      <div class="modal-footer"><button type="button" class="btn secundario" data-fechar>Fechar</button></div>
    `, null, { larga: true });
  }

  return { render };
})();
