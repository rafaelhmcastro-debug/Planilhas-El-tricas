const Api = (() => {
  async function req(method, url, body, isForm) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      if (isForm) {
        opts.body = body;
      } else {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
      }
    }
    const resp = await fetch(url, opts);
    if (!resp.ok) {
      let msg = `Erro ${resp.status}`;
      try {
        const data = await resp.json();
        if (Array.isArray(data.detail)) msg = data.detail.map((d) => `${(d.loc || []).slice(-1)[0]}: ${d.msg}`).join("; ");
        else msg = data.detail || JSON.stringify(data);
      } catch (e) { /* ignore */ }
      throw new Error(msg);
    }
    if (resp.status === 204) return null;
    const ct = resp.headers.get("content-type") || "";
    if (ct.includes("application/json")) return resp.json();
    return resp;
  }

  const get = (url) => req("GET", url);
  const post = (url, body) => req("POST", url, body);
  const put = (url, body) => req("PUT", url, body);
  const del = (url) => req("DELETE", url);
  const postForm = (url, form) => req("POST", url, form, true);

  return {
    // Projetos
    listarProjetos: () => get("/api/projetos"),
    criarProjeto: (p) => post("/api/projetos", p),
    atualizarProjeto: (id, p) => put(`/api/projetos/${id}`, p),
    removerProjeto: (id) => del(`/api/projetos/${id}`),

    // Equipamentos
    listarEquipamentos: (pid) => get(`/api/projetos/${pid}/equipamentos`),
    criarEquipamento: (pid, e) => post(`/api/projetos/${pid}/equipamentos`, e),
    atualizarEquipamento: (pid, id, e) => put(`/api/projetos/${pid}/equipamentos/${id}`, e),
    removerEquipamento: (pid, id, force) => del(`/api/projetos/${pid}/equipamentos/${id}${force ? "?force=true" : ""}`),
    duplicarEquipamento: (pid, id, novaTag) => post(`/api/projetos/${pid}/equipamentos/${id}/duplicar?nova_tag=${encodeURIComponent(novaTag)}`),
    uploadEquipamentoArquivo: (pid, id, campo, form) => postForm(`/api/projetos/${pid}/equipamentos/${id}/upload?campo=${campo}`, form),

    // Infraestrutura
    listarInfra: (pid) => get(`/api/projetos/${pid}/eletrodutos-bandejas`),
    criarInfra: (pid, i) => post(`/api/projetos/${pid}/eletrodutos-bandejas`, i),
    atualizarInfra: (pid, id, i) => put(`/api/projetos/${pid}/eletrodutos-bandejas/${id}`, i),
    removerInfra: (pid, id) => del(`/api/projetos/${pid}/eletrodutos-bandejas/${id}`),
    ocupacaoInfra: (pid, id) => get(`/api/projetos/${pid}/eletrodutos-bandejas/${id}/ocupacao`),

    // Cabos
    listarCabos: (pid) => get(`/api/projetos/${pid}/cabos`),
    criarCabo: (pid, c) => post(`/api/projetos/${pid}/cabos`, c),
    atualizarCabo: (pid, id, c) => put(`/api/projetos/${pid}/cabos/${id}`, c),
    removerCabo: (pid, id) => del(`/api/projetos/${pid}/cabos/${id}`),
    recalcularTodosCabos: (pid) => post(`/api/projetos/${pid}/cabos/recalcular-todos`),
    trechosDoCabo: (pid, id) => get(`/api/projetos/${pid}/cabos/${id}/trechos`),
    memoriaCalculo: (pid, id) => get(`/api/projetos/${pid}/cabos/${id}/memoria-calculo`),

    // Painéis
    listarPaineis: (pid) => get(`/api/projetos/${pid}/paineis`),
    arvorePaineis: (pid) => get(`/api/projetos/${pid}/paineis/arvore`),
    criarPainel: (pid, p) => post(`/api/projetos/${pid}/paineis`, p),
    equipamentosDoPainel: (pid, id) => get(`/api/projetos/${pid}/paineis/${id}/equipamentos`),
    atualizarPainel: (pid, id, p) => put(`/api/projetos/${pid}/paineis/${id}`, p),
    removerPainel: (pid, id) => del(`/api/projetos/${pid}/paineis/${id}`),

    // Catálogos
    catalogoCabos: (params) => get(`/api/catalogos/cabos?${new URLSearchParams(params || {})}`),
    criarCatalogoCabo: (c) => post("/api/catalogos/cabos", c),
    atualizarCatalogoCabo: (id, c) => put(`/api/catalogos/cabos/${id}`, c),
    removerCatalogoCabo: (id) => del(`/api/catalogos/cabos/${id}`),
    catalogoInfra: (params) => get(`/api/catalogos/infraestrutura?${new URLSearchParams(params || {})}`),
    criarInfraCustomizada: (payload) => post("/api/catalogos/infraestrutura/customizada", payload),
    importarCatalogoCabos: (form, substituir) => postForm(`/api/catalogos/cabos/importar?substituir=${!!substituir}`, form),
    importarCatalogoInfra: (form, substituir) => postForm(`/api/catalogos/infraestrutura/importar?substituir=${!!substituir}`, form),
    importarCapacidade: (form) => postForm(`/api/catalogos/normas/capacidade-conducao/importar?substituir=true`, form),
    urlModeloCabos: "/api/catalogos/cabos/modelo.xlsx",
    urlModeloInfra: "/api/catalogos/infraestrutura/modelo.xlsx",
    urlModeloCapacidade: "/api/catalogos/normas/capacidade-conducao/modelo.xlsx",
    tabCapacidade: () => get("/api/catalogos/normas/capacidade-conducao"),
    tabTemperatura: () => get("/api/catalogos/normas/fator-temperatura"),
    tabAgrupamento: () => get("/api/catalogos/normas/fator-agrupamento"),
    tabResistividade: () => get("/api/catalogos/normas/resistividade"),
    tabLimiteEletroduto: () => get("/api/catalogos/normas/limite-ocupacao-eletroduto"),

    // Relatórios (URLs diretas para download)
    urlRelatorio: (pid, nome, params) => `/api/projetos/${pid}/relatorios/${nome}${params ? "?" + new URLSearchParams(params) : ""}`,
  };
})();
