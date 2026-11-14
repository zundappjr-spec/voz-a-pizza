"""Debug detallado de supermercado."""
import sys
import os
import json

sys.path.insert(0, r"C:\Voz a texto\agentes")
sys.path.insert(0, r"C:\Voz a texto")

import imageio_ffmpeg as i
os.environ["PATH"] = os.path.dirname(i.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

from contexto import nuevo_contexto
from agente_interpretacion import run as run_interpretacion, _cargar_catalogo_comercio

TRANSCRIPCION = (
    "Hola, ¿qué tal? Necesito comprar 17 resmas de papel, "
    "4 latas de tomate, 5 litros de nasta super, 8 choplos, "
    "7 mandarinas, 27 revistas del demoledor, "
    "8 kilos de carne, de cerdo y lo de vaca."
)

ctx = nuevo_contexto("supermercado-demo", {
    "message_id": "wamid-test",
    "customer_id": "customer-test",
    "transcript": TRANSCRIPCION,
    "catalog_version": "2026-11-14T12:00:00-03:00",
    "catalog": [],
})

ctx = run_interpretacion(ctx)

pedido = ctx.get("pedido", {})
print(f"Estado: {ctx['estado']}")
print(f"Items: {len(pedido.get('items', []))}")
for it in pedido.get("items", []):
    print(f"  - {it['sku']}: {it['name']} qty={it['quantity']} conf={it['confidence']} match={it['match_method']} original='{it['original_text']}'")
print(f"Missing: {pedido.get('missing_information', [])}")
print(f"No identificados: {ctx.get('productos_no_identificados', [])}")
print(f"No disponibles: {ctx.get('productos_no_disponibles', [])}")
print(f"Subtotal: {pedido.get('subtotal', '-')}")
