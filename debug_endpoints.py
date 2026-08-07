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

# reconferir keywords isolado, sem status=active, minimo de params
testar("A: só keywords+site_id", "https://api.mercadolibre.com/products/search?site_id=MLB&keywords=iphone")
testar("B: keywords+site_id+status", "https://api.mercadolibre.com/products/search?site_id=MLB&status=active&keywords=iphone+13")
testar("C: keywords+domain_id", f"https://api.mercadolibre.com/products/search?site_id=MLB&domain_id={domain_id}&keywords=iphone")
testar("D: keywords+category_id", f"https://api.mercadolibre.com/products/search?site_id=MLB&category_id={category_id}&keywords=iphone")
testar("E: q em vez de keywords", "https://api.mercadolibre.com/products/search?site_id=MLB&q=iphone")

