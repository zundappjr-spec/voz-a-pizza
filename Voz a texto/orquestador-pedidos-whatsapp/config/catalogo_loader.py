"""Cargador de catálogos por comercio.

Lee archivos JSON externos con la configuración de productos, aliases y
unidades de medida de cada comercio. No hardcodea productos ni precios.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

CATALOGOS_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "comercios"
    )
)

_UNIDADES_VALIDAS = {
    "unidad": "unidad",
    "unidades": "unidad",
    "kg": "kilogramo",
    "kilos": "kilogramo",
    "kilogramo": "kilogramo",
    "kilogramos": "kilogramo",
    "lt": "litro",
    "litros": "litro",
    "litro": "litro",
    "paquete": "paquete",
    "paquetes": "paquete",
    "lata": "lata",
    "latas": "lata",
    "resma": "resma",
    "resmas": "resma",
}


def cargar_catalogo(comercio_id: str) -> Dict[str, Any]:
    """Carga el catálogo de un comercio desde su archivo JSON externo."""
    ruta = os.path.join(CATALOGOS_DIR, f"{comercio_id}.json")
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No existe catálogo para el comercio: {comercio_id}")

    with open(ruta, "r", encoding="utf-8") as f:
        datos = json.load(f)

    return datos


def listar_comercios_disponibles() -> list[str]:
    """Retorna los IDs de comercio con catálogo disponible."""
    if not os.path.isdir(CATALOGOS_DIR):
        return []
    return sorted(
        f.replace(".json", "")
        for f in os.listdir(CATALOGOS_DIR)
        if f.endswith(".json")
    )


def normalizar_unidad(texto: str) -> str | None:
    """Normaliza una expresión de unidad de medida."""
    t = texto.strip().lower()
    return _UNIDADES_VALIDAS.get(t)


def productos_por_sku(catalogo: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Indexa productos por SKU para búsquedas rápidas."""
    return {p["sku"]: p for p in catalogo.get("productos", [])}


def producto_no_disponible(catalogo: Dict[str, Any]) -> Dict[str, Any] | None:
    """Retorna el producto marcado como no disponible (ej. nafta súper en supermercado)."""
    return catalogo.get("producto_no_disponible")


def extraer_cantidad_y_unidad(fragmento: str) -> tuple[int | None, str | None, str]:
    """Extrae cantidad, unidad y texto restante de un fragmento.

    Retorna: (cantidad, unidad_normalizada, texto_producto)
    """
    import re

    texto = fragmento.strip().lower()

    # Patrón: número o palabra de cantidad + unidad opcional + producto
    # Ejemplos: "17 resmas", "4 latas", "5 litros", "8 kilos", "7 mandarinas"
    patron = r"^(\d+|un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|dieciseis|diecisiete|dieciocho|diecinueve|veinte|media docena|docena)\s+(de\s+)?(.+)$"
    m = re.match(patron, texto)
    if not m:
        return None, None, texto

    cantidad_raw = m.group(1)
    resto = m.group(3).strip()

    cantidad_map = {
        "un": 1, "uno": 1, "una": 1,
        "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
        "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
        "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
        "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
        "media docena": 6, "docena": 12,
    }
    cantidad = cantidad_map.get(cantidad_raw)
    if cantidad is None and cantidad_raw.isdigit():
        cantidad = int(cantidad_raw)

    # Intentar detectar unidad al inicio del resto
    unidades_lista = sorted(_UNIDADES_VALIDAS.keys(), key=len, reverse=True)
    unidad_detectada = None
    texto_producto = resto
    for u in unidades_lista:
        if resto.startswith(u + " ") or resto == u:
            unidad_detectada = _UNIDADES_VALIDAS[u]
            texto_producto = resto[len(u):].strip()
            if texto_producto.startswith("de "):
                texto_producto = texto_producto[3:].strip()
            break

    return cantidad, unidad_detectada, texto_producto
