import { api, ErroApi } from "./api.js";
import { h } from "./util/dom.js";
import { telaEntrar } from "./telas/entrar.js";
import { telaPainel } from "./telas/painel.js";
import { telaAdicionar } from "./telas/adicionar.js";
import { telaAjustes } from "./telas/ajustes.js";

const TELAS = {
  "/entrar": telaEntrar,
  "/painel": telaPainel,
  "/adicionar": telaAdicionar,
  "/ajustes": telaAjustes,
};

const app = {
  conta: null,
  definirConta(conta) {
    app.conta = conta;
    document.getElementById("nome-loja").textContent = conta ? conta.loja.nome : "";
  },
  ir(caminho) {
    if (location.hash === `#${caminho}`) navegar();
    else location.hash = `#${caminho}`;
  },
};

let saida = null; // limpeza da tela anterior (ex.: parar de consultar a IA)

async function navegar() {
  const caminho = location.hash.slice(1) || "/painel";
  const principal = document.getElementById("tela");

  if (!app.conta && caminho !== "/entrar") {
    try {
      app.definirConta(await api("GET", "/api/contas/eu"));
    } catch (erro) {
      if (erro instanceof ErroApi && erro.status === 0) {
        principal.replaceChildren(
          h("section", { class: "vazio" }, h("h1", {}, "Sem conexão"), h("p", {}, "Conecte-se à internet para ver as validades."))
        );
        return;
      }
      app.ir("/entrar");
      return;
    }
  }
  if (app.conta && caminho === "/entrar") return app.ir("/painel");

  const tela = TELAS[caminho] || telaPainel;
  const logado = Boolean(app.conta);
  document.getElementById("topo").hidden = !logado;
  document.getElementById("abas").hidden = !logado;
  document.querySelectorAll(".abas a").forEach((a) => {
    if (a.dataset.aba === caminho) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });

  if (typeof saida === "function") saida();
  saida = null;
  principal.replaceChildren();
  saida = await tela(principal, app);
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", navegar);
window.addEventListener("sessao-expirada", () => {
  app.definirConta(null);
  app.ir("/entrar");
});

navegar();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
}
