"""Agente 3 - INTERPRETACION (agente_interpretacion).

Invoca la skill de interpretacion para extraer productos, cantidades, confianza
y datos faltantes de la transcripcion contra el catalogo del comercio.

Contratos reutilizados:
- orchestrator.interpretar_pedido(transcript, catalog, catalog_version, customer_id, message_id, comercio_id)
- orquestador-pedidos-whatsapp.config.catalogo_loader.cargar_catalogo(comercio_id)
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from _paths import _ORCH  # noqa: E402

if _ORCH not in sys.path:
    sys.path.insert(0, _ORCH)

from contexto import estado  # noqa: E402
from orchestrator import interpretar_pedido  # noqa: E402

# Cargar catalogo externo del comercio
_CATALOGO_LOADER_DIR = os.path.abspath(
    os.path.join(_ORCH, "config")
)
if _CATALOGO_LOADER_DIR not in sys.path:
    sys.path.insert(0, _CATALOGO_LOADER_DIR)

try:
    from catalogo_loader import cargar_catalogo  # type: ignore
except Exception:  # pragma: no cover
    cargar_catalogo = None  # type: ignore


def _cargar_catalogo_comercio(comercio_id: str | None, catalog_evento: list) -> list:
    """Carga el catalogo desde archivo externo si es posible, sinon usa el del evento."""
    if comercio_id and cargar_catalogo:
        try:
            datos = cargar_catalogo(comercio_id)
            return list(datos.get("productos", []))
        except Exception:
            pass
    return list(catalog_evento or [])


def run(ctx: Dict[str, Any]) -> Dict[str, Any]:
    comercio_id = str(ctx.get("commerce_id", ""))
    catalog_evento = list(ctx.get("catalog", []) or [])
    catalog = _cargar_catalogo_comercio(comercio_id, catalog_evento)

    interpretacion = interpretar_pedido(
        transcript=str(ctx.get("transcript", "")),
        catalog=catalog,
        catalog_version=str(ctx.get("catalog_version", "")),
        customer_id=str(ctx.get("customer_id", "")),
        message_id=str(ctx.get("message_id", "")),
        comercio_id=comercio_id or None,
    )

    ctx["pedido"] = interpretacion
    ctx["items"] = list(interpretacion.get("items", []) or [])
    ctx["catalog"] = catalog
    ctx["fulfillment"] = dict(interpretacion.get("fulfillment", {}) or {})
    ctx["currency"] = str(interpretacion.get("currency", "") or "")
    ctx["productos_no_identificados"] = list(
        interpretacion.get("productos_no_identificados", []) or []
    )
    ctx["productos_no_disponibles"] = list(
        interpretacion.get("productos_no_disponibles", []) or []
    )
    missing = list(interpretacion.get("missing_information", []) or [])
    ctx["estado"] = (
        "requires_clarification" if missing else "interpreted"
    )
    return ctx


def main() -> int:
    import json

    if len(sys.argv) < 2:
        print("Uso: python agente_interpretacion.py <contexto.json>")
        return 2
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        ctx = json.load(f)
    resultado = run(ctx)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
