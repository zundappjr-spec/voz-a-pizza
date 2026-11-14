"""Simulación de app_web.py sin Streamlit para diagnóstico.

Imita exactamente el flujo de app_web.py:
1. Construye el evento desde un transcript dado
2. Llama a ejecutar() del pipeline
3. Imprime trace_id y estado de cada agente
"""

from __future__ import annotations

import json
import os
import sys
import uuid

# --- Asegurar ffmpeg ----------------------------------------------------------
import imageio_ffmpeg as _iio  # noqa: E402

os.environ["PATH"] = (
    os.path.dirname(_iio.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")
)

# --- Rutas -------------------------------------------------------------------
_PROJECT = r"C:\Voz a texto"
_AGENTES = os.path.join(_PROJECT, "agentes")
for _p in (_PROJECT, _AGENTES):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contexto import nuevo_contexto, hay_errores, estado, trace_id  # noqa: E402
from pipeline import ejecutar  # noqa: E402

# --- Transcripción de Whisper (misma que se usaría desde audio real) ---------
TRANSCRIPCION = (
    "Hola, quiero pedir dos pisas grandes, una de musa "
    "y otra napolitana para retirar."
)

CATALOGO = [
    {"sku": "PIZ-G-MUZ", "name": "Pizza grande de muzzarella", "price": 14500, "currency": "ARS", "available": True},
    {"sku": "PIZ-G-NAP", "name": "Pizza grande napolitana", "price": 16800, "currency": "ARS", "available": True},
    {"sku": "PIZ-G-CAL", "name": "Pizza grande calabresa", "price": 15200, "currency": "ARS", "available": True},
]

# --- Simular lo que hace app_web.py ------------------------------------------
trace_id_val = str(uuid.uuid4())[:8]
print(f"TRACE_ID: {trace_id_val}")
print(f"Transcripción de Whisper: '{TRANSCRIPCION}'")
print()

evento = {
    "message_id": f"wamid-web-{trace_id_val}",
    "customer_id": "customer-sim-001",
    "transcript": TRANSCRIPCION.strip(),
    "catalog_version": "2026-11-14T12:00:00-03:00",
    "catalog": CATALOGO,
}

print("Payload enviado al pipeline:")
print(json.dumps(evento, ensure_ascii=False, indent=2))
print()

ctx = ejecutar(
    "comercio-sim",
    evento,
    numero_cliente=None,
    confirmacion=None,
    registrar=None,
)

print("=" * 60)
print("RESULTADO FINAL DEL PIPELINE (simulación de app_web.py)")
print("=" * 60)
print(f"Trace ID: {trace_id(ctx)}")
print(f"Estado final: {ctx['estado']}")
print(f"Errores: {ctx.get('errores', [])}")
print(f"Ítems: {len(ctx.get('items', []))}")
print(f"Subtotal: {ctx.get('subtotal', '-')}")
print(f"Total: {ctx.get('total', '-')}")
print(f"Fulfillment: {ctx.get('fulfillment', {})}")
print()

pedido = ctx.get("pedido", {})
if pedido:
    print("Pedido interpretado:")
    print(json.dumps(pedido, ensure_ascii=False, indent=2))

print()
if hay_errores(ctx):
    print("ERRORES DETECTADOS:")
    for e in ctx["errores"]:
        print(f"  - {e}")
else:
    print("SIN ERRORES")

print()
print("Estado de cada agente (reconstruido desde el contexto):")
print(f"  Receptor: {ctx.get('estado', 'N/A')}")
print(f"  Transcripción: {'completa' if ctx.get('transcript') else 'vacía'}")
print(f"  Interpretación: {len(ctx.get('items', []))} ítems identificados")
print(f"  Validación: {'ok' if not ctx.get('errores') else 'con errores'}")
print(f"  Cálculo: subtotal={ctx.get('subtotal', '-')}, total={ctx.get('total', '-')}")
print(f"  Confirmación: {ctx['estado']}")
print(f"  Registro: {'no ejecutado (pendiente confirmación)' if ctx['estado'] in ('requires_confirmation', 'requires_clarification') else 'ejecutado'}")
