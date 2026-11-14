"""Calculo de importes con aritmetica decimal.

Calcula subtotal y total de un pedido validado.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List

CENT = Decimal("0.01")


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def calcular_total(
    items: List[Dict[str, Any]],
    currency: str = "",
) -> Dict[str, Any]:
    """Calcula importes con aritmetica decimal determinista.

    Retorna:
      - subtotal: str (string decimal)
      - total: str
      - currency: str
      - line_totals: lista de {sku, quantity, unit_price, line_total}
      - errors: lista de mensajes
    """
    errors: List[str] = []
    line_totals: List[Dict[str, Any]] = []
    subtotal = Decimal("0")

    for index, item in enumerate(items):
        sku = item.get("sku", f"item-{index}")
        quantity = item.get("quantity")
        unit_price = _to_decimal(item.get("unit_price"))

        try:
            quantity_int = int(quantity)
        except (TypeError, ValueError):
            errors.append(f"Linea {index}: cantidad invalida para {sku}")
            continue
        if quantity_int <= 0:
            errors.append(f"Linea {index}: cantidad no valida para {sku}")
            continue

        line_total = (unit_price * quantity_int).quantize(CENT, rounding=ROUND_HALF_UP)
        subtotal += line_total

        line_totals.append({
            "sku": sku,
            "quantity": quantity_int,
            "unit_price": str(unit_price.quantize(CENT, rounding=ROUND_HALF_UP)),
            "line_total": str(line_total),
        })

    total = subtotal.quantize(CENT, rounding=ROUND_HALF_UP)

    return {
        "subtotal": str(subtotal.quantize(CENT, rounding=ROUND_HALF_UP)),
        "total": str(total),
        "currency": currency or "",
        "line_totals": line_totals,
        "errors": errors,
    }
