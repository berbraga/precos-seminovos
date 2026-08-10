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

todos_ids = []
offset = 0
while offset < 300:
    url = f"https://api.mercadolibre.com/products/search?site_id=MLB&domain_id={domain_id}&q=iphone+13+seminovo&limit=50&offset={offset}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode("utf-8"))
    if not d["results"]:
        break
    todos_ids.extend(d["results"])
    offset += 50
    if offset >= d["paging"]["total"]:
        break

print(f"total catalog_product_ids coletados: {len(todos_ids)}")

total_usados_achados = 0
total_novos_achados = 0
sem_winner = 0
exemplos_usados = []
for r in todos_ids:
    pid = r["id"]
    url2 = f"https://api.mercadolibre.com/products/{pid}/items"
    req2 = urllib.request.Request(url2, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(req2, timeout=15) as r2:
            d2 = json.loads(r2.read().decode("utf-8"))
        usados = [x for x in d2.get("results", []) if x.get("condition") == "used"]
        novos = [x for x in d2.get("results", []) if x.get("condition") == "new"]
        total_usados_achados += len(usados)
        total_novos_achados += len(novos)
        if usados and len(exemplos_usados) < 2:
            exemplos_usados.append(usados[0])
    except urllib.error.HTTPError:
        sem_winner += 1

print(f"catalogos sem winner (404): {sem_winner}")
print(f"total itens usados encontrados: {total_usados_achados}")
print(f"total itens novos encontrados: {total_novos_achados}")
for ex in exemplos_usados:
    print("EXEMPLO USADO:", json.dumps(ex, ensure_ascii=False)[:1000])

print("\n== teste scraping HTML direto do runner ==")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
for url_html in [
    "https://lista.mercadolivre.com.br/iphone-13-seminovo",
    "https://www.mercadolivre.com.br/robots.txt",
]:
    req = urllib.request.Request(url_html, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8", errors="replace")
            print(f"{url_html}: HTTP {r.status} - {len(body)} bytes")
    except urllib.error.HTTPError as e:
        print(f"{url_html}: HTTP {e.code}")
    except Exception as e:
        print(f"{url_html}: ERRO {e}")

