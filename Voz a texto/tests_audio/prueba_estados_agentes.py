"""Pruebas de validación de estados individuales de agentes."""
import sys
import os
import json

sys.path.insert(0, r"C:\Voz a texto\agentes")
sys.path.insert(0, r"C:\Voz a texto")

import imageio_ffmpeg as i
os.environ["PATH"] = os.path.dirname(i.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

from contexto import nuevo_contexto
from pipeline import ejecutar

CATALOGO_PIZZA = [
    {"sku": "PIZ-G-MUZ", "name": "Pizza grande de muzzarella", "price": 14500, "currency": "ARS", "available": True, "unidad": "unidad", "aliases": ["pizza de muzzarella", "muzza"], "phonetic_aliases": []},
    {"sku": "PIZ-G-NAP", "name": "Pizza grande napolitana", "price": 16800, "currency": "ARS", "available": True, "unidad": "unidad", "aliases": ["pizza napolitana", "napolitana"], "phonetic_aliases": []},
    {"sku": "PIZ-G-CAL", "name": "Pizza grande calabresa", "price": 15200, "currency": "ARS", "available": True, "unidad": "unidad", "aliases": ["pizza calabresa", "calabresa"], "phonetic_aliases": []},
]

CATALOGO_SUPER = [
    {"sku": "SUP-RESMA-A4", "name": "Resma de papel A4", "price": 2500, "currency": "ARS", "available": True, "unidad": "resma", "aliases": ["resma papel a4"], "phonetic_aliases": []},
    {"sku": "SUP-TOMATE-LATA", "name": "Tomate triturado en lata", "price": 450, "currency": "ARS", "available": True, "unidad": "lata", "aliases": ["tomate en lata"], "phonetic_aliases": []},
    {"sku": "SUP-MANDARINA", "name": "Mandarina", "price": 120, "currency": "ARS", "available": True, "unidad": "unidad", "aliases": ["mandarina"], "phonetic_aliases": []},
    {"sku": "SUP-CARNE-VACUNA", "name": "Carne vacuna", "price": 5500, "currency": "ARS", "available": True, "unidad": "kilogramo", "aliases": ["carne de vaca"], "phonetic_aliases": []},
    {"sku": "SUP-NAFTA-SUPER", "name": "Nafta súper", "price": None, "currency": "ARS", "available": False, "unidad": "litro", "aliases": ["nafta super"], "phonetic_aliases": []},
]

eventos_recibidos = []

def capturar_evento(ev):
    eventos_recibidos.append(ev)

def run_test(nombre, comercio_id, transcript, catalogo, confirmar=False, registrar=False):
    global eventos_recibidos
    eventos_recibidos = []

    evento = {
        "message_id": f"wamid-test-{nombre.lower().replace(' ', '-')}",
        "customer_id": "customer-test",
        "transcript": transcript,
        "catalog_version": "2026-11-14T12:00:00-03:00",
        "catalog": catalogo,
    }

    ctx = ejecutar(comercio_id, evento, confirmacion=True if confirmar else None, registrar=registrar, event_callback=capturar_evento)

    print(f"\n{'='*70}")
    print(f"PRUEBA: {nombre}")
    print(f"{'='*70}")
    print(f"Transcripción: '{transcript}'")
    print(f"Estado global del pedido: {ctx.get('estado')}")
    print(f"\nEstados individuales de agentes:")

    for ev in eventos_recibidos:
        print(f"  [{ev['agent_name']:15s}] {ev['status']:15s} | {ev.get('result', '')}")

    # Verificaciones
    print(f"\nVerificaciones:")
    estados = {ev['agent_name']: ev['status'] for ev in eventos_recibidos}

    # Verificar que no todos los agentes muestran requires_clarification
    interpretacion = estados.get("Interpretación", "")
    validacion = estados.get("Validación", "")
    calculo = estados.get("Cálculo", "")
    confirmacion = estados.get("Confirmación", "")
    registro = estados.get("Registro", "")

    print(f"  Interpretación: {interpretacion}")
    print(f"  Validación: {validacion}")
    print(f"  Cálculo: {calculo}")
    print(f"  Confirmación: {confirmacion}")
    print(f"  Registro: {registro}")

    return ctx, eventos_recibidos

# Prueba 1: Pedido correcto de pizzería
print("\n" + "="*70)
print("PRUEBA 1: Pedido correcto de pizzería")
print("="*70)
ctx1, ev1 = run_test(
    "Pedido correcto pizzería",
    "pizzeria-demo",
    "quiero dos pizzas una de muzza y otra napolitana para retirar",
    CATALOGO_PIZZA,
    confirmar=False,
)

# Prueba 2: Pedido ambiguo (tres pizzas, dos variantes)
print("\n" + "="*70)
print("PRUEBA 2: Pedido ambiguo")
print("="*70)
ctx2, ev2 = run_test(
    "Pedido ambiguo",
    "pizzeria-demo",
    "tres pizzas una de muzza y otra napolitana",
    CATALOGO_PIZZA,
    confirmar=False,
)

# Prueba 3: Producto inexistente
print("\n" + "="*70)
print("PRUEBA 3: Producto inexistente")
print("="*70)
ctx3, ev3 = run_test(
    "Producto inexistente",
    "pizzeria-demo",
    "quiero una pizza cuatro estaciones",
    CATALOGO_PIZZA,
    confirmar=False,
)

# Prueba 4: Producto no disponible (nafta súper en supermercado)
print("\n" + "="*70)
print("PRUEBA 4: Producto no disponible")
print("="*70)
ctx4, ev4 = run_test(
    "Producto no disponible",
    "supermercado-demo",
    "quiero 5 litros de nafta super y una mandarina",
    CATALOGO_SUPER,
    confirmar=False,
)

# Prueba 5: Pedido con confirmación y registro
print("\n" + "="*70)
print("PRUEBA 5: Pedido con confirmación y registro (simulación)")
print("="*70)
ctx5, ev5 = run_test(
    "Pedido con confirmación",
    "pizzeria-demo",
    "una pizza de muzza para retirar",
    CATALOGO_PIZZA,
    confirmar=True,
    registrar=False,
)

print("\n" + "="*70)
print("TODAS LAS PRUEBAS COMPLETADAS")
print("="*70)
