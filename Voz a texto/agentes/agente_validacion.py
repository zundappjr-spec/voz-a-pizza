"""Agente 4 - VALIDACION (agente_validacion).

Valida cantidades, SKU, variantes y campos obligatorios del pedido interpretado
contra el catalogo del comercio.

Contratos reutilizados:
- validar_pedido.validate_pedido(items, catalog, fulfillment)
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from _paths import _SCRIPTS  # noqa: E402

if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from validar_pedido import validate_pedido  # noqa: E402
from contexto import hay_errores  # noqa: E402


def run(ctx: Dict[str, Any]) -> Dict[str, Any]:
    validacion = validate_pedido(
        list(ctx.get("items", []) or []),
        list(ctx.get("catalog", []) or []),
        dict(ctx.get("fulfillment", {}) or {}),
    )

    if not validacion["valid"]:
        ctx["estado"] = "requires_clarification"
        ctx["errores"].extend(validacion["errors"])

    ctx["advertencias"].extend(validacion.get("warnings", []))
    ctx["items"] = validacion["items"]
    ctx["fulfillment_type"] = validacion.get("fulfillment_type")
    return ctx


def main() -> int:
    import json

    if len(sys.argv) < 2:
        print("Uso: python agente_validacion.py <contexto.json>")
        return 2
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        ctx = json.load(f)
    resultado = run(ctx)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if not hay_errores(resultado) else 1


if __name__ == "__main__":
    sys.exit(main())
