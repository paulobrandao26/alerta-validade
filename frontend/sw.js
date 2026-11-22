// Service worker: deixa o app instalável e abre a "casca" mesmo sem internet.
// Dados da API nunca são guardados em cache (são da loja e mudam o tempo todo).

const VERSAO = "validade-v1";
const CASCA = [
  "/",
  "/index.html",
  "/css/app.css",
  "/js/app.js",
  "/js/api.js",
  "/js/util/dom.js",
  "/js/util/datas.js",
  "/js/util/imagem.js",
  "/js/telas/entrar.js",
  "/js/telas/painel.js",
  "/js/telas/adicionar.js",
  "/js/telas/ajustes.js",
  "/manifest.webmanifest",
  "/icones/icone.svg",
  "/icones/icone-192.png",
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(VERSAO).then((cache) => cache.addAll(CASCA)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((nomes) => Promise.all(nomes.filter((n) => n !== VERSAO).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (evento) => {
  const pedido = evento.request;
  const url = new URL(pedido.url);
  if (pedido.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;

  // Rede primeiro (sempre a versão mais nova); sem internet, usa a cópia guardada.
  evento.respondWith(
    fetch(pedido)
      .then((resposta) => {
        if (resposta.ok) {
          const copia = resposta.clone();
          caches.open(VERSAO).then((cache) => cache.put(pedido, copia));
        }
        return resposta;
      })
      .catch(() =>
        caches
          .match(pedido)
          .then((guardada) => guardada || (pedido.mode === "navigate" ? caches.match("/index.html") : Response.error()))
      )
  );
});
