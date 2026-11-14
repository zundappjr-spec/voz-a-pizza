import json
import sys
import os

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

CASOS = [
    ("1. dos pizzas, una de muzza y otra napolitana",
     "dos pizzas, una de muzza y otra napolitana",
     {"esperado_estado": "requires_confirmation", "esperado_items": 2, "esperado_total": "31300.00", "esperado_fulfillment": None}),
    ("2. dos pisas, una de musa y otra napolitana",
     "dos pisas, una de musa y otra napolitana",
     {"esperado_estado": "requires_confirmation", "esperado_items": 2, "esperado_total": "31300.00", "esperado_fulfillment": None}),
    ("3. tres pizzas, una de muzza y otra napolitana",
     "tres pizzas, una de muzza y otra napolitana",
     {"esperado_estado": "requires_clarification", "esperado_items": 2, "esperado_total": "31300.00", "esperado_fulfillment": None}),
    ("4. una docena de empanadas de carne",
     "una docena de empanadas de carne",
     {"esperado_estado": "requires_clarification", "esperado_items": 0, "esperado_total": "0.00", "esperado_fulfillment": None}),
    ("5. dos empanadas, sin indicar gusto",
     "dos empanadas, sin indicar gusto",
     {"esperado_estado": "requires_clarification", "esperado_items": 0, "esperado_total": "0.00", "esperado_fulfillment": None}),
    ("6. pizza de musa, con una unica coincidencia de catalogo",
     "pizza de musa",
     {"esperado_estado": "requires_confirmation", "esperado_items": 1, "esperado_total": "14500.00", "esperado_fulfillment": None}),
    ("7. palabra aproximada compatible con dos productos",
     "pizza",
     {"esperado_estado": "requires_clarification", "esperado_items": 0, "esperado_total": "0.00", "esperado_fulfillment": None}),
    ("8. paso a retirar",
     "paso a retirar",
     {"esperado_estado": "requires_clarification", "esperado_items": 0, "esperado_total": "0.00", "esperado_fulfillment": "pickup"}),
    ("9. mandamelo a domicilio",
     "mandamelo a domicilio",
     {"esperado_estado": "requires_clarification", "esperado_items": 0, "esperado_total": "0.00", "esperado_fulfillment": "delivery"}),
    ("10. pedido parcialmente interpretado",
     "una pizza de muzza",
     {"esperado_estado": "requires_confirmation", "esperado_items": 1, "esperado_total": "14500.00", "esperado_fulfillment": None}),
    ("11. producto inexistente",
     "una pizza cuatro estaciones",
     {"esperado_estado": "requires_clarification", "esperado_items": 0, "esperado_total": "0.00", "esperado_fulfillment": None}),
    ("12. palabras ajenas al pedido",
     "hola como estas que tal el clima hoy",
     {"esperado_estado": "requires_clarification", "esperado_items": 0, "esperado_total": "0.00", "esperado_fulfillment": None}),
]


def ejecutar_caso(texto, esperado):
    evento = {
        "message_id": "wamid-test",
        "customer_id": "customer-test",
        "transcript": texto,
        "catalog_version": "2026-11-14T12:00:00-03:00",
        "catalog": CATALOGO,
    }
    ctx = nuevo_contexto("comercio-test", evento)
    ctx = run_interpretacion(ctx)
    ctx = run_validacion(ctx)
    ctx = run_calculo(ctx)
    ctx = run_confirmacion(ctx, numero_cliente=None, confirmacion=None)

    estado = ctx["estado"]
    pedido = ctx.get("pedido", {})
    items = pedido.get("items", [])
    total = pedido.get("total", "0.00")
    fulfillment = pedido.get("fulfillment", {}) or {}
    tipo_fulfillment = fulfillment.get("type")

    ok = True
    detalle = []

    if estado != esperado["esperado_estado"]:
        ok = False
        detalle.append(f"estado: esperado {esperado['esperado_estado']}, obtuvo {estado}")
    if len(items) != esperado["esperado_items"]:
        ok = False
        detalle.append(f"items: esperado {esperado['esperado_items']}, obtuvo {len(items)}")
    if total != esperado["esperado_total"]:
        ok = False
        detalle.append(f"total: esperado {esperado['esperado_total']}, obtuvo {total}")
    if tipo_fulfillment != esperado["esperado_fulfillment"]:
        ok = False
        detalle.append(f"fulfillment.type: esperado {esperado['esperado_fulfillment']}, obtuvo {tipo_fulfillment}")

    return ok, detalle, {
        "texto": texto,
        "estado": estado,
        "items": len(items),
        "total": total,
        "fulfillment_type": tipo_fulfillment,
        "missing_information": pedido.get("missing_information", []),
    }


resultados = []
todos_ok = True
for nombre, texto, esperado in CASOS:
    ok, detalle, res = ejecutar_caso(texto, esperado)
    resultados.append(res)
    if not ok:
        todos_ok = False
        print(f"FALLO: {nombre}")
        for d in detalle:
            print(f"  - {d}")
    else:
        print(f"OK: {nombre}")

print("\n" + "=" * 60)
print(f"Resultado: {sum(1 for r in resultados if r['estado']==r.get('estado',''))} casos ejecutados")
print(f"Todos pasaron: {todos_ok}")
with open(r"C:\Voz a texto\tests_audio\resultados_pruebas.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)

sys.exit(0 if todos_ok else 1)
