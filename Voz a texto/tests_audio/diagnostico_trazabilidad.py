"""Diagnóstico de trazabilidad: compara intérprete directo vs pipeline.

Utiliza un mismo trace_id para toda la operación y registra:
1. Transcripción exacta generada por Whisper.
2. Transcripción recibida por app_web.py.
3. Payload enviado al pipeline.
4. Payload recibido por agente_interpretacion.py.
5. Catálogo efectivamente cargado.
6. Resultado devuelto por interpretar_pedido.
7. Estado recibido por agente_validacion.py.
8. Estado final del pipeline.
"""

from __future__ import annotations

import json
import os
import sys
import uuid

# --- Asegurar ffmpeg para faster-whisper -------------------------------------
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

# --- TRACE_ID compartido ------------------------------------------------------
TRACE_ID = str(uuid.uuid4())[:8]
print(f"=" * 70)
print(f"TRACE_ID: {TRACE_ID}")
print(f"=" * 70)

from contexto import nuevo_contexto, hay_errores, estado  # noqa: E402
from agente_interpretacion import run as run_interpretacion  # noqa: E402
from agente_validacion import run as run_validacion  # noqa: E402
from agente_calculo import run as run_calculo  # noqa: E402
from agente_confirmacion import run as run_confirmacion  # noqa: E402
from pipeline import ejecutar  # noqa: E402

# --- Transcripción real de Whisper (igual que la que generaría app_web) ------
TRANSCRIPCION_WHISPER = (
    "Hola, quiero pedir dos pisas grandes, una de musa "
    "y otra napolitana para retirar."
)

CATALOGO = [
    {"sku": "PIZ-G-MUZ", "name": "Pizza grande de muzzarella", "price": 14500, "currency": "ARS", "available": True},
    {"sku": "PIZ-G-NAP", "name": "Pizza grande napolitana", "price": 16800, "currency": "ARS", "available": True},
    {"sku": "PIZ-G-CAL", "name": "Pizza grande calabresa", "price": 15200, "currency": "ARS", "available": True},
]

# ---------------------------------------------------------------------------
print("\n[1] TRANSCRIPCION EXACTA GENERADA POR WHISPER:")
print(f"    '{TRANSCRIPCION_WHISPER}'")
print(f"    Trace ID: {TRACE_ID}")

# ===========================================================================
# CAMINO A: Invocación directa del intérprete (como en test_pedidos.py)
# ===========================================================================
print("\n" + "=" * 70)
print("CAMINO A: Intérprete directo")
print("=" * 70)

evento_a = {
    "message_id": f"wamid-{TRACE_ID}",
    "customer_id": "customer-diag-001",
    "transcript": TRANSCRIPCION_WHISPER,
    "catalog_version": "2026-11-14T12:00:00-03:00",
    "catalog": CATALOGO,
}

print("\n[2] TRANSCRIPCION RECIBIDA POR app_web.py (igual que Whisper):")
print(f"    '{evento_a['transcript']}'")
print(f"    Trace ID: {TRACE_ID}")

print("\n[3] PAYLOAD ENVIADO AL INTÉRPRETE (camino directo):")
print(json.dumps(evento_a, ensure_ascii=False, indent=2))

ctx_a = nuevo_contexto("comercio-diag", evento_a)
ctx_a = run_interpretacion(ctx_a)
ctx_a = run_validacion(ctx_a)
ctx_a = run_calculo(ctx_a)
ctx_a = run_confirmacion(ctx_a, numero_cliente=None, confirmacion=None)

print("\n[6] RESULTADO DE interpretar_pedido (camino directo):")
pedido_a = ctx_a.get("pedido", {})
print(json.dumps(pedido_a, ensure_ascii=False, indent=2))

print("\n[7] ESTADO RECIBIDO POR agente_validacion.py (camino directo):")
print(f"    estado: {ctx_a['estado']}")
print(f"    errores: {ctx_a.get('errores', [])}")
print(f"    items: {len(ctx_a.get('items', []))}")
print(f"    Trace ID: {TRACE_ID}")

