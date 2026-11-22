"""Mede quantas datas de validade cada IA acerta, usando fotos reais com a resposta certa anotada.

Como usar:
  1. Coloque as fotos em tests/avaliacao_ia/fotos/ (essa pasta não vai para o GitHub).
  2. Anote a data certa de cada foto em tests/avaliacao_ia/gabarito.csv (arquivo;validade).
     Use "sem_data" quando a foto não mostra a validade.
  3. Configure ao menos um provedor no .env (GEMINI_API_KEY, GROQ_API_KEY ou OLLAMA_URL) e rode:
       python -m tests.avaliacao_ia.avaliar
  4. Cada provedor é avaliado separadamente. O resultado sai no terminal e em
     tests/avaliacao_ia/resultado_<provedor>.csv.

Ao trocar o prompt ou o modelo, rode de novo e compare: assim se sabe se melhorou ou piorou.
"""

import csv
import sys
import time
from datetime import date
from pathlib import Path

from app.config import obter_configuracao
from app.modules.leitura_ia.arquivos import descobrir_tipo
from app.modules.leitura_ia.cliente_ia import IAIndisponivel, LeitorComReserva, criar_leitor
from app.modules.leitura_ia.schemas import RespostaIAInvalida

PASTA = Path(__file__).parent
FOTOS = PASTA / "fotos"


def avaliar(leitor, gabarito, confianca_minima: float) -> None:
    linhas, acertos, aceitas, aceitas_certas, falhas, tempos = [], 0, 0, 0, 0, []
    for item in gabarito:
        imagem = (FOTOS / item["arquivo"]).read_bytes()
        esperado = None if item["validade"] == "sem_data" else date.fromisoformat(item["validade"])
        inicio = time.perf_counter()
        try:
            resposta = leitor.ler(imagem, descobrir_tipo(imagem) or "image/jpeg")
            lida, confianca = resposta.validade, resposta.confianca
        except RespostaIAInvalida:
            lida, confianca = None, 0.0
        except IAIndisponivel:
            falhas += 1
            lida, confianca = None, 0.0
        tempos.append(time.perf_counter() - inicio)

        certo = lida == esperado
        aceita = lida is not None and confianca >= confianca_minima
        acertos += certo
        aceitas += aceita
        aceitas_certas += aceita and certo
        linhas.append([item["arquivo"], esperado or "sem_data", lida or "sem_data", f"{confianca:.2f}", certo, aceita])
        print(f"  {'OK  ' if certo else 'ERRO'} {item['arquivo']}: esperado {esperado}, lido {lida} ({confianca:.2f})")

    with (PASTA / f"resultado_{leitor.nome}.csv").open("w", newline="", encoding="utf-8") as saida:
        escritor = csv.writer(saida, delimiter=";")
        escritor.writerow(["arquivo", "esperado", "lido", "confianca", "acertou", "aceita_sem_revisao"])
        escritor.writerows(linhas)

    total = len(gabarito)
    tempos.sort()
    print(f"  Acerto geral da data: {acertos}/{total} ({acertos / total:.0%})")
    print(f"  Aceitas sem revisão (confiança >= {confianca_minima}): {aceitas}/{total}")
    if aceitas:
        print(f"  Precisão das aceitas: {aceitas_certas}/{aceitas} ({aceitas_certas / aceitas:.0%})")
    if falhas:
        print(f"  Sem resposta (limite ou fora do ar): {falhas}")
    print(f"  Tempo por foto: mediana {tempos[len(tempos) // 2]:.1f}s, pior {tempos[-1]:.1f}s\n")


def main() -> int:
    config = obter_configuracao()
    leitor = criar_leitor(config)
    if not isinstance(leitor, LeitorComReserva):
        print("Configure GEMINI_API_KEY, GROQ_API_KEY ou OLLAMA_URL no .env para avaliar a IA.")
        return 1
    gabarito = list(csv.DictReader((PASTA / "gabarito.csv").open(encoding="utf-8"), delimiter=";"))
    if not gabarito:
        print("O gabarito.csv está vazio.")
        return 1
    for provedor in leitor.leitores:
        print(f"== {provedor.nome} ({len(gabarito)} fotos)")
        avaliar(provedor, gabarito, config.ia_confianca_minima)
    return 0


if __name__ == "__main__":
    sys.exit(main())
