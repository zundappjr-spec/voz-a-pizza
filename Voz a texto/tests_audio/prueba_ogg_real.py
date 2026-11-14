"""Prueba end-to-end con archivo OGG real (PASO 4).

1. Transcribir OGG con faster-whisper
2. Mostrar texto reconocido
3. Enviar al pipeline
4. Identificar productos
5. Detectar cantidades y modalidad
6. Calcular total
7. Solicitar confirmación (sin registro real)
"""

from __future__ import annotations

import json
import os
import sys
import uuid

import imageio_ffmpeg as _iio  # noqa: E402

os.environ["PATH"] = (
    os.path.dirname(_iio.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")
)

_PROJECT = r"C:\Voz a texto"
_AGENTES = os.path.join(_PROJECT, "agentes")
for _p in (_PROJECT, _AGENTES):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from transcriptor import transcribir  # noqa: E402
from contexto import nuevo_contexto, hay_errores, estado, trace_id  # noqa: E402
from pipeline import ejecutar  # noqa: E402

TRACE_ID = str(uuid.uuid4())[:8]
print(f"TRACE_ID: {TRACE_ID}")
print("=" * 60)

# 1. Transcribir OGG real con Whisper
ogg_path = r"C:\Voz a texto\tests_audio\habla.ogg"
print(f"\n[1] Transcribiendo archivo OGG: {ogg_path}")
texto_whisper = transcribir(ogg_path, idioma="es")
print(f"[2] Texto reconocido por Whisper: '{texto_whisper}'")
assert texto_whisper.strip(), "Transcripción vacía"
print("   OK: transcripción no vacía")

# 3. Enviar al pipeline
evento = {
    "message_id": f"wamid-ogg-{TRACE_ID}",
    "customer_id": "customer-ogg-001",
    "transcript": texto_whisper.strip(),
    "catalog_version": "2026-11-14T12:00:00-03:00",
    "catalog": [
        {"sku": "PIZ-G-MUZ", "name": "Pizza grande de muzzarella", "price": 14500, "currency": "ARS", "available": True},
        {"sku": "PIZ-G-NAP", "name": "Pizza grande napolitana", "price": 16800, "currency": "ARS", "available": True},
        {"sku": "PIZ-G-CAL", "name": "Pizza grande calabresa", "price": 15200, "currency": "ARS", "available": True},
    ],
}

print(f"\n[3] Payload enviado al pipeline:")
print(json.dumps(evento, ensure_ascii=False, indent=2))

ctx = ejecutar(
    "comercio-ogg",
    evento,
    numero_cliente=None,
    confirmacion=None,
    registrar=None,
)

# 4-7. Resultados
print("\n" + "=" * 60)
print("RESULTADOS DEL PIPELINE (OGG real)")
print("=" * 60)
print(f"Trace ID: {trace_id(ctx)}")
print(f"Estado final: {ctx['estado']}")
print(f"Errores: {ctx.get('errores', []) or 'Ninguno'}")

pedido = ctx.get("pedido", {})
items = pedido.get("items", [])
print(f"\n[4] Productos identificados: {len(items)}")
for it in items:
    print(f"   - {it.get('quantity')}x {it.get('name', it.get('sku'))} = ${it.get('unit_price')} (confianza {it.get('confidence')}, original: '{it.get('original_text')}')")

print(f"\n[5] Cantidades y modalidad:")
print(f"   Fulfillment type: {pedido.get('fulfillment', {}).get('type') or 'no definida'}")
for it in items:
    print(f"   - {it.get('sku')}: qty={it.get('quantity')}")

print(f"\n[6] Totales:")
print(f"   Subtotal: {ctx.get('subtotal', '-')} {ctx.get('currency', '')}")
print(f"   Total: {ctx.get('total', '-')} {ctx.get('currency', '')}")

print(f"\n[7] Confirmación:")
print(f"   Estado: {ctx['estado']}")
print(f"   Mensaje al cliente: {pedido.get('customer_message', '-')}")
print(f"   Registro ejecutado: No (modo simulación, sin confirmación explícita)")

print("\n" + "=" * 60)
if hay_errores(ctx):
    print("ERRORES DETECTADOS:")
    for e in ctx["errores"]:
        print(f"  - {e}")
else:
    print("PRUEBA OGG REAL: EXITOSA - Sin errores")
print("=" * 60)
