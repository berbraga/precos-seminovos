#!/usr/bin/env python3
"""Coleta precos de iPhones seminovos no Mercado Livre via API oficial.

Uso:
    python ml_coleta.py                    # coleta todos os modelos -> ml_precos.json
    python ml_coleta.py --autotest         # valida normalizacao, sem rede e sem credencial
    python ml_coleta.py --modelos "IPHONE 13,IPHONE 14 PRO"

Credenciais (env vars, com fallback para .env ao lado do script):
    ML_CLIENT_ID, ML_CLIENT_SECRET, ML_REFRESH_TOKEN
Ver README.md para como obter.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BRT = timezone(timedelta(hours=-3))

TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
PRODUCTS_SEARCH_URL = "https://api.mercadolibre.com/products/search"
PRODUCT_ITEMS_URL = "https://api.mercadolibre.com/products/{}/items"
DOMAIN = "MLB-CELLPHONES"

TOKEN_CACHE = AQUI / ".ml_token.json"
NEW_REFRESH_FILE = AQUI / ".new_refresh_token"
ENV_FILE = AQUI / ".env"

MODELOS_PADRAO = [
    "IPHONE 6", "IPHONE 6S", "IPHONE 6S PLUS", "IPHONE 7", "IPHONE 7 PLUS",
    "IPHONE 8", "IPHONE 8 PLUS", "IPHONE X", "IPHONE XR", "IPHONE XS",
    "IPHONE XS MAX", "IPHONE SE (2020)", "IPHONE SE (2022)",
    "IPHONE 11", "IPHONE 11 PRO", "IPHONE 11 PRO MAX",
    "IPHONE 12 MINI", "IPHONE 12", "IPHONE 12 PRO", "IPHONE 12 PRO MAX",
    "IPHONE 13 MINI", "IPHONE 13", "IPHONE 13 PRO", "IPHONE 13 PRO MAX",
    "IPHONE 14", "IPHONE 14 PLUS", "IPHONE 14 PRO", "IPHONE 14 PRO MAX",
    "IPHONE 15", "IPHONE 15 PLUS", "IPHONE 15 PRO", "IPHONE 15 PRO MAX",
    "IPHONE 16", "IPHONE 16 PLUS", "IPHONE 16 PRO", "IPHONE 16 PRO MAX",
    "IPHONE 16E",
]

# Ordenado do mais especifico ao mais generico. Primeiro casamento vence.
PADROES_MODELO = [
    ("IPHONE 16 PRO MAX", r"16\s*pro\s*max"),
    ("IPHONE 16 PRO", r"16\s*pro"),
    ("IPHONE 16 PLUS", r"16\s*plus"),
    ("IPHONE 16E", r"16\s*e\b"),
    ("IPHONE 16", r"\b16\b"),
    ("IPHONE 15 PRO MAX", r"15\s*pro\s*max"),
    ("IPHONE 15 PRO", r"15\s*pro"),
    ("IPHONE 15 PLUS", r"15\s*plus"),
    ("IPHONE 15", r"\b15\b"),
    ("IPHONE 14 PRO MAX", r"14\s*pro\s*max"),
    ("IPHONE 14 PRO", r"14\s*pro"),
    ("IPHONE 14 PLUS", r"14\s*plus"),
    ("IPHONE 14", r"\b14\b"),
    ("IPHONE 13 PRO MAX", r"13\s*pro\s*max"),
    ("IPHONE 13 PRO", r"13\s*pro"),
    ("IPHONE 13 MINI", r"13\s*mini"),
    ("IPHONE 13", r"\b13\b"),
    ("IPHONE 12 PRO MAX", r"12\s*pro\s*max"),
    ("IPHONE 12 PRO", r"12\s*pro"),
    ("IPHONE 12 MINI", r"12\s*mini"),
    ("IPHONE 12", r"\b12\b"),
    ("IPHONE 11 PRO MAX", r"11\s*pro\s*max"),
    ("IPHONE 11 PRO", r"11\s*pro"),
    ("IPHONE 11", r"\b11\b"),
    ("IPHONE XS MAX", r"\bxs\s*max"),
    ("IPHONE XS", r"\bxs\b"),
    ("IPHONE XR", r"\bxr\b"),
    ("IPHONE SE (2022)", r"se\s*\(?(2022|3)"),
    ("IPHONE SE (2020)", r"se\s*\(?(2020|2)"),
    ("IPHONE X", r"\bx\b"),
    ("IPHONE 8 PLUS", r"\b8\s*plus"),
    ("IPHONE 8", r"\b8\b"),
    ("IPHONE 7 PLUS", r"\b7\s*plus"),
    ("IPHONE 7", r"\b7\b"),
    ("IPHONE 6S PLUS", r"6s\s*plus"),
    ("IPHONE 6S", r"\b6s\b"),
    ("IPHONE 6", r"\b6\b"),
]
PADROES_MODELO_COMPILADOS = [(m, re.compile(p)) for m, p in PADROES_MODELO]

STORAGE_VALIDOS = {16, 32, 64, 128, 256, 512, 1024, 2048}
RE_STORAGE = re.compile(r"(\d+)\s*(tb|gb|g\b)")

RE_DESCARTE = re.compile(
    r"capa|case|capinha|pelicula|pel[íi]cula|carregador|cabo|fone|adaptador|"
    r"suporte|bateria\s+para|tela\s+para|display\s+para|placa|conector|"
    r"caixa\s+vazia|somente\s+a\s+caixa|manual|sucata|pe[çc]as?|"
    r"retirada\s+de\s+pe|n[aã]o\s+liga|bloqueado|icloud|conta\s+bloqueada|"
    r"apenas\s+a\s+carca[çc]a",
    re.IGNORECASE,
)

CASOS_TESTE = [
    ("iPhone 13 128GB Meia Noite Seminovo Vitrine", "IPHONE 13", 128),
    ("Apple iPhone 14 Pro Max 256gb Roxo Excelente", "IPHONE 14 PRO MAX", 256),
    ("iPhone 12 Mini 64 GB Azul", "IPHONE 12 MINI", 64),
    ("iPhone 15 Pro 1tb Titanio Natural", "IPHONE 15 PRO", 1024),
    ("iPhone Xs Max 64gb Dourado", "IPHONE XS MAX", 64),
    ("iPhone SE 2022 64gb (3a geracao)", "IPHONE SE (2022)", 64),
    ("iPhone 16e 128gb Preto", "IPHONE 16E", 128),
    ("Capa Case Para iPhone 13 Pro Transparente", None, None),
    ("iPhone 11 64gb Placa Retirada De Pecas", None, None),
    ("Tela Display Para iPhone 12 Pro Max Original", None, None),
    ("iPhone X 64gb Bloqueado Icloud", None, None),
    ("Carregador iPhone 20w + Cabo", None, None),
]


def normalizar(titulo):
    """Recebe o title do anuncio e devolve (modelo, storage_gb) ou (None, None)."""
    if not titulo:
        return None, None
    t = titulo.lower()

    if RE_DESCARTE.search(t):
        return None, None
    if "iphone" not in t:
        return None, None

    modelo = None
    for nome, padrao in PADROES_MODELO_COMPILADOS:
        if padrao.search(t):
            modelo = nome
            break
    if modelo is None:
        return None, None

    storage = None
    m = RE_STORAGE.search(t)
    if m:
        valor = int(m.group(1))
        unidade = m.group(2)
        if unidade == "tb":
            valor *= 1024
        if valor in STORAGE_VALIDOS:
            storage = valor

    if storage is None:
        return None, None

    return modelo, storage


def descartar_outliers(precos):
    """Remove amostras fora de 40%-250% da mediana quando ha 4+ amostras."""
    if len(precos) < 4:
        return list(precos)
    mediana = statistics.median(precos)
    baixo = mediana * 0.4
    alto = mediana * 2.5
    filtrados = [p for p in precos if baixo <= p <= alto]
    if not filtrados:
        return list(precos)
    return filtrados


def rodar_autotest():
    ok = 0
    total = len(CASOS_TESTE)
    for titulo, modelo_esperado, storage_esperado in CASOS_TESTE:
        modelo, storage = normalizar(titulo)
        if modelo == modelo_esperado and storage == storage_esperado:
            ok += 1
        else:
            print(
                f"FALHOU: {titulo!r} -> esperado ({modelo_esperado}, {storage_esperado}), "
                f"obtido ({modelo}, {storage})",
                file=sys.stderr,
            )

    amostra = [1000, 1100, 1050, 1080, 120, 9000]
    esperado_outliers = [1000, 1100, 1050, 1080]
    resultado_outliers = descartar_outliers(amostra)
    outliers_ok = resultado_outliers == esperado_outliers
    if not outliers_ok:
        print(
            f"FALHOU (outliers): esperado {esperado_outliers}, obtido {resultado_outliers}",
            file=sys.stderr,
        )

    print(f"{ok}/{total} casos ok")
    print(f"outliers: {'ok' if outliers_ok else 'FALHOU'}")

    if ok != total or not outliers_ok:
        sys.exit(1)


def carregar_env_file(caminho):
    valores = {}
    if not caminho.exists():
        return valores
    for linha in caminho.read_text().splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valores[chave.strip()] = valor.strip()
    return valores


def obter_credenciais():
    env_arquivo = carregar_env_file(ENV_FILE)
    chaves = ["ML_CLIENT_ID", "ML_CLIENT_SECRET", "ML_REFRESH_TOKEN"]
    valores = {}
    faltando = []
    for chave in chaves:
        valor = os.environ.get(chave) or env_arquivo.get(chave)
        if not valor:
            faltando.append(chave)
        valores[chave] = valor

    if faltando:
        print(
            "ERRO: defina " + ", ".join(faltando) + " (env var ou .env). "
            "Veja README.md para como obter as credenciais.",
            file=sys.stderr,
        )
        sys.exit(1)

    return valores["ML_CLIENT_ID"], valores["ML_CLIENT_SECRET"], valores["ML_REFRESH_TOKEN"]


def requisitar_com_retry(request, tentativas=4):
    for tentativa in range(tentativas):
        try:
            with urllib.request.urlopen(request, timeout=30) as resposta:
                return json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            if erro.code in (429, 500, 502, 503) and tentativa < tentativas - 1:
                time.sleep(2**tentativa)
                continue
            raise


def renovar_access_token(client_id, client_secret, refresh_token):
    dados = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        TOKEN_URL,
        data=dados,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    return requisitar_com_retry(request, tentativas=1)


def obter_access_token(client_id, client_secret, refresh_token):
    agora = time.time()

    if TOKEN_CACHE.exists():
        try:
            cache = json.loads(TOKEN_CACHE.read_text())
            if cache.get("refresh_token") == refresh_token and cache.get("expira_em", 0) - agora > 300:
                return cache["access_token"], refresh_token
        except (json.JSONDecodeError, KeyError):
            pass

    resposta = renovar_access_token(client_id, client_secret, refresh_token)
    access_token = resposta["access_token"]
    novo_refresh_token = resposta.get("refresh_token", refresh_token)
    expira_em = agora + resposta.get("expires_in", 21600)

    TOKEN_CACHE.write_text(
        json.dumps(
            {
                "access_token": access_token,
                "refresh_token": novo_refresh_token,
                "expira_em": expira_em,
            }
        )
    )
    os.chmod(TOKEN_CACHE, 0o600)

    if novo_refresh_token != refresh_token:
        NEW_REFRESH_FILE.write_text(novo_refresh_token)
        os.chmod(NEW_REFRESH_FILE, 0o600)
        print("refresh_token rotacionado (novo valor gravado, nao exibido)", file=sys.stderr)

    return access_token, novo_refresh_token


def termo_busca(modelo):
    termo = modelo.replace("IPHONE ", "iPhone ")
    termo = re.sub(r"\s*\([^)]*\)", "", termo)
    return f"{termo} seminovo"


def buscar_modelo(access_token, modelo):
    anuncios = []
    offset = 0
    limite_total = 200
    limite_offset_maximo = 1000

    while len(anuncios) < limite_total and offset <= limite_offset_maximo:
        params = urllib.parse.urlencode(
            {
                "q": termo_busca(modelo),
                "category": CATEGORY,
                "condition": "used",
                "limit": 50,
                "offset": offset,
            }
        )
        request = urllib.request.Request(
            f"{SEARCH_URL}?{params}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        pagina = requisitar_com_retry(request)
        resultados = pagina.get("results", [])
        if not resultados:
            break
        anuncios.extend(resultados)

        paging = pagina.get("paging", {})
        total_disponivel = paging.get("total", 0)
        offset += 50
        if offset >= total_disponivel:
            break

        time.sleep(0.4)

    return anuncios[:limite_total]


def coletar(modelos, client_id, client_secret, refresh_token):
    access_token, _ = obter_access_token(client_id, client_secret, refresh_token)

    bruto = []
    erro_detalhado_impresso = False
    for modelo in modelos:
        try:
            anuncios = buscar_modelo(access_token, modelo)
        except urllib.error.HTTPError as erro:
            if not erro_detalhado_impresso:
                corpo = erro.read().decode("utf-8", errors="replace")
                print(f"ERRO detalhado (HTTP {erro.code}): {corpo}", file=sys.stderr)
                erro_detalhado_impresso = True
            print(f"ERRO ao coletar {modelo}: HTTP {erro.code}", file=sys.stderr)
            continue
        except Exception as erro:
            print(f"ERRO ao coletar {modelo}: {erro}", file=sys.stderr)
            continue

        validos = 0
        for anuncio in anuncios:
            titulo = anuncio.get("title", "")
            modelo_normalizado, storage_gb = normalizar(titulo)
            if modelo_normalizado is None:
                continue
            preco = anuncio.get("price")
            if preco is None or preco < 100:
                continue

            seller = anuncio.get("seller", {}) or {}
            vendedor_tipo = "loja" if seller.get("car_dealer") else "pf"

            bruto.append(
                {
                    "modelo": modelo_normalizado,
                    "storage_gb": storage_gb,
                    "preco": float(preco),
                    "nome_original": titulo,
                    "url": anuncio.get("permalink", ""),
                    "vendedor_tipo": vendedor_tipo,
                }
            )
            validos += 1

        print(f"{modelo:20s} {len(anuncios):3d} anuncios -> {validos:3d} validos")
        time.sleep(0.5)

    return bruto


def agregar(bruto):
    grupos = {}
    for item in bruto:
        chave = (item["modelo"], item["storage_gb"])
        grupos.setdefault(chave, []).append(item["preco"])

    itens = []
    for (modelo, storage_gb), precos in sorted(grupos.items()):
        n_original = len(precos)
        filtrados = descartar_outliers(precos)
        itens.append(
            {
                "modelo": modelo,
                "storage_gb": storage_gb,
                "grade": "Usado (marketplace)",
                "tier": 2,
                "mediana": round(statistics.median(filtrados), 2),
                "min": round(min(filtrados), 2),
                "max": round(max(filtrados), 2),
                "n": len(filtrados),
                "n_descartados": n_original - len(filtrados),
            }
        )
    return itens


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--autotest", action="store_true")
    parser.add_argument("--modelos", default=None)
    args = parser.parse_args()

    if args.autotest:
        rodar_autotest()
        return

    modelos = MODELOS_PADRAO
    if args.modelos:
        modelos = [m.strip().upper() for m in args.modelos.split(",") if m.strip()]

    client_id, client_secret, refresh_token = obter_credenciais()

    bruto = coletar(modelos, client_id, client_secret, refresh_token)
    itens = agregar(bruto)

    saida = {
        "fonte": "Mercado Livre",
        "coletado_em": datetime.now(BRT).isoformat(),
        "via": "API oficial /sites/MLB/search (condition=used)",
        "itens": itens,
        "bruto": bruto,
    }

    caminho_saida = AQUI / "ml_precos.json"
    caminho_saida.write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"gravado {caminho_saida} ({len(itens)} combos, {len(bruto)} anuncios brutos)")


if __name__ == "__main__":
    main()
