const Util = (() => {
  function fmt(n, casas = 2) {
    if (n === null || n === undefined || n === "" || Number.isNaN(Number(n))) return "-";
    return Number(n).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
  }

  function esc(s) {
    if (s === null || s === undefined) return "";
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function toast(msg, tipo = "info") {
    let el = document.getElementById("toast-container");
    if (!el) {
      el = document.createElement("div");
      el.id = "toast-container";
      el.style.cssText = "position:fixed;bottom:16px;right:16px;z-index:100;display:flex;flex-direction:column;gap:8px;";
      document.body.appendChild(el);
    }
    const cores = { info: "#1f4e78", erro: "#c0392b", ok: "#2e7d32" };
    const item = document.createElement("div");
    item.textContent = msg;
    item.style.cssText = `background:${cores[tipo] || cores.info};color:#fff;padding:10px 16px;border-radius:6px;box-shadow:0 4px 10px rgba(0,0,0,.2);font-size:13.5px;max-width:460px;`;
    el.appendChild(item);
    setTimeout(() => item.remove(), tipo === "erro" ? 7000 : 4500);
  }

  function erro(e) {
    toast(e.message || String(e), "erro");
  }

  // O modal só fecha pelos botões (×, Cancelar, Fechar) ou pela tecla Esc — nunca ao clicar fora.
  function abrirModal(html, onMount, opcoes = {}) {
    const root = document.getElementById("modal-root");
    root.innerHTML = `<div class="modal-fundo" id="modal-fundo"><div class="modal ${opcoes.larga ? "larga" : ""}">${html}</div></div>`;
    const fechar = () => fecharModal();
    root.querySelectorAll("[data-fechar]").forEach((b) => b.addEventListener("click", fechar));
    const onKey = (e) => { if (e.key === "Escape") { fecharModal(); document.removeEventListener("keydown", onKey); } };
    document.addEventListener("keydown", onKey);
    if (onMount) onMount(root);
  }

  function fecharModal() {
    document.getElementById("modal-root").innerHTML = "";
  }

  function cabecalhoModal(titulo) {
    return `<div class="modal-header"><h2>${esc(titulo)}</h2><button type="button" data-fechar title="Fechar">&times;</button></div>`;
  }

  function formToObj(form) {
    const data = new FormData(form);
    const obj = {};
    for (const [k, v] of data.entries()) {
      obj[k] = v === "" ? null : v;
    }
    form.querySelectorAll("input[type=checkbox]").forEach((cb) => { obj[cb.name] = cb.checked; });
    return obj;
  }

  function paraNumero(v) {
    if (v === null || v === undefined || v === "") return null;
    let s = String(v).trim();
    if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
    const n = Number(s);
    return Number.isNaN(n) ? null : n;
  }

  function confirmar(msg) { return window.confirm(msg); }

  return { fmt, esc, toast, erro, abrirModal, fecharModal, cabecalhoModal, formToObj, paraNumero, confirmar };
})();
