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

# 1) tentar achar product_id de iphone via /products/search com product_identifier generico
testar("products/search domain iphone", "https://api.mercadolibre.com/products/search?status=active&site_id=MLB&domain_id=MLB-CELLPHONES&keywords=iphone")

# 2) autocomplete de categoria - ver se existe endpoint de sugestao
testar("domain_discovery", "https://api.mercadolibre.com/sites/MLB/domain_discovery/search?q=iphone%2013&limit=5")

# 3) catalog_product_id conhecido de iphone (exemplo generico do dominio MLB-CELLPHONES) - achar via products/search com attributes
testar("products/search attributes brand=Apple", "https://api.mercadolibre.com/products/search?status=active&site_id=MLB&category_id=MLB1055&attributes=BRAND:Apple")

