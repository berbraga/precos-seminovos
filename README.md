# precos-seminovos

Coleta semanal de preco de iPhone seminovo no Mercado Livre — **projeto
abandonado, workflow desativado**. Ver "Por que o Mercado Livre foi
abandonado" abaixo antes de retomar.

Estado original do plano: coletar via API oficial e publicar como JSON num
repositorio publico para a rotina do Claude Cowork consumir por HTTP.

## Por que o Mercado Livre foi abandonado

Tres caminhos tecnicos foram tentados e esgotados, nesta ordem:

1. **`/sites/MLB/search` (API oficial, OAuth)** — funciona tecnicamente
   (token, escopo, credenciais corretas), mas retorna `403 forbidden` em
   toda chamada. O Mercado Livre restringiu esse endpoint de busca por termo
   para aplicacoes novas desde 2023; so segue liberado para apps
   homologados antes da mudanca (allowlist fechada, sem cadastro novo
   possivel). Nao ha toggle de permissao no painel do desenvolvedor que
   resolva isso — e bloqueio de politica de produto, nao de configuracao.

2. **`/products/search` + `/products/{id}/items` (API de catalogo)** —
   alternativa que responde 200 (nao bloqueada). Usada para localizar
   ~300 `catalog_product_id` de iPhone 13 e consultar os itens vinculados.
   Resultado real medido: **0 itens em condicao usada, 583 em condicao
   nova**, em 300 catalogos testados. Usados no Mercado Livre nao
   competem no sistema de catalogo/buybox — ficam fora dessa API.

3. **Scraping da pagina de listagem HTML via GitHub Actions (Playwright)**
   — hipotese de que o IP do runner do GitHub (diferente do sandbox do
   Cowork) nao seria bloqueado. `robots.txt` permite o path testado.
   Resultado: o Mercado Livre serve uma pagina de verificacao anti-bot
   (`gz-account-verification`, `suspicious-traffic-frontend`) tanto para
   requisicao HTTP simples quanto para Chromium headless via Playwright —
   deteccao ativa de bot, nao ausencia de renderizacao JS. Contornar
   deteccao anti-bot ativamente (fingerprint spoofing, stealth plugins)
   nao foi feito por ser evasao de protecao, fora do escopo aceitavel.

Com as 3 rotas esgotadas, a planilha final roda sem a fonte Mercado Livre.
O codigo abaixo fica documentado caso o Mercado Livre mude a politica do
endpoint de busca no futuro (rota 1 seria a correta se reaberta).

## Por que isso roda no GitHub Actions e nao no Cowork

A rotina do Cowork ja coleta Trocafy, CellularStore e Trocafone via `WebFetch`.
O Mercado Livre nao pode ser coletado do mesmo jeito — ja testamos os tres
caminhos possiveis e todos falharam:

| Caminho testado | Resultado |
|---|---|
| `lista.mercadolivre.com.br/...` via `WebFetch` | bloqueado por `robots.txt` |
| Pagina de produto `/up/MLBU...` via `WebFetch` | bloqueado por `robots.txt` |
| `api.mercadolibre.com` via HTTP direto no sandbox do Cowork | `403` no proxy de egresso |

A API oficial do Mercado Livre funciona, mas exige requisicao HTTP com token
no cabeçalho `Authorization`, e o sandbox do Cowork nao consegue fazer isso.
Por isso o coletor roda em GitHub Actions, num cron semanal, e commita
`ml_precos.json` no repositorio. A rotina do Cowork le esse JSON via
`raw.githubusercontent.com` e junta com as outras tres fontes.

```
GitHub Actions — domingo 22:30 BRT (cron '30 1 * * 1' UTC)
  ml_coleta.py  ---->  API oficial do Mercado Livre
       |
       +---->  commit de ml_precos.json  ---->  URL raw publica
                                                       |
Cowork — rotina, domingo 23:02 BRT                     |
  WebFetch Trocafy . CellularStore . Trocafone         |
  WebFetch  <-------------------------------------------+
  -> consolida 4 fontes -> planilha Excel
```

## Rotacao do refresh_token

O Mercado Livre invalida o `refresh_token` a cada uso e devolve outro. No
GitHub Actions o disco e efemero — se o novo valor nao for persistido de
volta no secret `ML_REFRESH_TOKEN`, a execucao da semana seguinte morre com
`invalid_grant`, e a coleta para de funcionar silenciosamente.

Por isso o workflow, depois de cada coleta, verifica se `ml_coleta.py`
gravou um `.new_refresh_token` local. Se sim, ele:

1. mascara o valor no log (`::add-mask::`) antes de qualquer outro uso
2. chama `gh secret set ML_REFRESH_TOKEN` usando o secret `GH_PAT`
3. se `GH_PAT` nao estiver configurado, falha a execucao com `::error::`
   explicito — falhar alto agora e melhor que a coleta parar silenciosamente
   dentro de uma semana

**`GH_PAT` nao e opcional.** O token padrao do Actions (`GITHUB_TOKEN`) nao
pode alterar secrets do proprio repositorio; por isso e necessario um
Personal Access Token fine-grained dedicado, com permissao
`Secrets: Read and write` restrita a este repositorio.

## Manutencao

