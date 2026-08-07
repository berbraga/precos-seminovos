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
line_value_id = next(a["value_id"] for a in info["attributes"] if a["id"] == "LINE")
brand_value_id = next(a["value_id"] for a in info["attributes"] if a["id"] == "BRAND")
domain_id = info["domain_id"]

attrs_variantes = [
    f"LINE:{line_value_id}",
    f"[{{\"id\":\"LINE\",\"value_id\":\"{line_value_id}\"}}]",
]
for attrs in attrs_variantes:
    q = urllib.parse.quote(attrs, safe="")
    testar(f"products/search attributes={attrs[:30]}", f"https://api.mercadolibre.com/products/search?status=active&site_id=MLB&domain_id={domain_id}&attributes={q}")

# product_identifier as vezes eh o proprio value_id do LINE combinado com BRAND
testar("products/search product_identifier=LINE value", f"https://api.mercadolibre.com/products/search?status=active&site_id=MLB&domain_id={domain_id}&product_identifier={line_value_id}")

