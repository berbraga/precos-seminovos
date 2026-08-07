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
    ("products/search keywords=iphone", "https://api.mercadolibre.com/products/search?status=active&site_id=MLB&category_id=MLB1055&keywords=iphone"),
    ("products/search keywords=iphone 13", "https://api.mercadolibre.com/products/search?status=active&site_id=MLB&category_id=MLB1055&keywords=iphone%2013"),
]

for nome, url in CANDIDATOS:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(request, timeout=15) as resposta:
            corpo = resposta.read().decode("utf-8", errors="replace")
            print(f"{nome}: HTTP {resposta.status} - {len(corpo)} bytes - {corpo[:1200]}")
    except urllib.error.HTTPError as erro:
        corpo = erro.read().decode("utf-8", errors="replace")
        print(f"{nome}: HTTP {erro.code} - {corpo[:200]}")
    except Exception as erro:
        print(f"{nome}: ERRO {erro}")
