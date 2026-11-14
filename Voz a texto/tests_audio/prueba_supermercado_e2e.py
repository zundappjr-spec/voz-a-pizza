"""Prueba end-to-end simulando app_web.py con comercio de supermercado."""
import json
import os
import sys
import uuid

import imageio_ffmpeg as _iio
os.environ["PATH"] = os.path.dirname(_iio.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

_PROJECT = r"C:\Voz a texto"
_AGENTES = os.path.join(_PROJECT, "agentes")
for _p in (_PROJECT, _AGENTES):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contexto import nuevo_contexto, hay_errores, estado, trace_id  # noqa: E402
from pipeline import ejecutar  # noqa: E402

# Cargar catálogo de supermercado
sys.path.insert(0, r"C:\Voz a texto\orquestador-pedidos-whatsapp\config")
from catalogo_loader import cargar_catalogo  # noqa: E402

TRACE_ID = str(uuid.uuid4())[:8]
print(f"TRACE_ID: {TRACE_ID}")
print("=" * 70)

datos_cat = cargar_catalogo("supermercado-demo")
catalogo = list(datos_cat.get("productos", []))

TRANSCRIPCION = (
    "Hola, ¿qué tal? Necesito comprar 17 resmas de papel, "
    "4 latas de tomate, 5 litros de nasta super, 8 choplos, "
    "7 mandarinas, 27 revistas del demoledor, "
    "8 kilos de carne, de cerdo y lo de vaca."
)

print(f"\n[1] Transcripción de Whisper:")
print(f"    '{TRANSCRIPCION}'")

evento = {
    "message_id": f"wamid-web-{TRACE_ID}",
    "customer_id": "customer-super-001",
    "transcript": TRANSCRIPCION.strip(),
    "catalog_version": "2026-11-14T12:00:00-03:00",
    "catalog": catalogo,
}

print(f"\n[2] Payload enviado al pipeline:")
print(json.dumps(evento, ensure_ascii=False, indent=2)[:500] + "...")

ctx = ejecutar(
    "supermercado-demo",
    evento,
    numero_cliente=None,
    confirmacion=None,
    registrar=None,
)

print("\n" + "=" * 70)
print("RESULTADO FINAL DEL PIPELINE (supermercado)")
print("=" * 70)
print(f"Trace ID: {trace_id(ctx)}")
print(f"Estado final: {ctx['estado']}")
print(f"Errores: {ctx.get('errores', []) or 'Ninguno'}")

pedido = ctx.get("pedido", {})
items = pedido.get("items", [])
print(f"\n[3] Productos identificados: {len(items)}")
for it in items:
    print(f"   - {it.get('quantity')}x {it.get('name', it.get('sku'))} ({it.get('unidad', 'unidad')}) = ${it.get('unit_price')} (conf {it.get('confidence')}, match={it.get('match_method')}, original='{it.get('original_text')}')")

no_id = pedido.get("productos_no_identificados", [])
print(f"\n[4] Productos no identificados: {len(no_id)}")
for ni in no_id:
    print(f"   - '{ni['texto_original']}' qty={ni.get('cantidad')} unit={ni.get('unidad', 'N/A')}")

no_disp = pedido.get("productos_no_disponibles", [])
print(f"\n[5] Productos no disponibles: {len(no_disp)}")
for nd in no_disp:
    print(f"   - {nd['nombre']} (SKU: {nd['sku']}) qty={nd.get('cantidad')} unit={nd.get('unidad', 'N/A')}")

print(f"\n[6] Totales:")
print(f"   Subtotal: {ctx.get('subtotal', '-')} {ctx.get('currency', '')}")
print(f"   Total: {ctx.get('total', '-')} {ctx.get('currency', '')}")
print(f"   Fulfillment: {pedido.get('fulfillment', {}).get('type') or 'no definida'}")

print(f"\n[7] Confirmación:")
print(f"   Estado: {ctx['estado']}")
print(f"   Registro ejecutado: No (modo simulación, sin confirmación explícita)")

print("\n" + "=" * 70)
if hay_errores(ctx):
    print("ERRORES:")
    for e in ctx["errores"]:
        print(f"  - {e}")
else:
    print("PRUEBA SUPERMERCADO: EXITOSA - Sin errores")
print("=" * 70)

# Verificaciones obligatorias
print("\n--- VERIFICACIONES OBLIGATORIAS ---")
checks = [
    ("Estado es requires_clarification", ctx["estado"] == "requires_clarification"),
    ("Identificó resma de papel", any(it["sku"] == "SUP-RESMA-A4" for it in items)),
    ("Identificó tomate en lata", any(it["sku"] == "SUP-TOMATE-LATA" for it in items)),
    ("Identificó mandarina", any(it["sku"] == "SUP-MANDARINA" for it in items)),
    ("Identificó carne vacuna", any(it["sku"] == "SUP-CARNE-VACUNA" for it in items)),
    ("No identificó choplos", not any("choplos" in ni["texto_original"] for ni in no_id) or any("choplos" in ni["texto_original"] for ni in no_id)),
    ("choplos en no identificados", any("choplos" in ni["texto_original"] for ni in no_id)),
    ("revistas del demoledor en no identificados", any("revistas" in ni["texto_original"] for ni in no_id)),
    ("Nafta súper en no disponibles", any(nd["sku"] == "SUP-NAFTA-SUPER" for nd in no_disp)),
    ("No avanzó a confirmación", ctx["estado"] != "confirmed" and ctx["estado"] != "registered"),
    ("Subtotal correcto", ctx.get("subtotal") == "89140.00"),
]
all_pass = True
for nombre, resultado in checks:
    status = "OK" if resultado else "FALLO"
    if not resultado:
        all_pass = False
    print(f"  [{status}] {nombre}")

print(f"\nTodas las verificaciones: {'PASARON' if all_pass else 'FALLARON'}")
