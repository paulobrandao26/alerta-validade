# Limitações conhecidas

Escritas de propósito: saber onde a solução para é parte da solução.

## Produto
- **Ainda não foi testado numa loja de verdade.** As regras (lote, prazo de alerta, frescos) vêm de conversa, não de uso. O próximo passo é medir com um mercado quanto tempo leva cadastrar uma entrega.
- **A data impressa precisa ser mostrada ao sistema.** Não existe automação que descubra a validade sem ver a embalagem. A nota fiscal (XML) traz produtos e quantidades, mas quase nunca a validade; a importação da nota ainda não foi feita.
- **O resumo do WhatsApp é por link.** A pessoa toca e o WhatsApp abre com a mensagem pronta. O envio automático todo dia exige a API oficial do WhatsApp Business (conta aprovada e custo por mensagem).
- **Um usuário por loja.** Funcionários usam a mesma conta.
- **Sem recuperação de senha.**
- **Sem leitor de código de barras pela câmera.** O campo existe na API, mas a interface ainda não lê.

## IA
- **A taxa de acerto ainda não foi medida com fotos reais.** O roteiro existe (`tests/avaliacao_ia/avaliar.py`), mas o gabarito está vazio. Nenhum número de acerto é afirmado até ele ser rodado.
- Datas em jato de tinta, em embalagem curva, borradas ou com reflexo tendem a falhar. Por isso a confirmação humana é obrigatória.
- Sem nenhum provedor configurado, a leitura fica desligada e a pessoa digita a data (o resto funciona igual).
- **Os planos grátis têm limite diário e podem mudar.** Google e Groq definem e alteram os limites quando quiserem. Com muitas lojas, o limite grátis acaba e a leitura passa a ser paga (ou vai para o Ollama, que precisa de uma máquina com memória para rodar). Não há controle de uso por loja.
- **Os nomes dos modelos mudam.** Os padrões do `.env.example` (`gemini-3.5-flash-lite`, o modelo de visão do Groq) precisam ser conferidos nos painéis dos provedores de tempos em tempos.
- **A integração com os provedores reais ainda não foi testada com chave de verdade.** Os testes usam um servidor falso que imita a resposta. Falta rodar com uma chave do Gemini.
- O Gemini e o Groq recebem a foto da embalagem. Ela não traz dado pessoal, mas no plano grátis o Google pode usar o conteúdo para melhorar seus produtos (ver os termos do provedor).

## Técnica
- **Fila no banco com consulta a cada 2 segundos.** Serve para o volume de mercados pequenos. Com muito volume, trocar por uma fila dedicada (Redis, SQS).
- **Limitador de tentativas na memória do processo.** Com mais de um servidor, cada um conta separado. Trocar por Redis.
- **A foto fica no disco do servidor enquanto espera na fila** (segundos, ou alguns minutos se a IA estiver fora). Com vários servidores, todos precisam enxergar a mesma pasta. Depois da leitura, ela é apagada.
- **O Docker Compose foi escrito, mas não testado nesta máquina** (o Docker não está instalado nela). O sistema foi testado com SQLite; os testes de concorrência rodam em SQLite, que serializa escritas, então o comportamento no PostgreSQL deve ser confirmado.
- **A interface é JavaScript puro, sem testes automatizados próprios.** Foi conferida em navegador (celular de 360 e 390 px e computador), mas não há testes de ponta a ponta no CI.
