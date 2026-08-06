# precos-seminovos

Coleta semanal de preco de iPhone seminovo no Mercado Livre, via API oficial,
publicada como JSON num repositorio publico para a rotina do Claude Cowork
consumir por HTTP.

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

A aplicacao `pitzi-precos` (App ID `5093338876848781`) ja existe no painel
do Mercado Pago (portais ML/MP unificados).

1. Em *Configuracoes da aplicacao -> Configuracao avancada*, salve a URL de
   redirecionamento `www.pitzi.com.br/callback`.

   > **Nunca `localhost`.** O WAF (CloudFront) do Mercado Livre devolve
   > `403 ERROR — Request blocked` para qualquer `redirect_uri` contendo
   > `localhost`, antes da requisicao chegar ao servidor de autenticacao. O
   > campo do painel tambem prefixa `https://` automaticamente — digitar a
   > URL completa gera `https://https://...`. A pagina
   > `pitzi.com.br/callback` nao precisa existir; o codigo aparece na barra
   > de endereco mesmo com 404.

2. Autorize em:

   ```
   https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=5093338876848781&redirect_uri=https%3A%2F%2Fwww.pitzi.com.br%2Fcallback
   ```

   Copie o `code=TG-...` da barra de endereco (validade: 10 minutos).

3. Pegue a **Chave secreta** em *PRODUCAO -> Credenciais de producao*.

4. Troque o code pelo `refresh_token`:

   ```bash
   curl -X POST https://api.mercadolibre.com/oauth/token \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -d grant_type=authorization_code \
     -d client_id=5093338876848781 \
     -d client_secret=SUA_CHAVE_SECRETA \
     -d code=TG-xxxxxxxxxx \
     -d redirect_uri=https://www.pitzi.com.br/callback
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
