"""Prueba directa de _buscar_producto_en_texto y interpretar_pedido."""
import sys
import os
import json

sys.path.insert(0, r"C:\Voz a texto\agentes")
sys.path.insert(0, r"C:\Voz a texto")
sys.path.insert(0, r"C:\Voz a texto\orquestador-pedidos-whatsapp")
sys.path.insert(0, r"C:\Voz a texto\orquestador-pedidos-whatsapp\config")

import imageio_ffmpeg as _iio
os.environ["PATH"] = os.path.dirname(_iio.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

# Import modules directly
import importlib.util

# Load catalogo_loader
spec = importlib.util.spec_from_file_location(
    "catalogo_loader",
    r"C:\Voz a texto\orquestador-pedidos-whatsapp\config\catalogo_loader.py"
)
catalogo_loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalogo_loader)

# Load orchestrator modules
from contexto import nuevo_contexto
from agente_interpretacion import run as run_interpretacion

# Cargar catálogo directamente
CATALOGO_PATH = r"C:\Voz a texto\orquestador-pedidos-whatsapp\config\comercios\supermercado-demo.json"
with open(CATALOGO_PATH, "r", encoding="utf-8") as f:
    datos = json.load(f)
catalog = list(datos.get("productos", []))
if datos.get("producto_no_disponible"):
    catalog.append(datos["producto_no_disponible"])

print(f"Catalog size: {len(catalog)}")

# Test the agente_interpretacion directly
TRANSCRIPCION = (
    "Hola, ¿qué tal? Necesito comprar 17 resmas de papel, "
    "4 latas de tomate, 5 litros de nasta super, 8 choplos, "
    "7 mandarinas, 27 revistas del demoledor, "
    "8 kilos de carne, de cerdo y lo de vaca."
)

ctx = nuevo_contexto("supermercado-demo", {
    "message_id": "wamid-super-001",
    "customer_id": "customer-super-001",
    "transcript": TRANSCRIPCION,
    "catalog_version": "2026-11-14T12:00:00-03:00",
    "catalog": [],
})

ctx = run_interpretacion(ctx)

pedido = ctx.get("pedido", {})
print(f"\nEstado: {ctx['estado']}")
print(f"Items: {len(pedido.get('items', []))}")
for it in pedido.get("items", []):
    print(f"  - {it['sku']}: {it['name']} qty={it['quantity']} unit={it.get('unidad')} price=${it['unit_price']} conf={it['confidence']} match={it['match_method']} original='{it['original_text']}'")
print(f"Fulfillment: {pedido.get('fulfillment', {})}")
print(f"Missing: {pedido.get('missing_information', [])}")
print(f"No identificados: {pedido.get('productos_no_identificados', [])}")
print(f"No disponibles: {pedido.get('productos_no_disponibles', [])}")
print(f"Subtotal: {pedido.get('subtotal', '-')}")
