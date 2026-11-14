"""Prueba de pedido ambiguo: tres pizzas pero solo dos variantes."""
import sys
import os
import json

sys.path.insert(0, r"C:\Voz a texto\agentes")
sys.path.insert(0, r"C:\Voz a texto")

import imageio_ffmpeg as i
os.environ["PATH"] = os.path.dirname(i.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

from contexto import nuevo_contexto
from agente_interpretacion import run as run_interpretacion
from agente_validacion import run as run_validacion
from agente_calculo import run as run_calculo
from agente_confirmacion import run as run_confirmacion

CATALOGO = [
    {
        "sku": "PIZ-G-MUZ", "name": "Pizza grande de muzzarella", "price": 14500,
        "currency": "ARS", "available": True, "unidad": "unidad",
        "aliases": ["pizza grande de muzza", "pizza de muzzarella", "pizza de muzza", "muzza", "musa"],
        "phonetic_aliases": ["pizza de musa", "pisa de musa", "pizza de muza"],
    },
    {
        "sku": "PIZ-G-NAP", "name": "Pizza grande napolitana", "price": 16800,
        "currency": "ARS", "available": True, "unidad": "unidad",
        "aliases": ["pizza grande napolitana", "pizza napolitana", "napolitana"],
        "phonetic_aliases": ["pizza napolitana", "napolitana"],
    },
    {
        "sku": "PIZ-G-CAL", "name": "Pizza grande calabresa", "price": 15200,
        "currency": "ARS", "available": True, "unidad": "unidad",
        "aliases": ["pizza grande calabresa", "pizza calabresa", "calabresa"],
        "phonetic_aliases": [],
    },
]

texto = "Tres pizzas, una de muzza y otra napolitana"

ctx = nuevo_contexto("comercio-test", {
    "message_id": "wamid-ambiguo-001",
    "customer_id": "customer-ambiguo-001",
    "transcript": texto,
    "catalog_version": "2026-11-14T12:00:00-03:00",
    "catalog": CATALOGO,
})

ctx = run_interpretacion(ctx)
ctx = run_validacion(ctx)
ctx = run_calculo(ctx)
ctx = run_confirmacion(ctx, numero_cliente=None, confirmacion=None)

pedido = ctx.get("pedido", {})
print(f"Estado: {ctx['estado']}")
print(f"Items: {len(pedido.get('items', []))}")
for it in pedido.get("items", []):
    print(f"  - {it['sku']}: {it['name']} qty={it['quantity']}")
print(f"Missing: {pedido.get('missing_information', [])}")
print(f"No identificados: {ctx.get('productos_no_identificados', [])}")
print(f"Subtotal: {pedido.get('subtotal', '-')}")

# Verificación: debe quedar en requires_clarification porque faltan variantes
if ctx["estado"] == "requires_clarification":
    print("\n✅ CORRECTO: Pedido ambiguo detectado, requiere aclaración")
else:
    print("\n❌ ERROR: El pedido ambiguo no fue detectado")
