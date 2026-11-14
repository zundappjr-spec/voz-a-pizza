"""Debug prueba 1 y 2 del intérprete."""
import sys
import os
import json

sys.path.insert(0, r"C:\Voz a texto\agentes")
sys.path.insert(0, r"C:\Voz a texto")

import imageio_ffmpeg as i
os.environ["PATH"] = os.path.dirname(i.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

from contexto import nuevo_contexto
from agente_interpretacion import run as run_interpretacion

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

def run_texto(texto, comercio_id="comercio-test"):
    ctx = nuevo_contexto(comercio_id, {
        "message_id": "wamid-test", "customer_id": "customer-test",
        "transcript": texto, "catalog_version": "2026-11-14T12:00:00-03:00",
        "catalog": CATALOGO,
    })
    ctx = run_interpretacion(ctx)
    return ctx

# Prueba 1
ctx1 = run_texto("dos pizzas, una de muzza y otra napolitana")
print("=== Prueba 1: dos pizzas, una de muzza y otra napolitana ===")
print(f"Estado: {ctx1['estado']}")
print(f"Items: {len(ctx1.get('items', []))}")
for it in ctx1.get("items", []):
    print(f"  - {it['sku']}: {it['name']} qty={it['quantity']}")
pedido = ctx1.get("pedido", {})
print(f"Missing: {pedido.get('missing_information', [])}")
print(f"No identificados: {ctx1.get('productos_no_identificados', [])}")
print(f"No disponibles: {ctx1.get('productos_no_disponibles', [])}")

# Prueba 2
ctx2 = run_texto("dos pisas, una de musa y otra napolitana")
print("\n=== Prueba 2: dos pisas, una de musa y otra napolitana ===")
print(f"Estado: {ctx2['estado']}")
print(f"Items: {len(ctx2.get('items', []))}")
for it in ctx2.get("items", []):
    print(f"  - {it['sku']}: {it['name']} qty={it['quantity']}")
pedido2 = ctx2.get("pedido", {})
print(f"Missing: {pedido2.get('missing_information', [])}")
print(f"No identificados: {ctx2.get('productos_no_identificados', [])}")
print(f"No disponibles: {ctx2.get('productos_no_disponibles', [])}")
