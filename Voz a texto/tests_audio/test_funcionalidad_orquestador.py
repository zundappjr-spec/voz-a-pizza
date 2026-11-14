"""Test de funcionalidad del orquestador y agentes de pedidos de voz.
Ejecuta pruebas end-to-end para verificar el registro correcto de pedidos.
"""
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

# Cargar catálogos
sys.path.insert(0, r"C:\Voz a texto\orquestador-pedidos-whatsapp\config")
from catalogo_loader import cargar_catalogo  # noqa: E402

RESULTADOS = []


def ejecutar_prueba(nombre, comercio_id, evento_path, numero_cliente=None, confirmar=False, registrar=False):
    print(f"\n{'='*70}")
    print(f"PRUEBA: {nombre}")
    print(f"{'='*70}")

    with open(evento_path, "r", encoding="utf-8") as f:
        evento = json.load(f)

    trace_id_val = str(uuid.uuid4())[:8]
    print(f"Trace ID: {trace_id_val}")
    print(f"Comercio: {comercio_id}")
    print(f"Message ID: {evento.get('message_id')}")
    print(f"Transcripcion: '{evento.get('transcript', '')[:100]}...'")

    ctx = ejecutar(
        comercio_id,
        evento,
        numero_cliente=numero_cliente,
        confirmacion=True if confirmar else None,
        registrar=registrar,
    )

    print(f"\nResultado:")
    print(f"  Estado final: {ctx['estado']}")
    print(f"  Trace ID: {trace_id(ctx)}")
    print(f"  Errores: {ctx.get('errores', []) or 'Ninguno'}")
    print(f"  Simulacion: {ctx.get('simulacion', True)}")

    pedido = ctx.get("pedido", {})
    items = pedido.get("items", [])
    print(f"  Items identificados: {len(items)}")
    for it in items:
        print(f"    - {it.get('quantity')}x {it.get('name', it.get('sku'))} = ${it.get('unit_price')} (conf {it.get('confidence')}, match={it.get('match_method')})")

    no_id = pedido.get("productos_no_identificados", [])
    if no_id:
        print(f"  Productos no identificados: {len(no_id)}")
        for ni in no_id:
            print(f"    - '{ni['texto_original']}' qty={ni.get('cantidad')}")

    no_disp = pedido.get("productos_no_disponibles", [])
    if no_disp:
        print(f"  Productos no disponibles: {len(no_disp)}")
        for nd in no_disp:
            print(f"    - {nd['nombre']} (SKU: {nd['sku']}) qty={nd.get('cantidad')}")

    registro = ctx.get("registro", {})
    if registro:
        print(f"  Registro: estado={registro.get('estado')}, clave_pedido={registro.get('clave_pedido')}")

    print(f"  Subtotal: {ctx.get('subtotal', '-')} {ctx.get('currency', '')}")
    print(f"  Total: {ctx.get('total', '-')} {ctx.get('currency', '')}")
    print(f"  Fulfillment: {pedido.get('fulfillment', {}).get('type') or 'no definida'}")

    resultado = {
        "prueba": nombre,
        "comercio": comercio_id,
        "trace_id": trace_id_val,
        "estado_final": ctx["estado"],
        "errores": ctx.get("errores", []),
        "items": len(items),
        "subtotal": ctx.get("subtotal", ""),
        "total": ctx.get("total", ""),
        "registro_estado": registro.get("estado", "no ejecutado"),
        "clave_pedido": registro.get("clave_pedido", "N/A"),
        "simulacion": ctx.get("simulacion", True),
    }
    RESULTADOS.append(resultado)

    print(f"\nResultado de prueba: {'EXITOSA' if not hay_errores(ctx) else 'CON ERRORES'}")
    return ctx


print("=" * 70)
print("TEST DE FUNCIONALIDAD - ORQUESTADOR Y AGENTES")
print("=" * 70)

# Cargar catálogos para verificar disponibilidad
print("\nCatálogos cargados:")
for comercio in ["supermercado-demo", "pizzeria-demo"]:
    try:
        datos = cargar_catalogo(comercio)
        productos = list(datos.get("productos", []))
        no_disp = datos.get("producto_no_disponible")
        print(f"  {comercio}: {len(productos)} productos")
        if no_disp:
            print(f"    Producto no disponible: {no_disp['name']} (SKU: {no_disp['sku']})")
    except Exception as e:
        print(f"  {comercio}: ERROR - {e}")

# Prueba A: Supermercado
ctx_a = ejecutar_prueba(
    "Supermercado - transcripción real",
    "supermercado-demo",
    r"C:\Voz a texto\tests_audio\evento_supermercado.json",
    confirmar=False,
    registrar=False,
)

# Prueba B: Pizzería
ctx_b = ejecutar_prueba(
    "Pizzería - dos pizzas para retirar",
    "pizzeria-demo",
    r"C:\Voz a texto\tests_audio\evento_pizzeria.json",
    confirmar=False,
    registrar=False,
)

# Prueba C: Pizzería con confirmación y registro
ctx_c = ejecutar_prueba(
    "Pizzería - confirmar y registrar (simulación)",
    "pizzeria-demo",
    r"C:\Voz a texto\tests_audio\evento_pizzeria.json",
    confirmar=True,
    registrar=True,
)

# Prueba D: Idempotencia (mismo evento dos veces)
print(f"\n{'='*70}")
print("PRUEBA: Idempotencia - mismo webhook dos veces")
print(f"{'='*70}")
ctx_d1 = ejecutar_prueba(
    "Idempotencia - primera ejecución",
    "pizzeria-demo",
    r"C:\Voz a texto\tests_audio\evento_pizzeria.json",
    confirmar=False,
    registrar=False,
)
ctx_d2 = ejecutar_prueba(
    "Idempotencia - segunda ejecución (duplicado)",
    "pizzeria-demo",
    r"C:\Voz a texto\tests_audio\evento_pizzeria.json",
    confirmar=False,
    registrar=False,
)

# Resumen final
print(f"\n{'='*70}")
print("RESUMEN DE PRUEBAS")
print(f"{'='*70}")
for r in RESULTADOS:
    print(f"  [{r['prueba'][:40]:40s}] estado={r['estado_final']:25s} items={r['items']} registro={r['registro_estado']}")

print(f"\nTotal pruebas ejecutadas: {len(RESULTADOS)}")
print("Test de funcionalidad completado.")

# Guardar resultados
resultados_path = r"C:\Voz a texto\tests_audio\resultados_test_funcionalidad.json"
with open(resultados_path, "w", encoding="utf-8") as f:
    json.dump(RESULTADOS, f, ensure_ascii=False, indent=2)
print(f"Resultados guardados en: {resultados_path}")
