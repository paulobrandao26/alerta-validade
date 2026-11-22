import { api } from "../api.js";
import { campo, h, mostrarErros, ocupado } from "../util/dom.js";

export function telaEntrar(principal, app) {
  let modo = "entrar";

  const nomeLoja = h("input", { name: "nome_loja", autocomplete: "organization", maxlength: 80 });
  const email = h("input", { name: "email", type: "email", autocomplete: "email", required: true, inputmode: "email" });
  const senha = h("input", { name: "senha", type: "password", autocomplete: "current-password", required: true, maxlength: 128 });
  const campoLoja = campo("Nome da loja", nomeLoja);
  const erroGeral = h("p", { class: "alerta alerta--erro", role: "alert", hidden: true });
  const botao = h("button", { class: "botao botao--principal", type: "submit" });
  const titulo = h("h1", {});
  const trocar = h("button", { class: "botao-texto", type: "button" });
  const ajudaSenha = h("p", { class: "campo__ajuda" });

  const formulario = h(
    "form",
    { class: "cartao formulario", novalidate: true },
    erroGeral,
    campoLoja,
    campo("E-mail", email),
    campo("Senha", senha),
    ajudaSenha,
    botao
  );

  function desenhar() {
    const cadastro = modo === "cadastro";
    titulo.textContent = cadastro ? "Criar conta da loja" : "Entrar";
    campoLoja.hidden = !cadastro;
    nomeLoja.required = cadastro;
    senha.autocomplete = cadastro ? "new-password" : "current-password";
    ajudaSenha.textContent = cadastro ? "A senha precisa ter pelo menos 8 caracteres." : "";
    ajudaSenha.hidden = !cadastro;
    botao.textContent = cadastro ? "Criar conta" : "Entrar";
    trocar.textContent = cadastro ? "Já tenho conta" : "Criar conta da loja";
    erroGeral.hidden = true;
  }

  trocar.addEventListener("click", () => {
    modo = modo === "entrar" ? "cadastro" : "entrar";
    desenhar();
    (modo === "cadastro" ? nomeLoja : email).focus();
  });

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    erroGeral.hidden = true;
    const dados = { email: email.value, senha: senha.value };
    if (modo === "cadastro") dados.nome_loja = nomeLoja.value;
    ocupado(botao, true);
    try {
      const conta = await api("POST", modo === "cadastro" ? "/api/contas/cadastro" : "/api/contas/entrar", dados);
      app.definirConta(conta);
      app.ir("/painel");
    } catch (erro) {
      if (!mostrarErros(formulario, erro)) {
        erroGeral.textContent = erro.message;
        erroGeral.hidden = false;
      }
    } finally {
      ocupado(botao, false);
    }
  });

  desenhar();
  principal.append(
    h(
      "section",
      { class: "entrada" },
      h(
        "div",
        { class: "entrada__apresentacao" },
        h("p", { class: "entrada__marca" }, "Validade Certa"),
        h("p", { class: "entrada__frase" }, "Saiba hoje o que vence esta semana na sua loja."),
        h("p", { class: "entrada__detalhe" }, "Fotografe a data de validade e a leitura é feita para você.")
      ),
      titulo,
      formulario,
      trocar
    )
  );
}
