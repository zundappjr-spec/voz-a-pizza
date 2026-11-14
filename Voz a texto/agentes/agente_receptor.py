"""Agente 1 - RECEPTOR (agente_receptor).

Recibe el evento de WhatsApp, valida su esquema, identifica al cliente,
obtiene el message_id, detecta mensajes duplicados (idempotencia inicial)
e identifica si trae audio.

Contratos reutilizados:
- validar_evento.validate_event(evento, commerce_id)
- validar_evento.compute_idempotency_key(commerce_id, evento)
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from _paths import _SCRIPTS  # noqa: E402  (agrega scripts al path)

if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from validar_evento import validate_event, compute_idempotency_key  # noqa: E402

from contexto import nuevo_contexto, hay_errores  # noqa: E402


def run(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Procesa el evento entrante y deja el contexto listo para el siguiente agente."""
    evento = ctx.get("evento") or {}
    commerce_id = ctx.get("commerce_id") or "comercio"
    message_id = evento.get("message_id")

    if not message_id:
        ctx["estado"] = "rejected"
        ctx["errores"].append("message_id ausente en el evento de WhatsApp")
        return ctx

    clave = compute_idempotency_key(commerce_id, evento)

    if validate_event:
        validacion = validate_event(evento, commerce_id)
        if not validacion["valid"]:
            ctx["estado"] = "rejected"
            ctx["errores"].extend(validacion["errors"])
            return ctx
        evento = validacion["event"]
        clave = validacion["idempotency_key"]
        ctx["evento"] = evento

    ctx["message_id"] = str(message_id)
    ctx["customer_id"] = str(evento.get("customer_id", ""))
    ctx["transcript"] = str(evento.get("transcript", ""))
    ctx["catalog"] = list(evento.get("catalog", []) or [])
    ctx["catalog_version"] = str(evento.get("catalog_version", ""))
    ctx["audio_url"] = evento.get("audio_url")
    ctx["clave_idempotencia"] = clave

    # Detección de duplicados: si el orquestador ya guarda resultados, se consulta
    # fuera de este agente (en el pipeline). Aquí solo se anota la clave.
    ctx["estado"] = "transcribed" if ctx["transcript"] else "received"
    return ctx


def main() -> int:
    import json

    if len(sys.argv) < 3:
        print("Uso: python agente_receptor.py <commerce_id> <evento.json>")
        return 2
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        evento = json.load(f)
    ctx = nuevo_contexto(sys.argv[1], evento)
    resultado = run(ctx)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if not hay_errores(resultado) else 1


if __name__ == "__main__":
    sys.exit(main())
