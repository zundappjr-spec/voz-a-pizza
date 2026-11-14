"""Prueba final de registro en simulación pura."""
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

TRACE_ID = str(uuid.uuid4())[:8]
print(f"TRACE_ID: {TRACE_ID}")
print("=" * 70)
print("PRUEBA FINAL: Registro en simulación pura (sin --registrar)")
print("=" * 70)

with open(r"C:\Voz a texto\tests_audio\evento_pizzeria.json", "r", encoding="utf-8") as f:
    evento = json.load(f)

ctx = ejecutar(
    "pizzeria-demo",
    evento,
    numero_cliente="5491122334455",
    confirmacion=True,  # Confirmación explícita
    registrar=None,     # Simulación por defecto (REGISTRAR_PEDIDOS no activo)
)

print(f"\nResultado:")
print(f"  Estado final: {ctx['estado']}")
print(f"  Trace ID: {trace_id(ctx)}")
print(f"  Errores: {ctx.get('errores', []) or 'Ninguno'}")
print(f"  Simulación: {ctx.get('simulacion', True)}")

pedido = ctx.get("pedido", {})
print(f"\n  Items: {len(pedido.get('items', []))}")
for it in pedido.get("items", []):
    print(f"    - {it.get('quantity')}x {it.get('name', it.get('sku'))} = ${it.get('unit_price')}")

print(f"\n  Subtotal: {ctx.get('subtotal', '-')} {ctx.get('currency', '')}")
print(f"  Total: {ctx.get('total', '-')} {ctx.get('currency', '')}")
print(f"  Fulfillment: {pedido.get('fulfillment', {}).get('type') or 'no definida'}")

registro = ctx.get("registro", {})
if registro:
    print(f"\n  Registro:")
    print(f"    Estado: {registro.get('estado')}")
    print(f"    Clave de pedido: {registro.get('clave_pedido')}")
    print(f"    Simulación: {registro.get('simulacion')}")
    if registro.get("mensaje"):
        print(f"    Mensaje: {registro.get('mensaje')}")

print(f"\n  Mensaje al cliente: {pedido.get('customer_message', '-')}")

# Verificaciones
print(f"\n{'='*70}")
print("VERIFICACIONES FINALES")
print(f"{'='*70}")

checks = [
    ("Estado es requires_confirmation", ctx["estado"] == "requires_confirmation"),
    ("Sin errores", not hay_errores(ctx)),
    ("2 productos identificados", len(pedido.get("items", [])) == 2),
    ("Subtotal 31300.00", ctx.get("subtotal") == "31300.00"),
    ("Fulfillment pickup", pedido.get("fulfillment", {}).get("type") == "pickup"),
    ("Registro en simulación (borrador)", registro.get("estado") == "borrador"),
    ("Clave de pedido generada", registro.get("clave_pedido") is not None),
    ("Mensaje al cliente generado", bool(pedido.get("customer_message"))),
]

todos_ok = True
for nombre, resultado in checks:
    status = "OK" if resultado else "FALLO"
    if not resultado:
        todos_ok = False
    print(f"  [{status}] {nombre}")

print(f"\nTodas las verificaciones: {'PASARON' if todos_ok else 'FALLARON'}")

# Guardar resultado
with open(r"C:\Voz a texto\tests_audio\resultado_registro_simulacion.json", "w", encoding="utf-8") as f:
    json.dump(ctx, f, ensure_ascii=False, indent=2)
print(f"\nResultado guardado en: tests_audio/resultado_registro_simulacion.json")

sys.exit(0 if todos_ok else 1)
