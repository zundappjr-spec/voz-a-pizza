"""Pruebas de validación de estados individuales de agentes.
Valida los 4 errores corregidos:
1. agent_id como clave técnica (no nombre con/sin tilde)
2. Cálculo no bloqueado por requires_confirmation
3. order_status separado de registration_status
4. Reducción determinista desde eventos finales
"""
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
        "message_id": f"wamid-test-{nombre.replace(' ', '-').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')}",
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
    print(f"\norder_status: {ctx.get('order_status', 'N/A')}")
    print(f"registration_status: {ctx.get('registration_status', 'N/A')}")
    print(f"persistence_status: {ctx.get('persistence_status', 'N/A')}")
    print(f"\nEstados individuales de agentes (reducidos desde eventos):")

    agent_states = ctx.get("agent_states", {})
    orden = ["receptor", "transcripcion", "interpretacion", "validacion", "calculo", "confirmacion", "registro"]
    nombres = {
        "receptor": "Receptor",
        "transcripcion": "Transcripción",
        "interpretacion": "Interpretación",
        "validacion": "Validación",
        "calculo": "Cálculo",
        "confirmacion": "Confirmación",
        "registro": "Registro",
    }

    for aid in orden:
        ev = agent_states.get(aid)
        if ev:
            print(f"  [{nombres.get(aid, aid):15s}] {ev.get('status', '?'):15s} | {ev.get('result', '')}")
        else:
            print(f"  [{nombres.get(aid, aid):15s}] {'no ejecutado':15s} | —")

    return ctx, eventos_recibidos

# ============ PRUEBA 1: Pedido correcto ============
print("\n" + "="*70)
print("PRUEBA 1: Pedido correcto de pizzería (2 productos)")
print("="*70)
ctx1, ev1 = run_test(
    "Pedido correcto pizzería",
    "pizzeria-demo",
    "quiero dos pizzas una de muzza y otra napolitana para retirar",
    CATALOGO_PIZZA,
    confirmar=False,
)
print("\n" + "="*70)
print("PRUEBA 2: Pedido ambiguo (3 pizzas, 2 variantes)")
print("="*70)
ctx2, ev2 = run_test(
    "Pedido ambiguo",
    "pizzeria-demo",
    "tres pizzas una de muzza y otra napolitana",
    CATALOGO_PIZZA,
    confirmar=False,
)

# ============ PRUEBA 3: Producto inexistente ============
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

# ============ PRUEBA 4: Producto no disponible ============
print("\n" + "="*70)
print("PRUEBA 4: Producto no disponible (nafta super en supermercado)")
print("="*70)
ctx4, ev4 = run_test(
    "Producto no disponible",
    "supermercado-demo",
    "quiero 5 litros de nafta super y una mandarina",
    CATALOGO_SUPER,
    confirmar=False,
)

# ============ PRUEBA 5: Pedido con confirmacion en simulacion ============
print("\n" + "="*70)
print("PRUEBA 5: Pedido con confirmacion y registro (simulacion)")
print("="*70)
ctx5, ev5 = run_test(
    "Pedido con confirmacion",
    "pizzeria-demo",
    "una pizza de muzza para retirar",
    CATALOGO_PIZZA,
    confirmar=True,
    registrar=False,
)

print("\n" + "="*70)
print("RESUMEN DE VALIDACIONES")
print("="*70)

# Validar PRUEBA 1
estados1 = ctx1.get("agent_states", {})
print(f"\n1. Pedido correcto: order_status={ctx1.get('order_status')}")
print(f"   Calculo completado: {estados1.get('calculo', {}).get('status', '?')}")
print(f"   Confirmacion bloqueada: {estados1.get('confirmacion', {}).get('status', '?')}")
print(f"   Registro no ejecutado: {estados1.get('registro', {}).get('status', '?')}")

# Validar PRUEBA 5
estados5 = ctx5.get("agent_states", {})
print(f"\n5. Pedido con confirmacion: order_status={ctx5.get('order_status')}")
print(f"   registration_status={ctx5.get('registration_status')}")
print(f"   persistence_status={ctx5.get('persistence_status')}")
print(f"   Confirmacion completada: {estados5.get('confirmacion', {}).get('status', '?')}")
print(f"   Registro completado (simulacion): {estados5.get('registro', {}).get('status', '?')}")