print("\n[8] ESTADO FINAL DEL PIPELINE (camino directo):")
print(f"    estado: {ctx_a['estado']}")
print(f"    subtotal: {ctx_a.get('subtotal', '-')}")
print(f"    total: {ctx_a.get('total', '-')}")
print(f"    fulfillment: {ctx_a.get('fulfillment', {})}")
print(f"    Trace ID: {TRACE_ID}")

# ===========================================================================
# CAMINO B: Invocación desde Streamlit mediante el pipeline
# ===========================================================================
print("\n" + "=" * 70)
print("CAMINO B: Pipeline (como desde Streamlit/app_web.py)")
print("=" * 70)

evento_b = {
    "message_id": f"wamid-web-{TRACE_ID}",
    "customer_id": "customer-diag-001",
    "transcript": TRANSCRIPCION_WHISPER,
    "catalog_version": "2026-11-14T12:00:00-03:00",
    "catalog": CATALOGO,
}

print("\n[2] TRANSCRIPCION RECIBIDA POR app_web.py (camino B):")
print(f"    '{evento_b['transcript']}'")
print(f"    Trace ID: {TRACE_ID}")

print("\n[3] PAYLOAD ENVIADO AL PIPELINE (camino B):")
print(json.dumps(evento_b, ensure_ascii=False, indent=2))

ctx_b = ejecutar(
    "comercio-diag",
    evento_b,
    numero_cliente=None,
    confirmacion=None,
    registrar=None,
)

print("\n[4] PAYLOAD RECIBIDO POR agente_interpretacion.py (camino B):")
# El contexto antes de interpretación ya pasó por receptor y transcripción
# Mostramos el estado del contexto en ese punto reconstruyéndolo:
ctx_b_pre = nuevo_contexto("comercio-diag", evento_b)
ctx_b_pre = run_interpretacion(ctx_b_pre)  # transcripción salta porque ya hay transcript
print(json.dumps(ctx_b_pre, ensure_ascii=False, indent=2))

print("\n[6] RESULTADO DE interpretar_pedido (camino B):")
pedido_b = ctx_b.get("pedido", {})
print(json.dumps(pedido_b, ensure_ascii=False, indent=2))

print("\n[7] ESTADO RECIBIDO POR agente_validacion.py (camino B):")
print(f"    estado: {ctx_b['estado']}")
print(f"    errores: {ctx_b.get('errores', [])}")
print(f"    items: {len(ctx_b.get('items', []))}")
print(f"    Trace ID: {TRACE_ID}")

print("\n[8] ESTADO FINAL DEL PIPELINE (camino B):")
print(f"    estado: {ctx_b['estado']}")
print(f"    subtotal: {ctx_b.get('subtotal', '-')}")
print(f"    total: {ctx_b.get('total', '-')}")
print(f"    fulfillment: {ctx_b.get('fulfillment', {})}")
print(f"    Trace ID: {TRACE_ID}")

# ===========================================================================
# COMPARACIÓN
# ===========================================================================
print("\n" + "=" * 70)
print("COMPARACIÓN CAMINO A vs CAMINO B")
print("=" * 70)

campos = ["estado", "subtotal", "total", "currency", "errores"]
for campo in campos:
    va = ctx_a.get(campo)
    vb = ctx_b.get(campo)
    igual = va == vb
    print(f"  {campo}: A={va} | B={vb} | {'IGUAL' if igual else 'DIFERENTE'}")

items_a = ctx_a.get("items", [])
items_b = ctx_b.get("items", [])
print(f"  items_count: A={len(items_a)} | B={len(items_b)} | {'IGUAL' if len(items_a)==len(items_b) else 'DIFERENTE'}")

fulfillment_a = ctx_a.get("fulfillment", {})
fulfillment_b = ctx_b.get("fulfillment", {})
print(f"  fulfillment.type: A={fulfillment_a.get('type')} | B={fulfillment_b.get('type')}")

print("\n" + "=" * 70)
print("FIN DEL DIAGNÓSTICO")
print("=" * 70)
