import { api } from "../api.js";
import { avisar, campo, h, mostrarErros, ocupado } from "../util/dom.js";

export function telaAjustes(principal, app) {
  const loja = app.conta.loja;
  const nome = h("input", { name: "nome", required: true, maxlength: 80, value: loja.nome });
  const dias = h("input", { name: "dias_alerta", type: "number", inputmode: "numeric", min: 1, max: 60, value: String(loja.dias_alerta) });
  const whatsapp = h("input", {
    name: "whatsapp",
    type: "tel",
    inputmode: "tel",
    autocomplete: "tel-national",
    placeholder: "81 99999-9999",
    value: loja.whatsapp || "",
  });
  const salvar = h("button", { class: "botao botao--principal", type: "submit" }, "Salvar ajustes");
  const erroGeral = h("p", { class: "alerta alerta--erro", role: "alert", hidden: true });

  const form = h(
    "form",
    { class: "cartao formulario", novalidate: true },
    erroGeral,
    campo("Nome da loja", nome),
    campo("Avisar quantos dias antes de vencer", dias, "Com 7, um produto que vence em até 7 dias já aparece como \"vence logo\"."),
    campo("WhatsApp para o resumo diário", whatsapp, "Com DDD. É para onde o resumo será mandado."),
    salvar
  );

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    erroGeral.hidden = true;
    ocupado(salvar, true, "Salvando…");
    try {
      const nova = await api("PATCH", "/api/contas/loja", {
        nome: nome.value,
        dias_alerta: Number(dias.value),
        whatsapp: whatsapp.value,
      });
      app.definirConta({ ...app.conta, loja: nova });
      avisar("Ajustes salvos.");
    } catch (erro) {
      if (!mostrarErros(form, erro)) {
        erroGeral.textContent = erro.message;
        erroGeral.hidden = false;
      }
    } finally {
      ocupado(salvar, false);
    }
  });

  const sair = h("button", { class: "botao botao--claro botao--largo", type: "button" }, "Sair da conta");
  sair.addEventListener("click", async () => {
    try {
      await api("POST", "/api/contas/sair");
    } finally {
      app.definirConta(null);
      app.ir("/entrar");
    }
  });

  principal.append(
    h("h1", { class: "tela__titulo" }, "Ajustes"),
    form,
    h(
      "section",
      { class: "cartao cartao--sutil" },
      h("h2", { class: "secao__titulo" }, "Conta"),
      h("p", {}, `Você entrou como ${app.conta.usuario.email}.`),
      h("p", { class: "campo__ajuda" }, "Para usar como aplicativo: no menu do navegador, toque em \"Adicionar à tela inicial\"."),
      sair
    )
  );
}
