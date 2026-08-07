#!/usr/bin/env python3
"""Script temporario: testa endpoints alternativos do ML pra achar um que nao seja 403.
Nao imprime token nem secret em nenhuma hipotese. Apagar depois do diagnostico.
"""
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, ".")
from ml_coleta import obter_access_token, obter_credenciais  # noqa: E402

client_id, client_secret, refresh_token = obter_credenciais()
access_token, _ = obter_access_token(client_id, client_secret, refresh_token)

def testar(nome, url):
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(request, timeout=15) as r:
            body = r.read().decode("utf-8", errors="replace")
            print(f"{nome}: HTTP {r.status} - {body[:400]}")
            return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"{nome}: HTTP {e.code} - {body[:400]}")
        return e.code, body

import urllib.parse

_, body = testar("domain_discovery", "https://api.mercadolibre.com/sites/MLB/domain_discovery/search?q=iphone%2013&limit=5")
info = json.loads(body)[0]
domain_id = info["domain_id"]
category_id = info["category_id"]

_, body = testar("q=iphone 13 seminovo + domain + limit50", f"https://api.mercadolibre.com/products/search?site_id=MLB&domain_id={domain_id}&q=iphone+13+seminovo&limit=50")
dados = json.loads(body)
print(f"total={dados['paging']['total']} results={len(dados['results'])}")
for r in dados["results"][:5]:
    print(" ", r.get("id"), r.get("domain_id"), r.get("name"))

# testar se /products/{catalog_product_id}/items aceita condition=used
if dados["results"]:
    pid = dados["results"][0]["id"]
    testar(f"items de {pid} condition=used", f"https://api.mercadolibre.com/products/{pid}/items?condition=used")

