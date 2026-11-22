import { api } from "../api.js";
import { avisar, h, ocupado } from "../util/dom.js";
import { dataCurta, plural, prazo } from "../util/datas.js";

const ROTULO_ESTADO = { vencido: "Vencido", atencao: "Vence logo", ok: "Em dia" };

export async function telaPainel(principal, app) {
  principal.append(h("p", { class: "carregando" }, "Carregando validades…"));
  let lotes, resumo;
  try {
    [lotes, resumo] = await Promise.all([api("GET", "/api/lotes"), api("GET", "/api/alertas/resumo")]);
  } catch (erro) {
    principal.replaceChildren(h("p", { class: "alerta alerta--erro" }, erro.message));
    return;
  }
  principal.replaceChildren(cabecalho(resumo, app, lotes.length), lista(lotes, app));
}

function frase(resumo) {
  if (resumo.vencidos === 0 && resumo.atencao === 0) return "Nada vence nos próximos dias.";
  const partes = [];
  if (resumo.vencidos) partes.push(`${plural(resumo.vencidos, "lote vencido", "lotes vencidos")} para retirar`);
  if (resumo.atencao) partes.push(`${plural(resumo.atencao, "lote", "lotes")} para vender primeiro`);
  return partes.join(" e ") + ".";
}

function cabecalho(resumo, app, total) {
  const acoes = h("div", { class: "resumo__acoes" });
  if (resumo.vencidos || resumo.atencao) {
    if (resumo.link_whatsapp) {
      acoes.append(
        h("a", { class: "botao botao--zap", href: resumo.link_whatsapp, target: "_blank", rel: "noopener noreferrer" }, "Mandar resumo no WhatsApp")
      );
    }
    const copiar = h("button", { class: "botao botao--claro", type: "button" }, "Copiar resumo");
    copiar.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(resumo.mensagem);
        avisar("Resumo copiado.");
      } catch {
        avisar("Não foi possível copiar neste navegador.", "erro");
      }
    });
    acoes.append(copiar);
    if (!resumo.link_whatsapp) {
      acoes.append(h("a", { class: "botao-texto", href: "#/ajustes" }, "Cadastrar WhatsApp para mandar o resumo"));
    }
  }

  return h(
    "section",
    { class: "resumo", "aria-labelledby": "titulo-resumo" },
    h("h1", { id: "titulo-resumo", class: "resumo__frase" }, total ? frase(resumo) : "Nenhum produto cadastrado ainda."),
    total
      ? h(
          "ul",
          { class: "contagem", "aria-label": "Contagem por situação" },
          h("li", { class: "contagem__item contagem__item--vencido" }, h("strong", {}, String(resumo.vencidos)), " vencidos"),
          h("li", { class: "contagem__item contagem__item--atencao" }, h("strong", {}, String(resumo.atencao)), ` em até ${app.conta.loja.dias_alerta} dias`),
          h("li", { class: "contagem__item contagem__item--ok" }, h("strong", {}, String(resumo.ok)), " em dia")
        )
      : null,
    acoes.childElementCount ? acoes : null
  );
}

function lista(lotes, app) {
  if (!lotes.length) {
    return h(
      "section",
      { class: "vazio" },
      h("p", {}, "Fotografe a data de validade do primeiro produto que chegou. Em poucos segundos ele aparece aqui."),
      h("a", { class: "botao botao--principal", href: "#/adicionar" }, "Adicionar produto")
    );
  }
  return h(
    "section",
    { "aria-labelledby": "titulo-lista" },
    h("h2", { id: "titulo-lista", class: "secao__titulo" }, "Por ordem de vencimento"),
    h("ul", { class: "lotes" }, lotes.map((lote) => itemLote(lote, app)))
  );
}

function itemLote(lote, app) {
  const p = prazo(lote.dias_restantes);
  const acoes = h("div", { class: "lote__acoes" });
  const item = h(
    "li",
    { class: `lote lote--${lote.estado}` },
    h(
      "div",
      { class: "lote__prazo", "aria-hidden": "true" },
      h("strong", {}, p.grande),
      h("span", {}, p.pequeno)
    ),
    h(
      "div",
      { class: "lote__info" },
      h("p", { class: "lote__nome" }, lote.produto_nome),
      h(
        "p",
        { class: "lote__meta" },
        h("span", { class: "etiqueta-estado" }, ROTULO_ESTADO[lote.estado]),
        ` ${plural(lote.quantidade, "unidade", "unidades")}, validade ${dataCurta(lote.validade)}`
      )
    ),
    acoes
  );

  function botoesNormais() {
    acoes.replaceChildren(
      h("button", { class: "botao botao--pequeno botao--claro", type: "button", onclick: () => pedirConfirmacao("vendido") }, "Vendi tudo"),
      h("button", { class: "botao botao--pequeno botao--perigo", type: "button", onclick: () => pedirConfirmacao("descartado") }, "Descartei")
    );
  }

  function pedirConfirmacao(motivo) {
    const confirmar = h(
      "button",
      { class: `botao botao--pequeno ${motivo === "descartado" ? "botao--perigo-cheio" : "botao--escuro"}`, type: "button" },
      motivo === "vendido" ? "Confirmar venda" : "Confirmar descarte"
    );
    confirmar.addEventListener("click", async () => {
      ocupado(confirmar, true);
      try {
        await api("POST", `/api/lotes/${lote.id}/baixa`, { motivo });
        avisar(motivo === "vendido" ? `${lote.produto_nome}: venda registrada.` : `${lote.produto_nome}: descarte registrado.`);
        app.ir("/painel");
      } catch (erro) {
        avisar(erro.message, "erro");
        ocupado(confirmar, false);
      }
    });
    acoes.replaceChildren(
      h("span", { class: "lote__pergunta" }, "Tirar este lote da lista?"),
      confirmar,
      h("button", { class: "botao botao--pequeno botao--claro", type: "button", onclick: botoesNormais }, "Voltar")
    );
    confirmar.focus();
  }

  botoesNormais();
  return item;
}
