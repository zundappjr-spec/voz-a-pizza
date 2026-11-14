"""Debug: ver fragmentos generados por _extraer_fragmentos_producto."""
import sys
import os
import json
import importlib.util

sys.path.insert(0, r"C:\Voz a texto\agentes")
sys.path.insert(0, r"C:\Voz a texto")

import imageio_ffmpeg as i
os.environ["PATH"] = os.path.dirname(i.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

# Cargar catalogo_loader
spec_cl = importlib.util.spec_from_file_location(
    "catalogo_loader",
    r"C:\Voz a texto\orquestador-pedidos-whatsapp\config\catalogo_loader.py"
)
catalogo_loader = importlib.util.module_from_spec(spec_cl)
spec_cl.loader.exec_module(catalogo_loader)

# Cargar orchestrator
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

fragmentos = orch._extraer_fragmentos_producto(texto, catalog)
print(f"Fragmentos generados: {len(fragmentos)}")
for f in fragmentos:
    print(f"  - cantidad={f['cantidad']}, unidad={f['unidad']}, texto_producto='{f['texto_producto']}'")
