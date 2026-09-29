const TelaRisco5419 = (() => {
  async function render(el) {
    const pid = State.getProjetoAtivo().id;
    el.innerHTML = '<div class="vazio">Carregando…</div>';
    const analises = await Api.listarAnalisesRisco(pid);
    desenhar(el, analises);
  }

  function desenhar(el, analises) {
    const pid = State.getProjetoAtivo().id;
    el.innerHTML = `
      <div class="card">
        <div class="toolbar">
          <h2 style="margin:0">Análise de Risco de Descargas Atmosféricas (NBR 5419-2)</h2>
          <div class="spacer"></div>
          <button class="btn" id="btn-nova-analise">+ Nova análise</button>
        </div>
        <div class="info-box">
          Cálculo de risco (R1, R3, R4) e frequência de danos (F) conforme o Projeto de Revisão
          ABNT NBR 5419-2 (JUL/2025). Esta tela cobre, por ora, o cadastro da análise e a resolução
          da densidade de descargas atmosféricas (NG) — manual ou por município (Anexo F). O motor
          de cálculo completo (R1/R3/R4/F) é etapa futura.
        </div>
        ${analises.length === 0 ? '<div class="vazio">Nenhuma análise cadastrada para este projeto.</div>' : `
        <div class="wrap-table">
          <table class="grid">
            <thead><tr>
              <th>TAG / Estrutura</th><th>Origem do NG</th><th class="num">NG (raios/km²·ano)</th>
              <th>Referência</th><th>Situação</th><th class="acoes-col">Ações</th>
            </tr></thead>
            <tbody>
              ${analises.map((a) => `
                <tr>
                  <td>${Util.esc(a.tag)}</td>
                  <td>${a.ng_modo === "municipio" ? `Município: ${Util.esc(a.ng_municipio)}/${Util.esc(a.ng_uf)}` : "Manual"}</td>
                  <td class="num">${Util.fmt(a.ng_valor, 1)}</td>
                  <td style="font-size:12px;color:var(--cinza)">${Util.esc(a.ng_referencia)}</td>
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

    el.querySelectorAll("[data-remover]").forEach((b) => b.addEventListener("click", async () => {
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
    let municipioEscolhido = null; // {municipio, uf, ng}

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

  return { render };
})();
