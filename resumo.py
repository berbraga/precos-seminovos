#!/usr/bin/env python3
"""Imprime o resumo da coleta em markdown, para GITHUB_STEP_SUMMARY."""
import json
from pathlib import Path

with open(Path(__file__).resolve().parent / "ml_precos.json", encoding="utf-8") as f:
    dados = json.load(f)

itens = dados.get("itens", [])
bruto = dados.get("bruto", [])

print("## Coleta Mercado Livre")
print("")
print(f"- coletado em: {dados.get('coletado_em')}")
print(f"- combos modelo+storage: {len(itens)}")
print(f"- anuncios brutos: {len(bruto)}")
print("")
print("| modelo | storage_gb | mediana | n |")
print("|---|---|---|---|")
for item in itens[:40]:
    print(f"| {item['modelo']} | {item['storage_gb']} | {item['mediana']} | {item['n']} |")
