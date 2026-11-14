"""Helpers de contexto compartido entre los 7 agentes.

Un contexto es un dict que se muta y pasa de agente en agente. Contiene todo
lo necesario para avanzar por el flujo de estados del SKILL.md existente.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

DEFAULT_CATALOG: list[dict[str, Any]] = []


def nuevo_contexto(
    commerce_id: str,
    evento: Dict[str, Any] | None = None,
    trace_id: str | None = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Crea un contexto inicial a partir de un evento de WhatsApp."""
    evento = evento or {}
    trace_id = trace_id or str(uuid.uuid4())[:8]
    ctx: Dict[str, Any] = {
        "trace_id": trace_id,
        "commerce_id": commerce_id,
        "evento": evento,
        "message_id": evento.get("message_id"),
        "customer_id": evento.get("customer_id", ""),
        "transcript": str(evento.get("transcript", "")),
        "catalog": list(evento.get("catalog", []) or DEFAULT_CATALOG),
        "catalog_version": str(evento.get("catalog_version", "")),
        "audio_url": evento.get("audio_url"),
        "items": [],
        "fulfillment": {},
        "fulfillment_type": None,
        "subtotal": "",
        "total": "",
        "currency": "",
        "line_totals": [],
        "estado": "received",
        "clave_idempotencia": None,
        "clave_pedido": None,
        "pedido": {},
        "registro": {},
        "errores": [],
        "advertencias": [],
        "simulacion": True,
    }
    ctx.update(extra)
    return ctx


def hay_errores(ctx: Dict[str, Any]) -> bool:
    return bool(ctx.get("errores"))


def estado(ctx: Dict[str, Any]) -> str:
    return str(ctx.get("estado", "received"))


def trace_id(ctx: Dict[str, Any]) -> str:
    return str(ctx.get("trace_id", "desconocido"))
