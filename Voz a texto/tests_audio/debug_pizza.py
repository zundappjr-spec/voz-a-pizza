"""Debug: ver qué catálogo llega al intérprete."""
import sys
import os
import json

sys.path.insert(0, r"C:\Voz a texto\agentes")
sys.path.insert(0, r"C:\Voz a texto")

import imageio_ffmpeg as i
os.environ["PATH"] = os.path.dirname(i.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

from contexto import nuevo_contexto
from agente_interpretacion import run as run_interpretacion, _cargar_catalogo_comercio, cargar_catalogo

CATALOGO = [
    {
        "sku": "PIZ-G-MUZ",
        "name": "Pizza grande de muzzarella",
        "price": 14500,
        "currency": "ARS",
        "available": True,
        "unidad": "unidad",
        "aliases": ["pizza grande de muzza", "pizza de muzzarella", "pizza de muzza", "muzza", "musa"],
        "phonetic_aliases": ["pizza de musa", "pisa de musa", "pizza de muza"],
    },
    {
        "sku": "PIZ-G-NAP",
        "name": "Pizza grande napolitana",
        "price": 16800,
        "currency": "ARS",
        "available": True,
        "unidad": "unidad",
        "aliases": ["pizza grande napolitana", "pizza napolitana", "napolitana"],
        "phonetic_aliases": ["pizza napolitana", "napolitana"],
    },
    {
        "sku": "PIZ-G-CAL",
        "name": "Pizza grande calabresa",
        "price": 15200,
        "currency": "ARS",
        "available": True,
        "unidad": "unidad",
        "aliases": ["pizza grande calabresa", "pizza calabresa", "calabresa"],
        "phonetic_aliases": [],
    },
]

print(f"cargar_catalogo disponible: {cargar_catalogo is not None}")

# Probar carga directa
try:
    datos = cargar_catalogo("comercio-test")
    print(f"cargar_catalogo('comercio-test') retornó: {datos}")
except Exception as e:
    print(f"cargar_catalogo('comercio-test') falló: {type(e).__name__}: {e}")

# Probar _cargar_catalogo_comercio
cat = _cargar_catalogo_comercio("comercio-test", CATALOGO)
print(f"_cargar_catalogo_comercio retornó {len(cat)} productos")
for p in cat:
    print(f"  - {p.get('sku')}: {p.get('name')} (aliases={p.get('aliases')})")

# Ejecutar intérprete
texto = "dos pizzas, una de muzza y otra napolitana"
ctx = nuevo_contexto("comercio-test", {
    "message_id": "wamid-test",
    "customer_id": "customer-test",
    "transcript": texto,
    "catalog_version": "2026-11-14T12:00:00-03:00",
    "catalog": CATALOGO,
})

ctx = run_interpretacion(ctx)

print(f"\nEstado: {ctx['estado']}")
print(f"Items: {len(ctx.get('items', []))}")
for it in ctx.get("items", []):
    print(f"  - {it['sku']}: {it['name']} qty={it['quantity']} conf={it['confidence']} match={it['match_method']} original='{it['original_text']}'")
print(f"Missing: {ctx.get('pedido', {}).get('missing_information', [])}")
print(f"No identificados: {ctx.get('productos_no_identificados', [])}")
