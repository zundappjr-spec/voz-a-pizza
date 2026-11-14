"""Registro de pedidos confirmados.

Opera en modo simulacion por defecto. Requiere un indicador explicito
(--registrar / REGISTRAR_PEDIDOS=1) para realizar el registro real.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict

SIMULATION_MODE = os.environ.get("REGISTRAR_PEDIDOS", "0").lower() not in ("1", "true", "yes")


def generar_clave_pedido(commerce_id: str, pedido: Dict[str, Any]) -> str:
    """Clave independiente para el pedido confirmada (distinta del message_id)."""
    raw = f"{commerce_id}|{pedido.get('source_message_id','')}|{pedido.get('subtotal','')}|{pedido.get('currency','')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def registrar_pedido(pedido: Dict[str, Any], commerce_id: str, registrar: bool = SIMULATION_MODE) -> Dict[str, Any]:
    """Registra un pedido confirmado.

    Por defecto (registrar=False) solo simula y devuelve un borrador.
    Si registrar=True, intenta el registro real contra el backend autorizado.
    """
    clave_pedido = generar_clave_pedido(commerce_id, pedido)
    registrado_en = datetime.now(timezone.utc).isoformat()

    resultado: Dict[str, Any] = {
        "clave_pedido": clave_pedido,
        "source_message_id": pedido.get("source_message_id"),
        "estado": "borrador" if not registrar else "registrado",
        "registrado_en": registrado_en,
        "simulacion": not registrar,
        "items": pedido.get("items", []),
        "subtotal": pedido.get("subtotal"),
        "total": pedido.get("total"),
        "currency": pedido.get("currency"),
        "fulfillment": pedido.get("fulfillment"),
    }

    if not registrar:
        resultado["mensaje"] = "Modo simulacion: pedido no registrado. Use REGISTRAR_PEDIDOS=1 para registrar."
        return resultado

    # Registro real: delegar en el componente autorizado (backend).
    # Aqui se integraria la llamada al backend autorizado con timeout y reintentos limitados.
    backend_url = os.environ.get("BACKEND_PEDIDOS_URL")
    if not backend_url:
        resultado["estado"] = "error"
        resultado["mensaje"] = "BACKEND_PEDIDOS_URL no configurado"
        return resultado

    try:
        import urllib.request
        payload = json.dumps({
            "clave_pedido": clave_pedido,
            "pedido": pedido,
            "commerce_id": commerce_id,
        }).encode("utf-8")
        req = urllib.request.Request(
            backend_url,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {os.environ.get('BACKEND_PEDIDOS_KEY','')}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            resultado["backend_respuesta"] = body
            resultado["estado"] = "registrado"
    except Exception as exc:  # noqa: BLE001
        resultado["estado"] = "error"
        resultado["mensaje"] = f"Fallo al registrar en el backend: {exc}"

    return resultado


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python registrar_pedido.py <archivo_pedido.json> [--registrar]")
        return 2

    ruta = sys.argv[1]
    registrar = "--registrar" in sys.argv or os.environ.get("REGISTRAR_PEDIDOS", "0").lower() in ("1", "true", "yes")

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            pedido = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error leyendo el pedido: {exc}")
        return 1

    commerce_id = os.environ.get("COMMERCE_ID", "comercio-desconocido")
    resultado = registrar_pedido(pedido, commerce_id, registrar=registrar)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado["estado"] in ("borrador", "registrado") else 1


if __name__ == "__main__":
    sys.exit(main())
