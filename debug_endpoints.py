#!/usr/bin/env python3
"""Debug temporario: inspecionar HTML renderizado da listagem via Playwright."""
from playwright.sync_api import sync_playwright

URL = "https://lista.mercadolivre.com.br/iphone-13-seminovo"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
    page.goto(URL, wait_until="networkidle", timeout=30000)
    html = page.content()
    print(f"tamanho html renderizado: {len(html)}")

    # tentar seletores comuns de card de anuncio no ML
    seletores = [
        "li.ui-search-layout__item",
        "div.ui-search-result__wrapper",
        "a.ui-search-item__group__element",
        "h2.ui-search-item__title",
        "h3.poly-component__title",
        "span.andes-money-amount__fraction",
        "[class*='poly-card']",
    ]
    for sel in seletores:
        count = page.locator(sel).count()
        print(f"seletor {sel!r}: {count} elementos")
        if count:
            texto = page.locator(sel).first.inner_text()
            print(f"  primeiro texto: {texto[:100]!r}")

    browser.close()
