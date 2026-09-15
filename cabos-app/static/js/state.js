const State = (() => {
  let projetos = [];
  let projetoAtivo = null;
  let telaAtiva = "projetos";

  const TELAS = [
    { id: "projetos", label: "Projetos", exigeProjeto: false },
    { id: "equipamentos", label: "Equipamentos", exigeProjeto: true },
    { id: "infraestrutura", label: "Eletrodutos/Bandejas", exigeProjeto: true },
    { id: "cabos", label: "Cabos", exigeProjeto: true },
    { id: "cargas", label: "Cargas e Demanda", exigeProjeto: true },
    { id: "relatorios", label: "Relatórios", exigeProjeto: true },
    { id: "config", label: "Configurações/Normas", exigeProjeto: false },
    { id: "perfil", label: "👤 Meu Perfil", exigeProjeto: false },
    { id: "admin", label: "👨‍💼 Administração", exigeProjeto: false, apenasAdmin: true },
  ];

  function getProjetos() { return projetos; }
  function setProjetos(p) { projetos = p; }
  function getProjetoAtivo() { return projetoAtivo; }

  function setProjetoAtivo(p) {
    projetoAtivo = p;
    try {
      if (p) localStorage.setItem("projeto_ativo_id", p.id);
      else localStorage.removeItem("projeto_ativo_id");
    } catch (e) { /* ignore */ }
  }

  function getTelaAtiva() { return telaAtiva; }
  function setTelaAtiva(t) { telaAtiva = t; }

  return { TELAS, getProjetos, setProjetos, getProjetoAtivo, setProjetoAtivo, getTelaAtiva, setTelaAtiva };
})();
