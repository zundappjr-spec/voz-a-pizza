"""Validacion de evento entrante de WhatsApp.

Valida esquema, tipo de mensaje e idempotencia inicial.
No realiza llamadas de red. Retorna un resultado estructurado.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict

REQUIRED_FIELDS = ("message_id", "customer_id", "catalog_version", "catalog")
MESSAGE_ID_RE = re.compile(r"^wamid-[A-Za-z0-9_-]+$")
CATALOG_VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


class EventValidationError(ValueError):
    """Error de validacion del evento entrante."""


def compute_idempotency_key(commerce_id: str, event: Dict[str, Any]) -> str:
    """Calcula la clave de idempotencia inicial del evento."""
    message_id = event.get("message_id", "")
    operation = "interpret"
    catalog_version = event.get("catalog_version", "")
    raw = f"{commerce_id}|{message_id}|{operation}|{catalog_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_event(event: Dict[str, Any], commerce_id: str) -> Dict[str, Any]:
    """Valida el esquema del evento, tipo de mensaje e idempotencia inicial.

    Retorna un dict con:
      - valid: bool
      - event: el evento normalizado si es valido
      - idempotency_key: clave calculada
      - errors: lista de mensajes de error
    """
    errors: list[str] = []

    if not isinstance(event, dict):
        return {
            "valid": False,
            "event": None,
            "idempotency_key": None,
            "errors": ["El evento no es un objeto JSON valido"],
        }

    for field in REQUIRED_FIELDS:
        if field not in event or event[field] is None or event[field] == "":
            errors.append(f"Campo obligatorio ausente o vacio: {field}")

    message_id = event.get("message_id", "")
    if message_id and not MESSAGE_ID_RE.match(str(message_id)):
        errors.append(f"message_id con formato invalido: {message_id}")

    catalog_version = event.get("catalog_version", "")
    if catalog_version and not CATALOG_VERSION_RE.match(str(catalog_version)):
        errors.append(f"catalog_version con formato invalido: {catalog_version}")

    catalog = event.get("catalog")
    if catalog is not None:
        if not isinstance(catalog, list):
            errors.append("catalog debe ser una lista")
        else:
            for i, product in enumerate(catalog):
                if not isinstance(product, dict):
                    errors.append(f"catalog[{i}] no es un objeto")
                    continue
                for pf in ("sku", "name", "price", "currency", "available"):
                    if pf not in product:
                        errors.append(f"catalog[{i}] falta campo: {pf}")

    if errors:
        return {
            "valid": False,
            "event": None,
            "idempotency_key": None,
            "errors": errors,
        }

    normalized = {
        "message_id": str(message_id).strip(),
        "customer_id": str(event.get("customer_id", "")).strip(),
        "transcript": str(event.get("transcript", "")).strip(),
        "catalog_version": str(catalog_version).strip(),
        "catalog": catalog,
    }

    return {
        "valid": True,
        "event": normalized,
        "idempotency_key": compute_idempotency_key(commerce_id, normalized),
        "errors": [],
    }
