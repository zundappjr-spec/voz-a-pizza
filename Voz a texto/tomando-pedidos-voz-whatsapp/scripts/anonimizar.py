"""Anonimizacion de datos personales.

Elimina o enmascara datos personales antes de logs o evaluaciones.
"""

from __future__ import annotations

import re
from typing import Any, Dict

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s-]?)?(\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{4}")


def _mask_phone(value: str) -> str:
    masked = PHONE_RE.sub("[telefono]", value)
    return masked


def _mask_email(value: str) -> str:
    return EMAIL_RE.sub("[email]", value)


def anonimizar_texto(texto: str) -> str:
    """Enmascara telefonos y emails en un texto libre."""
    if not texto:
        return texto
    texto = _mask_phone(texto)
    texto = _mask_email(texto)
    return texto


def anonimizar_pedido(pedido: Dict[str, Any]) -> Dict[str, Any]:
    """Retorna una copia del pedido con datos amarillos enmascarados."""
    import copy

    anon = copy.deepcopy(pedido)

    customer_id = anon.get("customer_id")
    if customer_id:
        anon["customer_id"] = f"c-{str(customer_id)[-4:]}" if len(str(customer_id)) >= 4 else "c-anon"

    fulfillment = anon.get("fulfillment") or {}
    if isinstance(fulfillment, dict):
        if fulfillment.get("address"):
            fulfillment["address"] = "[direccion]"
        if fulfillment.get("requested_time"):
            fulfillment["requested_time"] = "[hora]"

    customer_message = anon.get("customer_message")
    if customer_message:
        anon["customer_message"] = anonimizar_texto(str(customer_message))

    for item in anon.get("items", []) or []:
        item.pop("name", None)

    # Audio y transcripcion no se conservan en logs
    anon.pop("transcript", None)
    anon.pop("audio_url", None)

    return anon


def anonimizar_para_log(registro: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara un registro para logueo: elimina datos rojos y enmascara amarillos."""
    import copy

    anon = copy.deepcopy(registro)

    # Datos rojos: nunca loguear
    for campo_rojo in ("token", "credencial", "password", "api_key", "secret", "card", "tarjeta", "cvv"):
        for key in list(anon.keys()):
            if campo_rojo in key.lower():
                anon[key] = "[redactado]"

    if "pedido" in anon and isinstance(anon["pedido"], dict):
        anon["pedido"] = anonimizar_pedido(anon["pedido"])

    if "transcript" in anon:
        anon["transcript"] = "[transcripcion omitida]"
    if "audio" in anon:
        anon["audio"] = "[audio omitido]"

    return anon
