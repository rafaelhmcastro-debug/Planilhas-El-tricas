const TelaRelatorios = (() => {
  async function render(el) {
    const projeto = State.getProjetoAtivo();
    el.innerHTML = `
      <div class="card">
        <h2>Relatórios — ${Util.esc(projeto.numero_projeto)} ${Util.esc(projeto.nome_projeto)}</h2>
        <p style="color:var(--cinza);font-size:13px;margin-top:-6px">Todas as exportações são geradas em Excel (.xlsx) com os dados atuais do projeto ativo.</p>
        <div class="form-grid">
          ${botao("Lista de Equipamentos", "Potências (P, Q, S), rendimento, corrente nominal e painel de cada carga.", "equipamentos.xlsx")}
          ${botao("Lista de Cabos", "Layout PE-E-601: item, TAG, tensão, nº de cabos, nº de condutores, seção, isolamento, De/Para, percurso.", "cabos.xlsx")}
          ${botao("Lista de Eletrodutos/Bandejas", "Item adotado, ocupação efetiva (%), limite, item sugerido e cabos de cada trecho.", "infraestrutura.xlsx")}
          ${botao("Planilha de Cargas e Demanda", "Hierarquia completa: cargas de cada painel, subtotais, painéis a jusante e totais até o TOP.", "cargas-demanda.xlsx")}
          ${botao("Memória de Cálculo", "Uma aba por cabo, com todos os passos do dimensionamento explicados.", "memoria-calculo.xlsx")}
        </div>
      </div>
    `;
  }

  function botao(titulo, descricao, arquivo) {
    const pid = State.getProjetoAtivo().id;
    return `
      <div class="campo">
        <label>${titulo}</label>
        <small class="ajuda" style="min-height:32px">${descricao}</small>
        <a class="btn" href="${Api.urlRelatorio(pid, arquivo)}">Baixar Excel</a>
      </div>
    `;
  }

  return { render };
})();
