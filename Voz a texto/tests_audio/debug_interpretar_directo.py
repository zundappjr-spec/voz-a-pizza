"""Debug: llamar directamente a interpretar_pedido."""
import sys
import os
import json
import importlib.util

sys.path.insert(0, r"C:\Voz a texto\agentes")
sys.path.insert(0, r"C:\Voz a texto")

import imageio_ffmpeg as i
os.environ["PATH"] = os.path.dirname(i.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

spec_cl = importlib.util.spec_from_file_location(
    "catalogo_loader",
    r"C:\Voz a texto\orquestador-pedidos-whatsapp\config\catalogo_loader.py"
)
catalogo_loader = importlib.util.module_from_spec(spec_cl)
spec_cl.loader.exec_module(catalogo_loader)

spec_orch = importlib.util.spec_from_file_location(
    "orchestrator_module",
    r"C:\Voz a texto\orquestador-pedidos-whatsapp\orchestrator.py"
)
orch = importlib.util.module_from_spec(spec_orch)
spec_orch.loader.exec_module(orch)

datos = catalogo_loader.cargar_catalogo("supermercado-demo")
catalog = list(datos.get("productos", []))
if datos.get("producto_no_disponible"):
    catalog.append(datos["producto_no_disponible"])

texto = "Hola, ¿qué tal? Necesito comprar 17 resmas de papel, 4 latas de tomate, 5 litros de nasta super, 8 choplos, 7 mandarinas, 27 revistas del demoledor, 8 kilos de carne, de cerdo y lo de vaca."

resultado = orch.interpretar_pedido(
    transcript=texto,
    catalog=catalog,
    catalog_version="2026-11-14T12:00:00-03:00",
    customer_id="customer-test",
    message_id="wamid-test",
    comercio_id="supermercado-demo",
)

print(f"Estado: {resultado['status']}")
print(f"Items: {len(resultado['items'])}")
for it in resultado['items']:
    print(f"  - {it['sku']}: {it['name']} qty={it['quantity']}")
print(f"Missing: {resultado['missing_information']}")
print(f"No identificados: {resultado['productos_no_identificados']}")
print(f"No disponibles: {resultado['productos_no_disponibles']}")
