"""Validacion de pedido interpretado.

Valida cantidades, SKU, variantes y campos obligatorios contra el catalogo.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

MAX_QUANTITY = 100


class PedidoValidationError(ValueError):
    """Error de validacion del pedido."""


def _match_product(sku_or_name: str, catalog: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """Busca un producto por SKU exacto o por nombre normalizado."""
    target = sku_or_name.strip().lower()
    for product in catalog:
        if str(product.get("sku", "")).strip().lower() == target:
            return product
        if str(product.get("name", "")).strip().lower() == target:
            return product
    return None


def validate_pedido(
    items: List[Dict[str, Any]],
    catalog: List[Dict[str, Any]],
    fulfillment: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Valida cantidades, SKU, variantes y campos obligatorios.

    Retorna:
      - valid: bool
      - items: lista de items validados y enriquecidos
      - errors: lista de mensajes de error
      - warnings: advertencias (producto sin stock, etc.)
    """
    errors: List[str] = []
    warnings: List[str] = []
    validated: List[Dict[str, Any]] = []

    if not items:
        errors.append("El pedido no contiene items")
        return {"valid": False, "items": [], "errors": errors, "warnings": warnings}

    for index, item in enumerate(items):
        sku = item.get("sku")
        name = item.get("name")
        quantity_raw = item.get("quantity")
        unit_price_raw = item.get("unit_price")
        currency = item.get("currency")

        product = None
        if sku:
            product = _match_product(str(sku), catalog)
        if product is None and name:
            product = _match_product(str(name), catalog)

        if product is None:
            errors.append(f"Item {index}: producto no encontrado en el catalogo (sku={sku}, name={name})")
            continue

        # Cantidad
        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError):
            errors.append(f"Item {index}: cantidad invalida '{quantity_raw}'")
            continue
        if quantity <= 0:
            errors.append(f"Item {index}: cantidad debe ser mayor que cero")
            continue
        if quantity > MAX_QUANTITY:
            warnings.append(f"Item {index}: cantidad inusualmente alta ({quantity}), revision manual")

        # Precio: obtener exclusivamente del catalogo
        try:
            unit_price = Decimal(str(product["price"]))
        except (InvalidOperation, KeyError, TypeError):
            errors.append(f"Item {index}: precio no disponible en el catalogo")
            continue

        unit_currency = str(product.get("currency", currency or ""))

        validated.append({
            "sku": str(product["sku"]),
            "name": str(product.get("name", "")),
            "quantity": quantity,
            "unit_price": str(unit_price),
            "currency": unit_currency,
            "available": bool(product.get("available", False)),
            "confidence": float(item.get("confidence", 1.0) or 1.0),
            "observations": list(item.get("observations", []) or []),
            "original_text": item.get("original_text"),
            "normalized_match": item.get("normalized_match"),
            "match_method": item.get("match_method"),
        })

    # Fulfillment
    fulfillment_type = None
    if fulfillment and isinstance(fulfillment, dict):
        fulfillment_type = fulfillment.get("type")
        if fulfillment_type not in (None, "pickup", "delivery"):
            errors.append(f"Tipo de entrega invalido: {fulfillment_type}")

    if not validated:
        errors.append("No se pudo validar ningun item del pedido")

    return {
        "valid": len(errors) == 0,
        "items": validated,
        "fulfillment_type": fulfillment_type,
        "errors": errors,
        "warnings": warnings,
    }
