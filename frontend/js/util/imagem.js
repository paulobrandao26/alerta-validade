// Reduz a foto no próprio celular antes de enviar:
// - fica bem menor (envio rápido mesmo no 4G fraco);
// - vira JPEG (fotos HEIC do iPhone também funcionam);
// - perde os metadados (EXIF), que podem trazer a localização GPS de quem tirou.

const LADO_MAXIMO = 1600;

export async function prepararFoto(arquivo) {
  try {
    const bitmap = await createImageBitmap(arquivo, { imageOrientation: "from-image" });
    const escala = Math.min(1, LADO_MAXIMO / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * escala);
    canvas.height = Math.round(bitmap.height * escala);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close?.();
    const blob = await new Promise((ok) => canvas.toBlob(ok, "image/jpeg", 0.85));
    if (blob) return blob;
  } catch {
    // navegador antigo: envia o arquivo original (o servidor valida do mesmo jeito)
  }
  return arquivo;
}
