// Cria elementos sem innerHTML: todo texto entra como texto, então nada que o
// usuário (ou a IA) escreva vira código na página.

export function h(tag, atributos = {}, ...filhos) {
  const el = document.createElement(tag);
  for (const [nome, valor] of Object.entries(atributos || {})) {
    if (valor === false || valor === null || valor === undefined) continue;
    if (nome.startsWith("on") && typeof valor === "function") {
      el.addEventListener(nome.slice(2), valor);
    } else if (nome === "class") {
      el.className = valor;
    } else if (nome === "dados") {
      Object.assign(el.dataset, valor);
    } else if (valor === true) {
      el.setAttribute(nome, "");
    } else {
      el.setAttribute(nome, String(valor));
    }
  }
  for (const filho of filhos.flat()) {
    if (filho === null || filho === undefined || filho === false) continue;
    el.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
  return el;
}

let tempoAviso;
export function avisar(mensagem, tipo = "ok") {
  const aviso = document.getElementById("aviso");
  aviso.textContent = mensagem;
  aviso.dataset.tipo = tipo;
  aviso.hidden = false;
  clearTimeout(tempoAviso);
  tempoAviso = setTimeout(() => (aviso.hidden = true), 3600);
}

// Campo com rótulo e espaço para a mensagem de erro.
export function campo(rotulo, entrada, ajuda) {
  const id = entrada.id || `c-${Math.random().toString(36).slice(2, 8)}`;
  entrada.id = id;
  const erro = h("p", { class: "campo__erro", id: `${id}-erro`, hidden: true });
  const partes = [h("label", { for: id }, rotulo), entrada];
  if (ajuda) {
    partes.push(h("p", { class: "campo__ajuda", id: `${id}-ajuda` }, ajuda));
    entrada.setAttribute("aria-describedby", `${id}-ajuda`);
  }
  partes.push(erro);
  return h("div", { class: "campo" }, partes);
}

// Mostra os erros que a API devolveu ao lado de cada campo do formulário.
export function mostrarErros(formulario, erro) {
  formulario.querySelectorAll(".campo__erro").forEach((p) => (p.hidden = true));
  formulario.querySelectorAll("[aria-invalid]").forEach((e) => e.removeAttribute("aria-invalid"));
  let algum = false;
  for (const { campo: nome, mensagem } of erro.campos || []) {
    const entrada = formulario.querySelector(`[name="${CSS.escape(nome)}"]`);
    const alvo = entrada && formulario.querySelector(`#${CSS.escape(entrada.id)}-erro`);
    if (alvo) {
      alvo.textContent = traduzir(mensagem);
      alvo.hidden = false;
      entrada.setAttribute("aria-invalid", "true");
      if (!algum) entrada.focus();
      algum = true;
    }
  }
  return algum;
}

function traduzir(mensagem) {
  if (/at least (\d+) character/.test(mensagem)) return `Use pelo menos ${mensagem.match(/(\d+)/)[1]} caracteres.`;
  if (/valid email/i.test(mensagem)) return "Digite um e-mail válido.";
  if (/greater than or equal/.test(mensagem)) return "Valor muito baixo.";
  if (/less than or equal/.test(mensagem)) return "Valor muito alto.";
  if (/valid date/i.test(mensagem)) return "Digite uma data válida.";
  if (/required/i.test(mensagem)) return "Preencha este campo.";
  return mensagem.replace(/^Value error, /, "");
}

export function ocupado(botao, sim, texto) {
  if (sim) {
    botao.dataset.texto = botao.textContent;
    botao.textContent = texto || "Aguarde…";
    botao.disabled = true;
  } else {
    botao.textContent = botao.dataset.texto || botao.textContent;
    botao.disabled = false;
  }
}
