// Datas chegam da API como "AAAA-MM-DD". Montamos a data sem fuso para não "voltar um dia".

export function paraData(iso) {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(a, m - 1, d);
}

export function dataCurta(iso) {
  return paraData(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export function dataLonga(iso) {
  return paraData(iso).toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
}

export function hojeISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// Texto curto para a etiqueta do lote.
export function prazo(dias) {
  if (dias < 0) return { grande: "Venceu", pequeno: dias === -1 ? "ontem" : `há ${-dias} dias` };
  if (dias === 0) return { grande: "Hoje", pequeno: "último dia" };
  if (dias === 1) return { grande: "1", pequeno: "dia" };
  return { grande: String(dias), pequeno: "dias" };
}

export function plural(n, um, varios) {
  return `${n} ${n === 1 ? um : varios}`;
}
