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

_, body = testar("q=iphone 13 seminovo + domain + limit10", f"https://api.mercadolibre.com/products/search?site_id=MLB&domain_id={domain_id}&q=iphone+13+seminovo&limit=10")
dados = json.loads(body)
print(f"total={dados['paging']['total']} results={len(dados['results'])}")
print("PRIMEIRO RESULT COMPLETO:")
print(json.dumps(dados["results"][0], ensure_ascii=False))

# testar items de varios catalogos ate achar um com winner usado
for r in dados["results"][:8]:
    pid = r["id"]
    status2, body2 = testar(f"items {pid} ({r.get('name')}) condition=used", f"https://api.mercadolibre.com/products/{pid}/items?condition=used")
    if status2 == 200:
        d2 = json.loads(body2)
        usados = [x for x in d2["results"] if x.get("condition") == "used"]
        print(f"  -> {len(d2['results'])} total, {len(usados)} usados")
        if usados:
            print("  PRIMEIRO USADO COMPLETO:", json.dumps(usados[0], ensure_ascii=False)[:1500])