| Item | Frequencia |
|---|---|
| Rotacao do `ML_REFRESH_TOKEN` | automatica, a cada execucao do workflow |
| Expiracao do `refresh_token` (ML) | ~6 meses sem uso |
| Expiracao do `GH_PAT` | 1 ano — precisa ser renovado manualmente |

## Como ler o dado

O Mercado Livre e preco de **pessoa fisica** em marketplace, sem garantia
estruturada. As outras tres fontes (Trocafy, CellularStore, Trocafone) sao
varejo com garantia e grade de conservacao explicita. O ML aparece
sistematicamente mais baixo que as lojas — isso e informacao, nao erro: e o
preco com que o cliente da Pitzi compara na hora de vender. Por isso o dado
do ML fica em coluna propria na planilha e **nunca entra na media com as
lojas**.

Mapeamento de grade das outras fontes, para referencia:

- tier 1 = "Sou como novo" / "Excelente"
- tier 2 = "Tenho minhas marcas de uso" / "Muito Bom"
- tier 3 = "Fui mais usado" / "Bom"

O Mercado Livre nao expoe estado de conservacao estruturado no anuncio, por
isso todo item do ML sai com `grade: "Usado (marketplace)"` e `tier: 2` fixo.

## Uso local

```bash
python ml_coleta.py --autotest                              # sem rede, sem credencial
python ml_coleta.py --modelos "IPHONE 13,IPHONE 14 PRO"      # subconjunto
python ml_coleta.py                                          # coleta completa -> ml_precos.json
```

Credenciais via variaveis de ambiente ou `.env` ao lado do script (veja
`.env.example`):

```
ML_CLIENT_ID=
ML_CLIENT_SECRET=
ML_REFRESH_TOKEN=
```

## Como obter a credencial do Mercado Livre

**Atencao**: aplicacoes criadas no painel do Mercado Pago
(mercadopago.com.br/developers) NAO tem acesso a API de marketplace do
Mercado Livre, mesmo com escopo correto — sao portais separados. A
aplicacao correta precisa ser criada em developers.mercadolivre.com.br,
unidade de negocio "Mercado Livre", com PKCE habilitado (exige
`code_verifier`/`code_challenge` no fluxo abaixo).

Isso so importa se o endpoint `/sites/MLB/search` for reaberto pelo ML no
futuro — hoje ele retorna 403 mesmo com credenciais corretas (ver "Por que
o Mercado Livre foi abandonado" acima).

1. Em *Configuracoes da aplicacao -> Configuracao avancada*, salve a URL de
   redirecionamento `www.pitzi.com.br/callback`.

   > **Nunca `localhost`.** O WAF (CloudFront) do Mercado Livre devolve
   > `403 ERROR — Request blocked` para qualquer `redirect_uri` contendo
   > `localhost`, antes da requisicao chegar ao servidor de autenticacao. O
   > campo do painel tambem prefixa `https://` automaticamente — digitar a
   > URL completa gera `https://https://...`. A pagina
   > `pitzi.com.br/callback` nao precisa existir; o codigo aparece na barra
   > de endereco mesmo com 404.

2. Gere `code_verifier` (random) e `code_challenge` (SHA256 + base64url do
   verifier), e autorize em:

   ```
   https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=SEU_CLIENT_ID&redirect_uri=https%3A%2F%2Fwww.pitzi.com.br%2Fcallback&code_challenge=SEU_CODE_CHALLENGE&code_challenge_method=S256
   ```

   Copie o `code=TG-...` da barra de endereco (validade: 10 minutos, uso
   unico).

3. Pegue a **Chave secreta** na pagina de configuracao da aplicacao.

4. Troque o code pelo `refresh_token` (note o `code_verifier` extra em
   relacao ao fluxo OAuth padrao, exigido pelo PKCE):

   ```bash
   curl -X POST https://api.mercadolibre.com/oauth/token \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -d grant_type=authorization_code \
     -d client_id=SEU_CLIENT_ID \
     -d client_secret=SUA_CHAVE_SECRETA \
     -d code=TG-xxxxxxxxxx \
     -d redirect_uri=https://www.pitzi.com.br/callback \
     -d code_verifier=SEU_CODE_VERIFIER
   ```

5. Crie um **Personal Access Token fine-grained** do GitHub: acesso restrito
   a este repositorio, permissao *Repository permissions -> Secrets: Read
   and write*, validade de 1 ano. Esse e o `GH_PAT`.

Se as permissoes `read` e `offline access` nao estiverem marcadas na
aplicacao, o `refresh_token` nao e emitido — confira isso no painel antes de
repetir os passos acima.

## Schema de `ml_precos.json`

Contrato com a rotina do Cowork — nomes de campo nao devem mudar.

```json
{
  "fonte": "Mercado Livre",
  "coletado_em": "2026-08-09T22:30:00-03:00",
  "via": "API oficial /sites/MLB/search (condition=used)",
  "itens": [
    {
      "modelo": "IPHONE 13",
      "storage_gb": 128,
      "grade": "Usado (marketplace)",
      "tier": 2,
      "mediana": 1690.00,
      "min": 1200.00,
      "max": 2300.00,
      "n": 41,
      "n_descartados": 5
    }
  ],
  "bruto": [
    {
      "modelo": "IPHONE 13",
      "storage_gb": 128,
      "preco": 1690.00,
      "nome_original": "iPhone 13 128gb Seminovo",
      "url": "https://...",
      "vendedor_tipo": "pf"
    }
  ]
}
```
