# Segurança

O que foi feito, e onde está o teste que garante.

| Risco | Proteção | Teste |
|---|---|---|
| Senha vazada do banco | Argon2 (hash lento e com sal). A senha nunca aparece em resposta. | `unitarios/test_seguranca_basica.py`, `integracao/test_contas.py` |
| Descobrir quais e-mails têm conta | Login responde igual para e-mail inexistente e senha errada, e confere um hash falso para o tempo ser parecido. | `test_senha_errada_e_email_inexistente_tem_a_mesma_resposta` |
| Força bruta no login | Limite de 5 tentativas por IP + e-mail a cada 5 minutos. | `test_bloqueia_depois_de_muitas_tentativas` |
| Roubo de sessão por script (XSS) | Sessão em cookie `HttpOnly` (o JavaScript não lê), `SameSite=Strict`, `Secure` em produção. A interface só cria elementos com `textContent` (nunca `innerHTML`). CSP bloqueia scripts de fora e scripts inline. | `test_cadastro_abre_sessao_com_cookie_protegido`, `test_cabecalhos_de_seguranca` |
| CSRF (site malicioso agindo em nome do usuário) | Toda requisição que altera dados precisa do cabeçalho `X-Requested-With: validade-certa`, que um site de fora não consegue enviar sem CORS (que não liberamos). Somado ao `SameSite=Strict`. | `test_sem_cabecalho_csrf_nada_e_alterado` |
| Token falsificado | JWT assinado com HS256, `exp` obrigatório, algoritmo fixo (recusa `alg: none`). Chave de 32+ caracteres obrigatória em produção. | `test_token_valido_e_adulterado`, `test_cookie_adulterado_nao_entra`, `test_producao_exige_chave_secreta_forte` |
| Uma loja ver dados de outra | Toda consulta filtra por `loja_id` da sessão. Ids de outra loja respondem 404 (nem confirma que existem). | `integracao/test_isolamento_lojas.py` |
| Upload malicioso | Tipo descoberto pelos bytes (só JPEG, PNG, WebP; SVG recusado). Limite de 5 MB. Nome do arquivo descartado e trocado por um aleatório. Caminho validado contra `../`. Não existe rota para baixar fotos, e elas são apagadas depois da leitura. Limite de 20 fotos por minuto por usuário. | `unitarios/test_arquivos.py`, `integracao/test_leituras.py` |
| Chave da IA vazar | Chaves só no `.env` do servidor; nunca chegam ao navegador nem aparecem nos logs (o log registra só o nome do provedor e o código HTTP). | `unitarios/test_cliente_ia.py` |
| Localização nas fotos | O celular reduz a foto e regrava em JPEG antes de enviar, o que apaga os metadados (EXIF/GPS). | (no navegador: `frontend/js/util/imagem.js`) |
| SQL injection | Só consultas do SQLAlchemy com parâmetros; a busca escapa `%` e `_`. | `test_busca_de_produto_nao_quebra_com_caracteres_especiais` |
| Vazamento em erro | Erro inesperado responde mensagem genérica; o detalhe vai só para o log. | `test_erro_inesperado_nao_vaza_detalhes` |
| Clickjacking e afins | `X-Frame-Options: DENY`, `frame-ancestors 'none'`, `nosniff`, `Referrer-Policy: no-referrer`, HSTS em produção. API com `Cache-Control: no-store`. | `test_cabecalhos_de_seguranca`, `test_producao_esconde_documentacao_e_usa_cookie_seguro` |
| Documentação da API exposta | `/api/docs` só existe fora de produção. | idem |
| Segredos no GitHub | `.env` no `.gitignore`; `.env.example` sem valores. | — |
| Prompt injection pela foto | A IA não tem ferramentas nem acesso a nada: só devolve texto, que é validado contra um formato fixo. O pior caso é uma sugestão errada, que a pessoa vê antes de salvar. | `unitarios/test_resposta_ia.py` |

## O que ainda falta (ver também `limitacoes.md`)
- Recuperação de senha por e-mail.
- Mais de um usuário por loja, com permissões (dono e funcionário).
- Limitador de tentativas compartilhado entre servidores (hoje fica na memória de um processo).
- Varredura de vírus nas fotos e limpeza das fotos antigas.
- Atrás de proxy, configurar `--forwarded-allow-ips` para o limitador enxergar o IP real.
