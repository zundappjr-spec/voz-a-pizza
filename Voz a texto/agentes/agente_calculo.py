"""Agente 5 - CALCULO (agente_calculo).

Calcula subtotal y total con aritmetica decimal determinista.

Contratos reutilizados:
- calcular_total.calcular_total(items, currency)
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from _paths import _SCRIPTS  # noqa: E402

if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from calcular_total import calcular_total  # noqa: E402
from contexto import hay_errores  # noqa: E402


def run(ctx: Dict[str, Any]) -> Dict[str, Any]:
    total = calcular_total(
        list(ctx.get("items", []) or []),
        currency=str(ctx.get("currency", "") or ""),
    )

    if total.get("errors"):
        ctx["errores"].extend(total["errors"])
        ctx["estado"] = "requires_clarification"
        return ctx

    ctx["subtotal"] = str(total.get("subtotal", ""))
    ctx["total"] = str(total.get("total", ""))
    ctx["currency"] = str(total.get("currency", ctx.get("currency", "") or ""))
    ctx["line_totals"] = list(total.get("line_totals", []) or [])

    pedido = ctx.get("pedido", {})
    pedido["subtotal"] = ctx["subtotal"]
    pedido["total"] = ctx["total"]
    pedido["currency"] = ctx["currency"]
    ctx["pedido"] = pedido

    if not hay_errores(ctx):
        if ctx.get("estado") not in ("requires_clarification", "rejected"):
            ctx["estado"] = "requires_confirmation"
    return ctx


def main() -> int:
    import json

    if len(sys.argv) < 2:
        print("Uso: python agente_calculo.py <contexto.json>")
        return 2
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        ctx = json.load(f)
    resultado = run(ctx)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if not hay_errores(resultado) else 1


if __name__ == "__main__":
    sys.exit(main())
