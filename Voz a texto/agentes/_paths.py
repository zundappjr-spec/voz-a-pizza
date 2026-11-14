"""Rutas compartidas del paquete de agentes.

Agrega al sys.path los scripts de la skill y el orquestador para que cada
agente pueda importar los contratos existentes sin modificarlos.
"""

from __future__ import annotations

import os
import sys

_BASE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(
    os.path.join(_BASE, "..", "tomando-pedidos-voz-whatsapp", "scripts")
)
_ORCH = os.path.abspath(os.path.join(_BASE, "..", "orquestador-pedidos-whatsapp"))

for _p in (_SCRIPTS, _ORCH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

__all__ = ["_BASE", "_SCRIPTS", "_ORCH"]
