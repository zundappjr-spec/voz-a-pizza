"""Prueba rápida del intérprete con transcripción de supermercado."""
import sys
import os
import json

sys.path.insert(0, r"C:\Voz a texto\agentes")
sys.path.insert(0, r"C:\Voz a texto")

from contexto import nuevo_contexto
from agente_interpretacion import run as run_interpretacion

TRANSCRIPCION = (
    "Hola, ¿qué tal? Necesito comprar 17 resmas de papel, "
    "4 latas de tomate, 5 litros de nasta super, 8 choplos, "
    "7 mandarinas, 27 revistas del demoledor, "
    "8 kilos de carne, de cerdo y lo de vaca."
)

CATALOGO_EVENTO = []  # Se cargará desde archivo externo

ctx = nuevo_contexto("supermercado-demo", {
    "message_id": "wamid-super-001",
    "customer_id": "customer-super-001",
    "transcript": TRANSCRIPCION,
    "catalog_version": "2026-11-14T12:00:00-03:00",
    "catalog": CATALOGO_EVENTO,
})

ctx = run_interpretacion(ctx)

print(json.dumps(ctx, ensure_ascii=False, indent=2))
