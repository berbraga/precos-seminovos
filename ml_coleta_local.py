#!/usr/bin/env python3
"""Coleta precos de iPhones seminovos no Mercado Livre via scraping local.

Roda SO no seu PC, com seu Chrome de verdade (nao headless, nao datacenter).
GitHub Actions e sandbox de nuvem sao bloqueados pelo Mercado Livre (deteccao
anti-bot de fingerprint) -- rodando localmente, com navegador real, a pagina
carrega normal porque parece uso comum.

Requisitos (rodar uma vez):
    pip install playwright
    python -m playwright install chromium

Uso:
    python ml_coleta_local.py                          # coleta todos os modelos
    python ml_coleta_local.py --modelos "IPHONE 13,IPHONE 14 PRO"
    python ml_coleta_local.py --headed                  # abre janela visivel (default: visivel)
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml_coleta import (  # noqa: E402
    MODELOS_PADRAO,
    normalizar,
    descartar_outliers,
)

AQUI = Path(__file__).resolve().parent
BRT = timezone(timedelta(hours=-3))

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def termo_busca(modelo):
    termo = modelo.replace("IPHONE ", "iphone-")
    termo = re.sub(r"\s*\([^)]*\)", "", termo)
    termo = termo.replace(" ", "-").lower()
    return f"{termo}-seminovo"


def extrair_anuncios(page):
    """Extrai (titulo, preco, url) de cada card da pagina renderizada."""
    anuncios = []
    cards = page.locator("li.ui-search-layout__item, div.ui-search-result__wrapper, [class*='poly-card']")
    total = cards.count()
    for i in range(total):
        card = cards.nth(i)
        try:
            titulo_el = card.locator("h2, h3, [class*='title']").first
            titulo = titulo_el.inner_text(timeout=2000)
        except Exception:
            continue
        try:
            preco_el = card.locator("span.andes-money-amount__fraction").first
            preco_texto = preco_el.inner_text(timeout=2000)
            preco = float(preco_texto.replace(".", "").replace(",", "."))
        except Exception:
            continue
        try:
            url = card.locator("a").first.get_attribute("href") or ""
        except Exception:
            url = ""

        anuncios.append({"titulo": titulo, "preco": preco, "url": url})
    return anuncios


def buscar_modelo(browser, modelo):
    page = browser.new_page(user_agent=UA, locale="pt-BR")
    url = f"https://lista.mercadolivre.com.br/{termo_busca(modelo)}"
    anuncios = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        anuncios = extrair_anuncios(page)
    except Exception as erro:
        print(f"ERRO ao coletar {modelo}: {erro}", file=sys.stderr)
    finally:
        page.close()
    return anuncios


def coletar(modelos, headed):
    bruto = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        for modelo in modelos:
            anuncios = buscar_modelo(browser, modelo)
            validos = 0
            for anuncio in anuncios:
                modelo_normalizado, storage_gb = normalizar(anuncio["titulo"])
                if modelo_normalizado is None:
                    continue
                if anuncio["preco"] < 100:
                    continue
                bruto.append(
                    {
                        "modelo": modelo_normalizado,
                        "storage_gb": storage_gb,
                        "preco": anuncio["preco"],
                        "nome_original": anuncio["titulo"],
                        "url": anuncio["url"],
                        "vendedor_tipo": "pf",
                    }
                )
                validos += 1
            print(f"{modelo:20s} {len(anuncios):3d} anuncios -> {validos:3d} validos")
            time.sleep(1.5)
        browser.close()
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
    parser.add_argument("--modelos", default=None)
    parser.add_argument("--headed", action="store_true", default=True)
    args = parser.parse_args()

    modelos = MODELOS_PADRAO
    if args.modelos:
        modelos = [m.strip().upper() for m in args.modelos.split(",") if m.strip()]

    bruto = coletar(modelos, args.headed)
    itens = agregar(bruto)

    saida = {
        "fonte": "Mercado Livre",
        "coletado_em": datetime.now(BRT).isoformat(),
        "via": "scraping local (Chrome real, nao headless)",
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
