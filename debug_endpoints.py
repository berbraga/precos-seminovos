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
    ("search por categoria (sem q=)", "https://api.mercadolibre.com/sites/MLB/search?category=MLB1055"),
    ("search por categoria+q", "https://api.mercadolibre.com/sites/MLB/search?category=MLB1055&q=iphone"),
    ("products/search", "https://api.mercadolibre.com/products/search?status=active&site_id=MLB&category_id=MLB1055"),
    ("highlights categoria", "https://api.mercadolibre.com/highlights/MLB/category/MLB1055"),
    ("categories/MLB1055 (metadata)", "https://api.mercadolibre.com/categories/MLB1055"),
    ("sites/MLB (metadata)", "https://api.mercadolibre.com/sites/MLB"),
    ("search generico condition=used", "https://api.mercadolibre.com/sites/MLB/search?category=MLB1055&condition=used"),
]

for nome, url in CANDIDATOS:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(request, timeout=15) as resposta:
            corpo = resposta.read().decode("utf-8", errors="replace")
            print(f"{nome}: HTTP {resposta.status} - {len(corpo)} bytes - {corpo[:150]}")
    except urllib.error.HTTPError as erro:
        corpo = erro.read().decode("utf-8", errors="replace")
        print(f"{nome}: HTTP {erro.code} - {corpo[:200]}")
    except Exception as erro:
        print(f"{nome}: ERRO {erro}")
