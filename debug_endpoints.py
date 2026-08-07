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

CANDIDATOS = [
    ("highlights categoria", "https://api.mercadolibre.com/highlights/MLB/category/MLB1055"),
]

for nome, url in CANDIDATOS:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(request, timeout=15) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    ids = [c["id"] for c in dados.get("content", []) if c.get("type") == "PRODUCT"]
    print(f"{nome}: {len(ids)} ids -> {ids[:10]}")

    for item_id in ids[:3]:
        for path in (f"/items/{item_id}", f"/products/{item_id}", f"/products/{item_id}/items"):
            url2 = f"https://api.mercadolibre.com{path}"
            req2 = urllib.request.Request(url2, headers={"Authorization": f"Bearer {access_token}"})
            try:
                with urllib.request.urlopen(req2, timeout=15) as r2:
                    body2 = r2.read().decode("utf-8", errors="replace")
                    print(f"  {path}: HTTP {r2.status} - {body2[:300]}")
            except urllib.error.HTTPError as e2:
                body2 = e2.read().decode("utf-8", errors="replace")
                print(f"  {path}: HTTP {e2.code} - {body2[:300]}")

