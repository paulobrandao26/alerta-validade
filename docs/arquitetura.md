# Arquitetura

## Escolha: monólito modular com fila de tarefas

Uma aplicação só (FastAPI), dividida em módulos por assunto. A leitura da foto pela IA roda fora da requisição, num worker que consome uma fila guardada no próprio banco.

```
Celular (PWA)
   │  foto
   ▼
API (FastAPI) ──► grava a foto e cria uma "leitura" pendente ──► responde 202 na hora
                                   │
                                   ▼
                         Worker (fila no banco)
                                   │  chama a IA: Gemini → Groq → Ollama (o próximo assume se um falhar)
                                   ▼
                  JSON validado ──► "lida" ou "revisão manual" ──► foto apagada do servidor
                                   │
Celular consulta a leitura ◄───────┘
   │  a pessoa confere e confirma
   ▼
Lote gravado (produto + quantidade + validade) ──► alertas e resumo do WhatsApp
```

### Por que essa e não outra

| Opção | Por que não (agora) |
|---|---|
| Microsserviços | Uma pessoa mantendo vários serviços, redes e deploys. Complexidade sem ganho para o tamanho do problema. |
| Monólito sem fila | A IA leva segundos e às vezes cai. Chamar a IA dentro da requisição deixa o app travado e perde a foto quando a IA falha. |
| Fila com Redis/RabbitMQ | Mais uma peça para instalar. Para o volume de mercados pequenos, uma tabela no banco com reivindicação atômica resolve. |

### Pontos positivos
- Sobe com um comando e roda inteiro no computador (SQLite) ou no Docker (PostgreSQL).
- Falha da IA não derruba nada: a foto fica na fila, tenta de novo com espera crescente e, no fim, vai para preenchimento manual.
- Cada módulo tem a mesma forma, então é fácil achar as coisas.

### Pontos negativos
- Escala como um bloco: se a leitura de fotos crescer muito, não dá para escalar só ela (dá para rodar mais workers, mas o resto vai junto).
- A fila no banco é consultada de tempos em tempos (polling a cada 2 s). Com milhares de lojas, o certo é trocar por uma fila de verdade.
- Exige disciplina: um módulo só deve conversar com outro pelos serviços, nunca mexendo direto nas tabelas do outro.

## Organização

```
app/
  main.py                 monta a aplicação (rotas, proteções, worker, interface)
  config.py               variáveis de ambiente, com validação
  nucleo/                 coisas usadas por todos: relógio e erros de negócio
  db/                     conexão, base dos modelos e migrations (Alembic)
  seguranca/              senhas (Argon2), sessão (JWT em cookie), CSRF, cabeçalhos, limitador
  modules/
    contas/               loja e usuário: cadastro, entrar, sair, ajustes
    produtos/             produtos e lotes (validade, quantidade, baixa)
    leitura_ia/           foto → fila → IA → JSON validado → confirmação
    alertas/              regra de vencimento, resumo diário, link do WhatsApp
  worker/                 processa a fila (embutido ou como processo separado)
frontend/                 PWA em HTML, CSS e JavaScript puro (sem build)
tests/
  unitarios/              regras puras (sem banco)
  integracao/             API de ponta a ponta com banco de verdade (SQLite)
  avaliacao_ia/           mede o acerto da IA com fotos reais
docs/                     arquitetura, segurança e limitações
```

Cada módulo segue o mesmo padrão:

| Arquivo | Papel |
|---|---|
| `modelos.py` | tabelas (SQLAlchemy) |
| `schemas.py` | formato e validação do que entra e sai (Pydantic) |
| `repositorio.py` | consultas ao banco, sempre filtradas pela loja |
| `servico.py` | regras de negócio |
| `rotas.py` | endpoints HTTP (fino: só chama o serviço) |

## Decisões que valem destacar

- **A IA nunca grava nada sozinha.** Ela sugere; a pessoa confirma. Uma data errada vira um produto vencido na prateleira.
- **A resposta da IA tem contrato.** JSON com `produto`, `validade` (AAAA-MM-DD) e `confianca` (0 a 1), validado pelo Pydantic. Fora disso, vai para revisão manual. Datas implausíveis (mais de 1 ano atrás ou 5 anos à frente) também.
- **Vários provedores de IA, um cliente só.** Gemini, Groq e Ollama aceitam o mesmo formato de pedido (API de chat no padrão da OpenAI), então um único `LeitorCompativelOpenAI` atende os três, e o `LeitorComReserva` passa para o próximo quando um falha. A ordem e os provedores ativos vêm do `.env`. O resto do sistema só conhece a interface `LeitorDeEmbalagem`.
- **Custo zero como requisito.** Os provedores escolhidos têm uso gratuito, a foto é apagada assim que é lida (nada de armazenamento pago) e a digitação continua sendo o caminho principal.
- **Concorrência resolvida no banco.** Baixa de lote, confirmação de leitura e reivindicação da fila usam `UPDATE ... WHERE status = <esperado>` e conferem quantas linhas mudaram. Dois toques ao mesmo tempo nunca contam duas vezes (há testes para isso).
- **Transações.** Criar lote cria o produto junto; se algo falha, nada fica gravado pela metade.
