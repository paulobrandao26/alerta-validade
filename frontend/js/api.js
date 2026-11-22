// Única porta de saída para o servidor. Toda chamada leva o cabeçalho anti-CSRF
// e o cookie de sessão (httpOnly: o JavaScript nunca vê o token).

const CABECALHOS = { "X-Requested-With": "validade-certa" };

export class ErroApi extends Error {
  constructor(status, mensagem, campos = []) {
    super(mensagem);
    this.status = status;
    this.campos = campos;
  }
}

export async function api(metodo, rota, corpo) {
  const opcoes = { method: metodo, headers: { ...CABECALHOS }, credentials: "same-origin" };
  if (corpo instanceof FormData) {
    opcoes.body = corpo;
  } else if (corpo !== undefined) {
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo);
  }

  let resposta;
  try {
    resposta = await fetch(rota, opcoes);
  } catch {
    throw new ErroApi(0, "Sem conexão. Confira a internet e tente de novo.");
  }
  if (resposta.status === 204) return null;

  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    if (resposta.status === 401 && !rota.startsWith("/api/contas/")) {
      window.dispatchEvent(new Event("sessao-expirada"));
    }
    throw new ErroApi(resposta.status, dados.detail || "Algo deu errado. Tente de novo.", dados.campos || []);
  }
  return dados;
}
