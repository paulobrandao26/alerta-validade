import { api } from "../api.js";
import { avisar, campo, h, mostrarErros, ocupado } from "../util/dom.js";
import { dataLonga, hojeISO } from "../util/datas.js";
import { prepararFoto } from "../util/imagem.js";

const INTERVALO_CONSULTA = 1500;
const TEMPO_MAXIMO_ESPERA = 90_000;

export function telaAdicionar(principal, app) {
  let consulta = null;
  let urlFoto = null;
  const parar = () => {
    clearTimeout(consulta);
    consulta = null;
    if (urlFoto) URL.revokeObjectURL(urlFoto);
    urlFoto = null;
  };

  // Sugestões de nomes já usados na loja (evita "Leite" e "Leite integral" virarem dois produtos).
  const sugestoes = h("datalist", { id: "produtos-existentes" });
  api("GET", "/api/produtos")
    .then((produtos) => sugestoes.replaceChildren(...produtos.map((p) => h("option", { value: p.nome }))))
    .catch(() => {});

  const area = h("div", {});
  principal.append(h("h1", { class: "tela__titulo" }, "Adicionar produto"), sugestoes, area);

  /* ---------- Escolha ---------- */
  function inicio() {
    parar();
    const entradaFoto = h("input", {
      type: "file",
      accept: "image/*",
      capture: "environment",
      class: "visualmente-oculto",
      id: "entrada-foto",
    });
    entradaFoto.addEventListener("change", () => entradaFoto.files[0] && enviarFoto(entradaFoto.files[0]));

    area.replaceChildren(
      h(
        "div",
        { class: "escolha" },
        h(
          "label",
          { class: "escolha__foto", for: "entrada-foto" },
          h("span", { class: "escolha__icone", "aria-hidden": "true" }, iconeCamera()),
          h("strong", {}, "Fotografar a data"),
          h("span", {}, "Aponte para onde está escrito VAL ou VENC.")
        ),
        entradaFoto,
        h("button", { class: "botao botao--claro botao--largo", type: "button", onclick: () => formulario({ modo: "manual" }) }, "Digitar sem foto")
      ),
      !app.conta.ia_ligada
        ? h(
            "p",
            { class: "alerta alerta--info" },
            "A leitura automática está desligada neste servidor. A foto fica guardada e você digita a data na tela seguinte."
          )
        : null
    );
  }

  /* ---------- Foto: envio e espera da IA ---------- */
  async function enviarFoto(arquivo) {
    parar();
    const estado = h("p", { class: "leitura__estado", role: "status" }, "Preparando a foto…");
    const miniatura = h("img", { class: "leitura__foto", alt: "Foto enviada da embalagem" });
    area.replaceChildren(h("div", { class: "leitura" }, miniatura, h("div", {}, estado, h("div", { class: "barra-espera", "aria-hidden": "true" }))));

    const foto = await prepararFoto(arquivo);
    urlFoto = URL.createObjectURL(foto);
    miniatura.src = urlFoto;

    const dados = new FormData();
    dados.append("foto", foto, "embalagem.jpg");
    let leitura;
    try {
      estado.textContent = "Enviando…";
      leitura = await api("POST", "/api/leituras", dados);
    } catch (erro) {
      avisar(erro.message, "erro");
      inicio();
      return;
    }

    estado.textContent = "Lendo a data de validade…";
    const comeco = Date.now();
    const consultar = async () => {
      try {
        leitura = await api("GET", `/api/leituras/${leitura.id}`);
      } catch {
        // falha de rede passageira: tenta de novo no próximo ciclo
      }
      if (leitura.status === "lida" || leitura.status === "revisao") {
        consulta = null;
        formulario({ modo: "foto", leitura, foto: urlFoto });
        return;
      }
      if (leitura.status === "pendente" && leitura.erro) estado.textContent = "A leitura está demorando. Tentando de novo…";
      if (Date.now() - comeco > TEMPO_MAXIMO_ESPERA) {
        consulta = null;
        formulario({ modo: "foto", leitura: { ...leitura, status: "revisao", erro: "A leitura demorou demais. Preencha os dados." }, foto: urlFoto });
        return;
      }
      consulta = setTimeout(consultar, INTERVALO_CONSULTA);
    };
    consulta = setTimeout(consultar, 800);
  }

  /* ---------- Conferir / digitar ---------- */
  function formulario({ modo, leitura, foto }) {
    const daFoto = modo === "foto";
    const produto = h("input", {
      name: "produto_nome",
      required: true,
      maxlength: 120,
      list: "produtos-existentes",
      autocomplete: "off",
      value: leitura?.produto_lido || "",
    });
    const validade = h("input", { name: "validade", type: "date", required: true, value: leitura?.validade_lida || "", min: "2020-01-01" });
    const quantidade = h("input", { name: "quantidade", type: "number", inputmode: "numeric", min: 1, max: 100000, required: true, value: "1" });
    const prazoDias = h("input", { name: "prazo_padrao_dias", type: "number", inputmode: "numeric", min: 1, max: 60, value: "2" });
    const fresco = h("input", { type: "checkbox", id: "fresco" });
    const campoValidade = campo("Data de validade", validade);
    const campoPrazo = campo("Dura quantos dias depois que chega?", prazoDias, "Na próxima entrega, o sistema já lembra.");
    campoPrazo.hidden = true;
    fresco.addEventListener("change", () => {
      campoValidade.hidden = fresco.checked;
      campoPrazo.hidden = !fresco.checked;
      validade.required = !fresco.checked;
    });

    const erroGeral = h("p", { class: "alerta alerta--erro", role: "alert", hidden: true });
    const salvar = h("button", { class: "botao botao--principal", type: "submit" }, "Salvar lote");

    let aviso = null;
    if (daFoto && leitura.status === "lida") {
      aviso = h(
        "p",
        { class: "alerta alerta--ok" },
        `Data lida: ${dataLonga(leitura.validade_lida)}. Confira na foto antes de salvar.`
      );
    } else if (daFoto) {
      aviso = h("p", { class: "alerta alerta--atencao" }, leitura.erro || "Confira os dados antes de salvar.");
    }

    const form = h(
      "form",
      { class: "cartao formulario", novalidate: true },
      erroGeral,
      aviso,
      daFoto && foto ? h("img", { class: "formulario__foto", src: foto, alt: "Foto da embalagem para conferir a data" }) : null,
      campo("Produto", produto, "Ex.: Iogurte natural 170g"),
      daFoto ? null : h("div", { class: "campo campo--marcar" }, fresco, h("label", { for: "fresco" }, "Produto fresco, sem data impressa (pão, frios)")),
      campoValidade,
      campoPrazo,
      campo("Quantidade (unidades deste lote)", quantidade),
      h("div", { class: "formulario__acoes" }, salvar, h("button", { class: "botao botao--claro", type: "button", onclick: inicio }, "Cancelar"))
    );

    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      erroGeral.hidden = true;
      if (validade.value && validade.value < hojeISO() && !fresco.checked) {
        // produto já vencido: deixa salvar, mas avisa (pode ser um lote encontrado na prateleira)
        avisar("Esse lote já está vencido. Ele aparece no topo da lista para retirar.", "erro");
      }
      ocupado(salvar, true, "Salvando…");
      try {
        let lote;
        if (daFoto) {
          lote = await api("POST", `/api/leituras/${leitura.id}/confirmar`, {
            produto_nome: produto.value,
            validade: validade.value || null,
            quantidade: Number(quantidade.value),
          });
        } else {
          const corpo = { produto_nome: produto.value, quantidade: Number(quantidade.value) };
          if (fresco.checked) corpo.prazo_padrao_dias = Number(prazoDias.value);
          else corpo.validade = validade.value || null;
          lote = await api("POST", "/api/lotes", corpo);
        }
        avisar(`${lote.produto_nome} salvo.`);
        inicio();
      } catch (erro) {
        if (!mostrarErros(form, erro)) {
          erroGeral.textContent = erro.message;
          erroGeral.hidden = false;
        }
      } finally {
        ocupado(salvar, false);
      }
    });

    area.replaceChildren(form);
    (daFoto && leitura.status === "lida" ? quantidade : produto).focus();
  }

  inicio();
  return parar;
}

function iconeCamera() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  for (const d of ["M3 8h3.5l2-3h7l2 3H21v12H3z", "M12 10a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"]) {
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", d);
    svg.append(p);
  }
  return svg;
}
