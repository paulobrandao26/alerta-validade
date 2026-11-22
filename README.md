# Validade Certa

Sistema que avisa o dono de um mercado pequeno sobre os produtos vencidos ou perto de vencer. Para cadastrar, basta fotografar a data de validade: uma IA lê a data, a pessoa confere e o lote entra na lista.

## O problema

Mercadinhos e lojas de bairro perdem dinheiro com produto vencido na prateleira, e às vezes levam multa por isso. Grandes redes têm sistemas para isso; os pequenos controlam de cabeça ou no caderno. O motivo de não usarem um sistema é o trabalho de cadastrar a validade de cada produto.

## Como o sistema ataca o trabalho de cadastrar

- **Por lote, não por unidade:** uma caixa com 24 iogurtes da mesma data é um cadastro só.
- **Foto em vez de digitação:** a IA lê a data e o nome do produto; a pessoa só confere.
- **Frescos sem data impressa** (pão, frios): validade = dia da chegada + prazo do produto. Na próxima entrega, o sistema lembra o prazo.
- **O sistema lembra os produtos:** o nome aparece como sugestão, sem duplicar "Leite" e "leite ".
- **Resumo pronto para o WhatsApp:** o que retirar da prateleira e o que vender primeiro.

## Arquitetura

Monólito modular (FastAPI) com uma fila de fotos processada por um worker separado. A IA nunca é chamada durante a requisição: se ela cair, a foto espera na fila e, no limite, vai para preenchimento manual. Detalhes, motivos e pontos negativos em [docs/arquitetura.md](docs/arquitetura.md).

```
app/modules/   contas · produtos · leitura_ia · alertas
app/worker/    processa a fila de fotos
app/seguranca/ senhas, sessão, CSRF, cabeçalhos, limite de tentativas
frontend/      PWA (instala no celular, abre sem internet)
tests/         unitários, integração e avaliação da IA
```

**Tecnologias:** Python, FastAPI, SQLAlchemy 2, Alembic, Pydantic, PostgreSQL (SQLite no computador), IA de visão (Gemini, Groq ou Ollama local, com troca automática entre eles), Pytest, Ruff, Docker Compose, GitHub Actions. Interface em HTML, CSS e JavaScript sem framework.

## Custo zero

- **IA:** Gemini e Groq têm uso gratuito com limite diário; o Ollama roda no próprio computador, sem limite. O sistema tenta um, e se o limite grátis do dia acabar ou ele cair, passa para o próximo. Sem nenhum, a pessoa digita a data.
- **Fotos:** apagadas do servidor assim que a IA termina de ler. Nada para armazenar nem pagar.
- **Digitar continua sendo o caminho principal:** a foto é um atalho.

## Como a IA é tratada

| Situação | O que o sistema faz |
|---|---|
| Leu com confiança e a data é plausível | Mostra a data para a pessoa conferir e salvar |
| Pouca confiança, ou data absurda (ex.: 2019) | Vai para revisão: a sugestão aparece, mas com aviso |
| Respondeu fora do formato JSON combinado | Revisão manual |
| Um provedor fora do ar ou sem limite grátis | O próximo provedor da lista assume na hora |
| Todos fora do ar | Volta para a fila e tenta de novo (30 s, 60 s…); depois de 3 tentativas, revisão manual |
| Nenhum provedor configurado | Leitura desligada; a pessoa digita a data |

Para medir o acerto com fotos reais: [tests/avaliacao_ia/avaliar.py](tests/avaliacao_ia/avaliar.py). **Ainda não foi rodado com fotos reais**, então este projeto não afirma nenhuma taxa de acerto.

## Rodar no computador

Requisitos: Python 3.12 ou mais novo.

```bash
python -m venv .venv
.venv\Scripts\activate            # no Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # preencha SECRET_KEY e, se quiser a leitura por foto, GEMINI_API_KEY (grátis)
uvicorn app.main:criar_app --factory --reload
```

Abra http://localhost:8000. O banco (SQLite) e as migrations são criados sozinhos. O worker roda junto com o servidor.

### Com Docker (PostgreSQL + worker separado)

```bash
cp .env.example .env
docker compose up --build
```

## Testes

```bash
pytest            # 110 testes: regras, API, IA (com servidor falso), segurança, concorrência, isolamento, migrations
ruff check .
```

Alguns dos testes:
- Duas pessoas dão baixa no mesmo lote ao mesmo tempo: só uma vale.
- Dois workers tentam pegar a mesma foto da fila: só um consegue.
- A IA cai três vezes seguidas: a foto não se perde.
- O Gemini estoura o limite grátis: o Groq assume sem a pessoa perceber.
- Depois da leitura, a foto não existe mais no servidor.
- Uma loja tenta ver, baixar ou confirmar dados de outra adivinhando ids: recebe 404.
- Um arquivo que não é foto (HTML, executável, SVG) é recusado mesmo com nome `.jpg`.

## Segurança

Resumo em [docs/seguranca.md](docs/seguranca.md): senhas com Argon2, sessão em cookie HttpOnly/SameSite, proteção contra CSRF, CSP, isolamento entre lojas, validação de upload pelos bytes, limite de tentativas e nenhum detalhe interno em mensagens de erro.

## Limitações conhecidas

O que ainda não funciona ou não foi testado está em [docs/limitacoes.md](docs/limitacoes.md). Principais: ainda sem teste numa loja real, taxa de acerto da IA não medida, WhatsApp por link (não automático) e fila no banco (serve para volume pequeno).

## API

Com o servidor rodando (fora de produção): http://localhost:8000/api/docs
