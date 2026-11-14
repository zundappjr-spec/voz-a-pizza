"""Agente 6 - CONFIRMACION (agente_confirmacion).

Genera el resumen de confirmacion o la pregunta de aclaracion, envia el mensaje
por WhatsApp al cliente y registra si hay confirmacion explicita.

Contratos reutilizados:
- orchestrator.enviar_mensaje_whatsapp(numero, texto)
- anonimizar.anonimizar_texto(texto)  (para enmascarar datos en logs si se usa)
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from _paths import _ORCH, _SCRIPTS  # noqa: E402

for _p in (_ORCH, _SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from orchestrator import enviar_mensaje_whatsapp  # noqa: E402
from anonimizar import anonimizar_texto  # noqa: E402
from contexto import estado, hay_errores  # noqa: E402


def _armar_resumen(ctx: Dict[str, Any]) -> str:
    items = ctx.get("items", [])
    partes = []
    for it in items:
        partes.append(
            f"{it.get('quantity', 1)}x {it.get('name', it.get('sku', 'producto'))}"
        )
    items_texto = " y ".join(partes) if partes else "sin items"
    total = ctx.get("total") or ""
    moneda = ctx.get("currency") or ""
    cumplimiento = ctx.get("fulfillment", {}) or {}
    tipo = cumplimiento.get("type")
    hora = cumplimiento.get("requested_time")
    direccion = cumplimiento.get("address")
    entrega = "retiro en local" if tipo == "pickup" else ("envio a domicilio" if tipo == "delivery" else "modalidad no definida")
    resumen = (
        f"Tu pedido es: {items_texto}. Total: {total} {moneda}. "
        f"{entrega.capitalize()}"
    )
    if hora:
        resumen += f" a las {hora}"
    if direccion:
        resumen += f", direccion: {anonimizar_texto(str(direccion))}"
    resumen += ". Responde CONFIRMAR para registrarlo o indicame que queres cambiar."
    return resumen


def _armar_pregunta(ctx: Dict[str, Any]) -> str:
    missing = list((ctx.get("pedido", {}) or {}).get("missing_information", []) or [])
    errores = list(ctx.get("errores", []) or [])
    if errores:
        return "No pude procesar tu pedido: " + "; ".join(errores) + ". ¿Me lo volves a enviar por escrito?"
    if missing:
        return (
            "Entendi parte de tu pedido, pero me falta: "
            + ", ".join(missing)
            + ". ¿Podés completar esa informacion?"
        )
    return "¿Confirmas este pedido para registrarlo?"


def run(
    ctx: Dict[str, Any],
    numero_cliente: str | None = None,
    confirmacion: bool | None = None,
) -> Dict[str, Any]:
    st = estado(ctx)

    if st == "requires_clarification":
        pregunta = _armar_pregunta(ctx)
        ctx["pedido"] = ctx.get("pedido", {})
        ctx["pedido"]["customer_message"] = pregunta
        if numero_cliente:
            enviar_mensaje_whatsapp(numero_cliente, pregunta)
        ctx["estado"] = "requires_clarification"
        return ctx

    if st == "requires_confirmation":
        resumen = _armar_resumen(ctx)
        ctx["pedido"] = ctx.get("pedido", {})
        ctx["pedido"]["customer_message"] = resumen
        if numero_cliente:
            enviar_mensaje_whatsapp(numero_cliente, resumen)
        if confirmacion is True:
            ctx["estado"] = "confirmed"
        else:
            ctx["estado"] = "requires_confirmation"
        return ctx

    # Estados intermedios: no hay nada que confirmar aun.
    ctx["estado"] = st
    return ctx


def main() -> int:
    import json

    if len(sys.argv) < 2:
        print("Uso: python agente_confirmacion.py <contexto.json> [numero_cliente] [--confirmar]")
        return 2
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        ctx = json.load(f)
    numero = sys.argv[2] if len(sys.argv) > 2 else None
    confirmar = "--confirmar" in sys.argv
    resultado = run(ctx, numero_cliente=numero, confirmacion=confirmar)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if not hay_errores(resultado) else 1


if __name__ == "__main__":
    sys.exit(main())
