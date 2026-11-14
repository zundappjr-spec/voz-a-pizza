"""Orquestador de pedidos de voz por WhatsApp.

Coordina el flujo de extremo a extremo:
webhook -> descarga audio -> transcripcion -> interpretacion (skill)
-> validacion -> calculo total -> confirmacion cliente -> registro.

Disenado para operar sin dependencias externas obligatorias (solo stdlib).
Los puntos de integracion con WhatsApp, transcripcion, catalogo y backend
están marcados como componentes autorizados y operan en simulacion
salvo que se configure REGISTRAR_PEDIDOS=1.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import sys
import unicodedata
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

# --- Importar los scripts de la skill ---------------------------------------
SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..", "tomando-pedidos-voz-whatsapp", "scripts")
SCRIPT_DIR = os.path.abspath(SCRIPT_DIR)
if os.path.isdir(SCRIPT_DIR):
    sys.path.insert(0, SCRIPT_DIR)

try:
    from validar_evento import validate_event, compute_idempotency_key  # type: ignore
    from validar_pedido import validate_pedido  # type: ignore
    from calcular_total import calcular_total  # type: ignore
    from anonimizar import anonimizar_para_log  # type: ignore
    from registrar_pedido import registrar_pedido, SIMULATION_MODE  # type: ignore
except Exception:  # pragma: no cover - permite ejecutar sin la skill instalada
    validate_event = None  # type: ignore
    validate_pedido = None  # type: ignore
    calcular_total = None  # type: ignore
    anonimizar_para_log = None  # type: ignore
    registrar_pedido = None  # type: ignore
    SIMULATION_MODE = True

# --- Cargador de catálogos externos -------------------------------------------
CATALOGO_LOADER_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "config")
)
if CATALOGO_LOADER_DIR not in sys.path:
    sys.path.insert(0, CATALOGO_LOADER_DIR)

try:
    from catalogo_loader import (  # type: ignore
        cargar_catalogo,
        productos_por_sku,
        producto_no_disponible,
        extraer_cantidad_y_unidad,
        normalizar_unidad,
    )
except Exception:  # pragma: no cover
    cargar_catalogo = None  # type: ignore
    productos_por_sku = None  # type: ignore
    producto_no_disponible = None  # type: ignore
    extraer_cantidad_y_unidad = None  # type: ignore
    normalizar_unidad = None  # type: ignore

# Estados permitidos
STATES = [
    "received",
    "transcribed",
    "interpreted",
    "requires_clarification",
    "requires_confirmation",
    "confirmed",
    "registered",
]
ALTERNATE_STATES = {"cancelled", "rejected", "expired", "manual_review"}


class OrquestadorError(RuntimeError):
    """Error del orquestador."""


def ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clave_idempotencia(commerce_id: str, message_id: str, operation: str, catalog_version: str) -> str:
    raw = f"{commerce_id}|{message_id}|{operation}|{catalog_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# --- Componentes autorizados (simulacion por defecto) -----------------------

def descargar_audio(mensaje_id: str, audio_url: Optional[str]) -> str:
    """Descarga el audio de WhatsApp y retorna una ruta temporal.

    En simulacion retorna un identificador de audio temporal sin red real.
    """
    if not audio_url:
        raise OrquestadorError("No se provino URL de audio para descargar")
    audio_id = hashlib.sha256(f"{mensaje_id}|{audio_url}".encode()).hexdigest()[:16]
    ruta = f"/tmp/audio_{audio_id}.tmp"
    # Componente autorizado: WhatsApp Business Platform (download media).
    # Aquí se integraría la llamada real con timeout 10s.
    return ruta


def transcribir_audio(ruta_audio: str, idioma: str = "es-ES") -> str:
    """Transcribe el audio y retorna el texto.

    En simulacion retorna un texto de prueba. Reemplazar por llamada real
    a Azure AI Speech o Whisper con timeout 10s.
    """
    return "Mandame dos pizzas grandes, una de muzza y otra napolitana"


def consultar_catalogo(commerce_id: str, catalog_version: str) -> list[dict[str, Any]]:
    """Consulta el catalogo del comercio. En simulacion retorna catalogo vacio."""
    # Componente autorizado: API del catalogo (GET, timeout 10s).
    return []


def enviar_mensaje_whatsapp(numero: str, texto: str) -> Dict[str, Any]:
    """Envía un mensaje por WhatsApp al cliente. Componente autorizado."""
    return {"enviado": True, "mensaje": texto, "numero": anonimizar_telefono(numero)}


def anonimizar_telefono(numero: str) -> str:
    return f"[telefono:{numero[-4:]}]" if numero and len(numero) >= 4 else "[telefono]"


# --- Interpretacion con la skill -------------------------------------------

# Umbrales de confianza configurables
THRESHOLD_CONFIRM = 0.90
THRESHOLD_SPECIFIC = 0.75
THRESHOLD_CLARIFY = 0.75

# Numeros escritos en espanol
NUMBERS_ES = {
    "un": 1, "uno": 1, "una": 1,
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
    "veintiuno": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "treinta": 30,
    "media docena": 6, "docena": 12,
}

EXPRESIONES_PICKUP = ["retirar", "retiro", "paso a buscar", "busco en el local", "para llevar"]
EXPRESIONES_DELIVERY = ["envio", "envío", "delivery", "mandamelo", "mandámelo", "enviar a domicilio", "traer a casa"]


def _quitar_tildes(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def normalizar_texto(texto: str) -> str:
    """Version normalizada unicamente para analisis. No modifica el original."""
    t = texto.lower()
    t = _quitar_tildes(t)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _numero_a_entero(valor: Any) -> Optional[int]:
    if isinstance(valor, int) and not isinstance(valor, bool):
        return valor
    s = str(valor).strip().lower()
    if s.isdigit():
        return int(s)
    return NUMBERS_ES.get(s)


def _extraer_cantidad_total(texto_norm: str) -> Optional[int]:
    """Extrae la primera cantidad numérica o escrita del texto."""
    m = re.search(r"\b(\d+)\b", texto_norm)
    if m:
        return int(m.group(1))
    for palabra, valor in sorted(NUMBERS_ES.items(), key=lambda x: -len(x[0])):
        if re.search(r"\b" + re.escape(palabra) + r"\b", texto_norm):
            return valor
    return None


def _detectar_modalidad(texto_norm: str) -> Optional[str]:
    for expr in EXPRESIONES_PICKUP:
        if re.search(r"\b" + re.escape(expr) + r"\b", texto_norm):
            return "pickup"
    for expr in EXPRESIONES_DELIVERY:
        if re.search(r"\b" + re.escape(expr) + r"\b", texto_norm):
            return "delivery"
    return None


def _tokens_busqueda_producto(producto: Dict[str, Any]) -> List[str]:
    """Tokens de búsqueda para un producto: nombre + aliases + phonetic_aliases."""
    tokens: set[str] = set()
    nombre = str(producto.get("name", "")).lower()
    for tok in normalizar_texto(nombre).split():
        if len(tok) >= 3:
            tokens.add(tok)
    for frase in list(producto.get("aliases") or []) + list(producto.get("phonetic_aliases") or []):
        for tok in normalizar_texto(str(frase)).split():
            if len(tok) >= 3:
                tokens.add(tok)
    return sorted(tokens, key=len, reverse=True)


def _buscar_producto_en_texto(
    texto_norm: str,
    producto: Dict[str, Any],
) -> Optional[Tuple[float, str, str, str]]:
    """Busca coincidencia del producto en el texto normalizado.

    Retorna (confianza, frase_original, metodo, texto_coincidente) o None.
    """
    nombre = str(producto.get("name", "")).lower()
    frases: List[str] = [nombre]
    frases.extend([str(a).lower() for a in list(producto.get("aliases") or [])])
    frases.extend([str(p).lower() for p in list(producto.get("phonetic_aliases") or [])])

    mejor: Optional[Tuple[float, str, str, str]] = None
    texto_tokens = set(texto_norm.split())

    for frase in frases:
        frase_norm = normalizar_texto(frase)
        if not frase_norm:
            continue

        # 1. Coincidencia exacta de subcadena
        # 1. Coincidencia bidireccional de subcadena (como palabras completas)
        #    El texto del usuario puede estar dentro del nombre del catálogo
        #    (ej. "tomate" en "tomate triturado en lata") o viceversa
        #    (ej. "napolitana" en "una pizza napolitana").
        texto_in_frase = texto_norm in frase_norm
        frase_in_texto = frase_norm in texto_norm
        # Para frase_in_texto, exigir que frase_norm sea una palabra completa
        # en texto_norm (no solo substring, ej. evitar que "te" matchee "tomate")
        frase_palabra_completa = False
        if frase_in_texto and len(frase_norm) >= 3:
            frase_palabra_completa = (
                texto_norm == frase_norm
                or texto_norm.startswith(frase_norm + " ")
                or texto_norm.endswith(" " + frase_norm)
                or (" " + frase_norm + " ") in texto_norm
            )

        if texto_in_frase or frase_palabra_completa:
            conf = 0.98
            if mejor is None or conf > mejor[0]:
                mejor = (conf, frase, "exacto", frase_norm)
            continue

        # 2. Difflib entre texto completo y frase
        ratio = difflib.SequenceMatcher(None, texto_norm, frase_norm).ratio()
        if ratio > 0.80:
            conf = round(ratio, 2)
            if mejor is None or conf > mejor[0]:
                mejor = (conf, frase, "difflib_texto", frase_norm)

        # 3. Difflib token a token
        for tok in texto_norm.split():
            ratio_tok = difflib.SequenceMatcher(None, tok, frase_norm).ratio()
            if ratio_tok > 0.85:
                conf = round(ratio_tok * 0.95, 2)
                if mejor is None or conf > mejor[0]:
                    mejor = (conf, frase, "difflib_token", tok)

        # 4. Matching por tokens del nombre del producto presentes en el texto
        # (permite reconocer "papel" contra "Resma de papel A4")
        frase_tokens = set(frase_norm.split())
        tokens_significativos = {t for t in frase_tokens if len(t) >= 3}
        if tokens_significativos:
            tokens_encontrados = tokens_significativos & texto_tokens
            if tokens_encontrados:
                proporcion = len(tokens_encontrados) / len(tokens_significativos)
                # Confianza basada en proporcion de tokens encontrados,
                # con un tope para no superar coincidencias exactas
                conf = round(0.70 + (proporcion * 0.25), 2)
                if mejor is None or conf > mejor[0]:
                    mejor = (conf, frase, "token_match", frase_norm)

    return mejor


def _extraer_fragmentos_producto(
    texto_original: str,
    catalog: list[dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Extrae fragmentos del tipo: cantidad + unidad + producto.

    Divide el texto original por comas y punto y coma para separar items
    individuales, luego normaliza cada parte. Busca patrones como:
    "17 resmas", "4 latas de tomate", "8 kilos de carne".
    También divide fragmentos que contienen "y" conectando dos productos
    (ej. "una de X y otra de Y") cuando ambos lados matchean con productos
    diferentes del catálogo.
    Retorna lista de {cantidad, unidad, texto_producto, fragmento_original}.
    """
    import catalogo_loader  # type: ignore

    fragmentos: List[Dict[str, Any]] = []

    # Dividir por comas y punto y coma ANTES de normalizar
    partes = re.split(r"[,;]", texto_original)

    patron = re.compile(
        r"\b(\d+|un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|dieciseis|diecisiete|dieciocho|diecinueve|veinte|veintiuno|veintidos|veintitres|veinticuatro|veinticinco|veintiseis|veintisiete|veintiocho|veintinueve|treinta|media docena|docena)\s+(?:de\s+)?(.+)"
    )

    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue

        # Normalizar solo esta parte
        parte_norm = normalizar_texto(parte)

        m = patron.search(parte_norm)
        if not m:
            continue

        cantidad_raw = m.group(1)
        resto = m.group(2).strip()
        cantidad = _numero_a_entero(cantidad_raw)

        # Detectar unidad al inicio del resto
        unidad = None
        texto_producto = resto
        if catalogo_loader and normalizar_unidad:
            unidades_lista = sorted(
                ["unidad", "unidades", "kg", "kilos", "kilogramo", "kilogramos",
                 "lt", "litros", "litro", "paquete", "paquetes", "lata", "latas",
                 "resma", "resmas"],
                key=len, reverse=True,
            )
            for u in unidades_lista:
                un = normalizar_unidad(u)
                if un and (resto.startswith(u + " ") or resto == u):
                    unidad = un
                    texto_producto = resto[len(u):].strip()
                    if texto_producto.startswith("de "):
                        texto_producto = texto_producto[3:].strip()
                    break

        fragmentos.append({
            "cantidad": cantidad,
            "unidad": unidad,
            "texto_producto": texto_producto,
            "fragmento_original": parte,
        })

    # --- Post-procesamiento: dividir fragmentos con "y" entre dos productos --
    if catalog:
        fragmentos_divididos: List[Dict[str, Any]] = []
        for frag in fragmentos:
            texto_p = frag["texto_producto"]
            if " y " in texto_p or " e " in texto_p:
                separador = " y " if " y " in texto_p else " e "
                partes_texto = texto_p.split(separador, 1)
                if len(partes_texto) == 2:
                    texto_izq = partes_texto[0].strip()
                    texto_der = partes_texto[1].strip()
                    # Quitar artículos iniciales de la parte derecha
                    for art in ("otra ", "otro ", "una ", "un "):
                        if texto_der.startswith(art):
                            texto_der = texto_der[len(art):].strip()
                            break
                    # Verificar que ambos lados matcheen con productos diferentes
                    match_izq = _buscar_producto_en_catalogo(texto_izq, catalog)
                    match_der = _buscar_producto_en_catalogo(texto_der, catalog)
                    if (match_izq and match_der
                            and match_izq[0].get("sku") != match_der[0].get("sku")):
                        # Crear dos fragmentos separados
                        frag_izq = dict(frag)
                        frag_izq["texto_producto"] = texto_izq
                        frag_izq["fragmento_original"] = frag["fragmento_original"]
                        frag_der = dict(frag)
                        frag_der["texto_producto"] = texto_der
                        frag_der["fragmento_original"] = frag["fragmento_original"]
                        # Asignar cantidades: si la original es 1, cada uno es 1.
                        # Si es mayor, cada uno toma 1 (se aclarará después si es necesario).
                        frag_izq["cantidad"] = (
                            frag["cantidad"] if frag["cantidad"] and frag["cantidad"] > 1 else 1
                        )
                        frag_der["cantidad"] = 1
                        fragmentos_divididos.append(frag_izq)
                        fragmentos_divididos.append(frag_der)
                        continue
            fragmentos_divididos.append(frag)
        fragmentos = fragmentos_divididos

    return fragmentos


def _buscar_producto_en_catalogo(
    texto: str,
    catalog: list[dict[str, Any]],
) -> Optional[Tuple[Dict[str, Any], float]]:
    """Busca el mejor producto en el catálogo para un texto dado.

    Retorna (producto, confianza) o None si no hay coincidencia clara.
    """
    texto_norm = normalizar_texto(texto)
    if not texto_norm:
        return None

    mejor: Optional[Tuple[Dict[str, Any], float]] = None
    for producto in catalog:
        match = _buscar_producto_en_texto(texto_norm, producto)
        if not match:
            continue
        confianza, _, _, _ = match
        if mejor is None or confianza > mejor[1]:
            mejor = (producto, confianza)

    if mejor and mejor[1] >= 0.80:
        return mejor
    return None


def interpretar_pedido(
    transcript: str,
    catalog: list[dict[str, Any]],
    catalog_version: str,
    customer_id: str,
    message_id: str,
    comercio_id: str | None = None,
) -> Dict[str, Any]:
    """Interpreta la transcripcion usando el catalogo como contexto.

    Normaliza el texto, busca productos contra nombres/aliases del catalogo,
    extrae cantidades y unidades de medida, detecta productos no disponibles,
    productos inexistentes y ambiguedades. No modifica la transcripcion original.
    """
    texto_original = transcript or ""
    texto_norm = normalizar_texto(texto_original)

    # Cargar catalogo externo si se proporciona comercio_id
    catalogo_externo: Dict[str, Any] | None = None
    if comercio_id and cargar_catalogo:
        try:
            catalogo_externo = cargar_catalogo(comercio_id)
            productos_cat = list(catalogo_externo.get("productos", []))
            # Incluir producto_no_disponible si existe (ej. nafta super en supermercado)
            prod_no_disp = producto_no_disponible(catalogo_externo) if producto_no_disponible else None
            if prod_no_disp:
                productos_cat.append(prod_no_disp)
            catalog = productos_cat
        except Exception:
            catalog = list(catalog or [])

    # 1. Cantidad total mencionada (solo como referencia, no se asume distribucion)
    cantidad_total = _extraer_cantidad_total(texto_norm)

    # 2. Modalidad de entrega
    modalidad = _detectar_modalidad(texto_norm)

    # 3. Extraer fragmentos cantidad+unidad+producto (desde texto original para preservar comas)
    fragmentos = _extraer_fragmentos_producto(texto_original, catalog)

    # 4. Buscar cada fragmento contra el catalogo
    items_salida: List[Dict[str, Any]] = []
    productos_no_identificados: List[Dict[str, Any]] = []
    productos_no_disponibles: List[Dict[str, Any]] = []
    errores: List[str] = []
    missing_information: List[str] = []

    sku_vistos: set[str] = set()

    for frag in fragmentos:
        texto_prod = normalizar_texto(frag["texto_producto"])
        if not texto_prod:
            continue

        # Buscar todas las coincidencias en catalogo para detectar ambiguedad
        todas_coincidencias: List[Tuple[float, Dict[str, Any], str, str]] = []
        for producto in catalog:
            match = _buscar_producto_en_texto(texto_prod, producto)
            if not match:
                continue
            confianza, frase_original, metodo, texto_coincidente = match
            sku = str(producto.get("sku", ""))
            if sku in sku_vistos:
                continue
            todas_coincidencias.append((confianza, producto, metodo, texto_coincidente))

        if not todas_coincidencias:
            # Producto no encontrado en catalogo -> no identificar, no inventar.
            # Excepción: palabras genéricas de una sola palabra que son similares
            # a tokens de múltiples productos del catálogo (ej. "pizzas" ~ "pizza"
            # en varios nombres de pizza) no se tratan como productos no
            # identificados.
            texto_tokens = set(texto_prod.split())
            es_palabra_generica = False
            if len(texto_tokens) == 1:
                token = list(texto_tokens)[0]
                if len(token) >= 3:
                    productos_con_token_similar = 0
                    for p in catalog:
                        p_tokens = set(normalizar_texto(str(p.get("name", ""))).split())
                        a_tokens = set()
                        for a in list(p.get("aliases") or []) + list(p.get("phonetic_aliases") or []):
                            a_tokens |= set(normalizar_texto(str(a)).split())
                        # Verificar si el token es similar a algún token del producto
                        for pt in p_tokens | a_tokens:
                            if len(pt) >= 3:
                                ratio = difflib.SequenceMatcher(None, token, pt).ratio()
                                if ratio > 0.85:
                                    productos_con_token_similar += 1
                                    break
                    if productos_con_token_similar >= 2:
                        es_palabra_generica = True
            if not es_palabra_generica:
                productos_no_identificados.append({
                    "texto_original": frag["texto_producto"],
                    "cantidad": frag["cantidad"],
                    "unidad": frag["unidad"],
                    "fragmento": frag["fragmento_original"],
                })
            continue

        # Ordenar por confianza descendente
        todas_coincidencias.sort(key=lambda x: x[0], reverse=True)
        mejor_confianza = todas_coincidencias[0][0]

        # Detectar ambiguedad: múltiples productos con confianza similar
        coincidencias_similares = [
            c for c in todas_coincidencias
            if mejor_confianza - c[0] <= 0.05
        ]

        if len(coincidencias_similares) > 1:
            # Ambigüedad: múltiples productos con confianza similar
            # Si ya hay items identificados, ignorar este fragmento ambiguo
            # (puede ser una palabra genérica como "pizzas" que ya está
            # cubierta por productos específicos identificados)
            if items_salida:
                continue
            nombres_ambiguos = ", ".join(
                str(c[1].get("name", "")) for c in coincidencias_similares
            )
            productos_no_identificados.append({
                "texto_original": frag["texto_producto"],
                "cantidad": frag["cantidad"],
                "unidad": frag["unidad"],
                "fragmento": frag["fragmento_original"],
                "ambiguedad": f"múltiples productos posibles: {nombres_ambiguos}",
            })
            missing_information.append(
                f"ambiguedad_producto: '{frag['texto_producto']}' coincide con {len(coincidencias_similares)} productos"
            )
            continue

        mejor_match = todas_coincidencias[0]
        confianza, producto, metodo, texto_coincidente = mejor_match
        sku = str(producto.get("sku", ""))
        sku_vistos.add(sku)

        # Verificar disponibilidad
        available = bool(producto.get("available", False))
        if not available:
            productos_no_disponibles.append({
                "sku": sku,
                "nombre": str(producto.get("name", "")),
                "texto_original": frag["texto_producto"],
                "cantidad": frag["cantidad"],
                "unidad": frag["unidad"],
            })
            missing_information.append(
                f"producto_no_disponible: {producto.get('name', sku)} no esta disponible en este comercio"
            )
            continue

        cantidad = frag["cantidad"] if frag["cantidad"] is not None else 1
        unidad = frag["unidad"] or str(producto.get("unidad", "unidad"))

        try:
            unit_price = Decimal(str(producto["price"]))
        except (InvalidOperation, KeyError, TypeError):
            continue

        if confianza >= THRESHOLD_CONFIRM:
            nivel = "confirm"
        elif confianza >= THRESHOLD_SPECIFIC:
            nivel = "specific"
        else:
            nivel = "clarify"

        items_salida.append({
            "sku": sku,
            "name": str(producto.get("name", "")),
            "quantity": cantidad,
            "unit_price": str(unit_price.quantize(Decimal("0.01"))),
            "currency": str(producto.get("currency", "")),
            "confidence": round(confianza, 2),
            "original_text": frag["texto_producto"],
            "normalized_match": str(producto.get("name", "")).lower(),
            "match_method": metodo,
            "unidad": unidad,
            "observations": [f"nivel: {nivel}"],
            "available": available,
        })

    # 5. Detectar productos del catalogo mencionados sin cantidad explícita
    # (ya se manejan por fragmentos; si no hay fragmento, no se asume cantidad)

    # 6. Detectar ambiguedad en cantidades cuando hay múltiples productos
    # de la misma categoria con cantidad total pero sin distribucion clara
    if cantidad_total is not None and items_salida:
        suma_identificada = sum(it["quantity"] for it in items_salida)
        if suma_identificada < cantidad_total:
            missing_information.append(
                f"cantidad_total_vs_variantes: se mencionaron {cantidad_total} "
                f"unidades pero solo se identificaron {suma_identificada} variantes"
            )

    # 6.5. Filtrar productos_no_identificados genéricos ya cubiertos por items
    if cantidad_total is not None and items_salida:
        suma_identificada = sum(it["quantity"] for it in items_salida)
        if suma_identificada >= cantidad_total:
            # Cuando ya identificamos suficientes productos para cubrir la
            # cantidad total, cualquier producto_no_identificado adicional
            # es una descripción genérica ya cubierta (ej. "pizzas grandes"
            # ya representado por muzza + napolitana). Solo conservar
            # verdaderas ambigüedades (con campo "ambiguedad") que requieran
            # resolución del cliente.
            productos_no_identificados = [
                p for p in productos_no_identificados
                if "ambiguedad" in p
            ]
            missing_information = [
                m for m in missing_information
                if not m.startswith("ambiguedad_producto")
                and not m.startswith("productos_no_identificados")
            ]

    # 6.6. Buscar productos mencionados sin cantidad explícita (qty = 1 por defecto)
    # Solo para matches de alta confianza (>= 0.90) que no estén ya identificados
    skus_identificados = {it["sku"] for it in items_salida}
    texto_completo_norm = normalizar_texto(texto_original)
    
    # Recolectar todas las coincidencias en el texto completo para detectar ambiguedad
    coincidencias_texto_completo: List[Tuple[float, Dict[str, Any], str]] = []
    for producto in catalog:
        sku = str(producto.get("sku", ""))
        if sku in skus_identificados:
            continue
        match = _buscar_producto_en_texto(texto_completo_norm, producto)
        if not match:
            continue
        confianza, _, _, _ = match
        if confianza < THRESHOLD_CONFIRM:
            continue
        coincidencias_texto_completo.append((confianza, producto, match[3] if len(match) > 3 else ""))

    if len(coincidencias_texto_completo) > 1:
        # Detectar ambiguedad: múltiples productos con confianza similar
        # Solo si ya no tenemos suficientes productos identificados para cubrir
        # la cantidad total (evita falsas ambigüedades con palabras genéricas
        # como "pizzas" ya cubiertas por productos específicos).
        suma_identificada_tc = sum(it["quantity"] for it in items_salida)
        ya_cubierto = (
            cantidad_total is not None
            and suma_identificada_tc >= cantidad_total
        )
        if not ya_cubierto:
            coincidencias_texto_completo.sort(key=lambda x: x[0], reverse=True)
            mejor_confianza_tc = coincidencias_texto_completo[0][0]
            similares_tc = [
                c for c in coincidencias_texto_completo
                if mejor_confianza_tc - c[0] <= 0.05
            ]
            if len(similares_tc) > 1:
                nombres_ambiguos_tc = ", ".join(
                    str(c[1].get("name", "")) for c in similares_tc
                )
                missing_information.append(
                    f"ambiguedad_producto: '{texto_completo_norm}' coincide con {len(similares_tc)} productos: {nombres_ambiguos_tc}"
                )
                # No agregar ningún producto automáticamente
            else:
                # Solo una coincidencia clara, agregarla
                confianza, producto, texto_coinc = coincidencias_texto_completo[0]
                sku = str(producto.get("sku", ""))
                try:
                    unit_price = Decimal(str(producto["price"]))
                except (InvalidOperation, KeyError, TypeError):
                    unit_price = Decimal("0")
                available = bool(producto.get("available", False))
                if not available:
                    productos_no_disponibles.append({
                        "sku": sku,
                        "nombre": str(producto.get("name", "")),
                        "texto_original": str(producto.get("name", "")),
                        "cantidad": 1,
                        "unidad": str(producto.get("unidad", "unidad")),
                    })
                    missing_information.append(
                        f"producto_no_disponible: {producto.get('name', sku)} no esta disponible en este comercio"
                    )
                else:
                    items_salida.append({
                        "sku": sku,
                        "name": str(producto.get("name", "")),
                        "quantity": 1,
                        "unit_price": str(unit_price.quantize(Decimal("0.01"))),
                        "currency": str(producto.get("currency", "")),
                        "confidence": round(confianza, 2),
                        "original_text": str(producto.get("name", "")),
                        "normalized_match": str(producto.get("name", "")).lower(),
                        "match_method": "texto_completo",
                        "unidad": str(producto.get("unidad", "unidad")),
                        "observations": ["nivel: confirm", "cantidad_asumida: 1"],
                        "available": available,
                    })
    elif len(coincidencias_texto_completo) == 1:
        confianza, producto, texto_coinc = coincidencias_texto_completo[0]
        sku = str(producto.get("sku", ""))
        try:
            unit_price = Decimal(str(producto["price"]))
        except (InvalidOperation, KeyError, TypeError):
            unit_price = Decimal("0")
        available = bool(producto.get("available", False))
        if not available:
            productos_no_disponibles.append({
                "sku": sku,
                "nombre": str(producto.get("name", "")),
                "texto_original": str(producto.get("name", "")),
                "cantidad": 1,
                "unidad": str(producto.get("unidad", "unidad")),
            })
            missing_information.append(
                f"producto_no_disponible: {producto.get('name', sku)} no esta disponible en este comercio"
            )
        else:
            items_salida.append({
                "sku": sku,
                "name": str(producto.get("name", "")),
                "quantity": 1,
                "unit_price": str(unit_price.quantize(Decimal("0.01"))),
                "currency": str(producto.get("currency", "")),
                "confidence": round(confianza, 2),
                "original_text": str(producto.get("name", "")),
                "normalized_match": str(producto.get("name", "")).lower(),
                "match_method": "texto_completo",
                "unidad": str(producto.get("unidad", "unidad")),
                "observations": ["nivel: confirm", "cantidad_asumida: 1"],
                "available": available,
            })

    # 7. Productos no identificados -> aclaracion
    if productos_no_identificados:
        textos_no_id = ", ".join(
            f"'{p['texto_original']}'" for p in productos_no_identificados
        )
        missing_information.append(
            f"productos_no_identificados: no se reconocieron {textos_no_id}"
        )

    # 8. Determinar estado
    if missing_information or errores:
        estado = "requires_clarification"
    else:
        estado = "requires_confirmation"

    # 9. Subtotal solo de items disponibles y validados
    subtotal = Decimal("0")
    for it in items_salida:
        subtotal += Decimal(it["unit_price"]) * it["quantity"]
    subtotal = subtotal.quantize(Decimal("0.01"))

    fulfillment = {"type": modalidad, "requested_time": None, "address": None}

    return {
        "status": estado,
        "source_message_id": message_id,
        "items": items_salida,
        "fulfillment": fulfillment,
        "missing_information": missing_information,
        "productos_no_identificados": productos_no_identificados,
        "productos_no_disponibles": productos_no_disponibles,
        "subtotal": str(subtotal),
        "currency": catalog[0].get("currency", "") if catalog else "",
        "customer_message": "Pedido interpretado. Confirma para registrar.",
    }


# --- Orquestador principal --------------------------------------------------

class OrquestadorPedidos:
    def __init__(self, commerce_id: str):
        self.commerce_id = commerce_id
        self.estado: Dict[str, Any] = {}

    def procesar_webhook(self, evento: Dict[str, Any]) -> Dict[str, Any]:
        """Punto de entrada del webhook de WhatsApp."""
        message_id = evento.get("message_id")
        if not message_id:
            return {"error": "message_id ausente", "estado": "rejected"}

        # Idempotencia inicial: si ya procesamos este mensaje, devolver resultado.
        clave = clave_idempotencia(
            self.commerce_id,
            str(message_id),
            "interpret",
            str(evento.get("catalog_version", "")),
        )
        if self._ya_procesado(clave):
            return {"estado": "duplicado", "message_id": message_id, "resultado": self._obtener_resultado(clave)}

        # 1. Validar evento
        if validate_event:
            validacion = validate_event(evento, self.commerce_id)
            if not validacion["valid"]:
                return {"estado": "rejected", "errores": validacion["errors"], "message_id": message_id}
            evento = validacion["event"]
            clave = validacion["idempotency_key"]

        catalog = evento.get("catalog", []) or consultar_catalogo(self.commerce_id, evento.get("catalog_version", ""))
        transcript = evento.get("transcript") or ""

        # 2. Si hay audio pero no transcripcion, descargar y transcribir
        if not transcript and evento.get("audio_url"):
            ruta_audio = descargar_audio(str(message_id), evento.get("audio_url"))
            transcript = transcribir_audio(ruta_audio)
            # Borrar audio temporal luego de transcribir (politica de datos)
            try:
                os.remove(ruta_audio)
            except OSError:
                pass

        # 3. Interpretar con la skill
        interpretacion = interpretar_pedido(
            transcript=transcript,
            catalog=catalog,
            catalog_version=str(evento.get("catalog_version", "")),
            customer_id=evento.get("customer_id", ""),
            message_id=str(message_id),
        )

        # 4. Validar pedido
        if validate_pedido and calcular_total:
            validacion_pedido = validate_pedido(
                interpretacion.get("items", []),
                catalog,
                interpretacion.get("fulfillment"),
            )
            if not validacion_pedido["valid"]:
                return {
                    "estado": "requires_clarification",
                    "message_id": message_id,
                    "errores": validacion_pedido["errores"],
                    "advertencias": validacion_pedido.get("warnings", []),
                }

            total = calcular_total(
                validacion_pedido["items"],
                currency=interpretacion.get("currency", ""),
            )
            interpretacion["total"] = total.get("total")
            interpretacion["subtotal"] = total.get("subtotal")
            interpretacion["currency"] = total.get("currency")

        # 5. Determinar estado siguiente
        if interpretacion.get("missing_information"):
            estado = "requires_clarification"
        else:
            estado = "requires_confirmation"

        resultado = {
            "estado": estado,
            "message_id": message_id,
            "clave_idempotencia": clave,
            "pedido": interpretacion,
            "timestamp": ahora_iso(),
        }

        self._guardar_resultado(clave, resultado)
        return resultado

    def confirmar_registro(self, clave_idempotencia: str, confirmacion_explicita: bool = True) -> Dict[str, Any]:
        """Registra el pedido solo si hubo confirmacion explicita del cliente."""
        if not confirmacion_explicita:
            return {"estado": "rechazado", "motivo": "Falta confirmacion explicita del cliente"}

        resultado = self._obtener_resultado(clave_idempotencia)
        if not resultado:
            return {"estado": "no_encontrado", "motivo": "No existe pedido para esa clave"}

        pedido = resultado.get("pedido", {})
        comercio = self.commerce_id

        if registrar_pedido:
            registro = registrar_pedido(pedido, comercio, registrar=SIMULATION_MODE)
        else:
            registro = {"estado": "borrador", "simulacion": True, "mensaje": "registrar_pedido no disponible"}

        salida = {
            "estado": registro.get("estado", "borrador"),
            "clave_pedido": registro.get("clave_pedido"),
            "clave_idempotencia": clave_idempotencia,
            "simulacion": registro.get("simulacion", True),
            "registro": registro,
            "timestamp": ahora_iso(),
        }

        # Log anonimizado (politica de datos)
        if anonimizar_para_log:
            print(json.dumps(anonimizar_para_log(salida), ensure_ascii=False))
        else:
            print(json.dumps(salida, ensure_ascii=False))

        return salida

    # --- Almacenamiento de resultados (idempotencia) ------------------------

    def _almacen_dir(self) -> str:
        base = os.environ.get("ORQUESTADOR_ALMACEN", os.path.join(os.path.dirname(__file__), ".estado"))
        os.makedirs(base, exist_ok=True)
        return base

    def _ruta_clave(self, clave: str) -> str:
        return os.path.join(self._almacen_dir(), f"{clave}.json")

    def _ya_procesado(self, clave: str) -> bool:
        return os.path.exists(self._ruta_clave(clave))

    def _guardar_resultado(self, clave: str, resultado: Dict[str, Any]) -> None:
        try:
            with open(self._ruta_clave(clave), "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise OrquestadorError(f"No se pudo guardar el resultado: {exc}")

    def _obtener_resultado(self, clave: str) -> Optional[Dict[str, Any]]:
        try:
            with open(self._ruta_clave(clave), "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None


def cargar_evento_desde_archivo(ruta: str) -> Dict[str, Any]:
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python orchestrator.py <webhook|test-evento> [archivo.json] [--registrar]")
        return 2

    modo = sys.argv[1]
    comercio = os.environ.get("COMMERCE_ID", "comercio-demo")
    registrar = "--registrar" in sys.argv or os.environ.get("REGISTRAR_PEDIDOS", "0").lower() in ("1", "true", "yes")

    orquestador = OrquestadorPedidos(comercio)

    if modo == "webhook":
        print("Modo webhook: escuchar eventos de WhatsApp. Procesar evento a evento con procesar_webhook().")
        return 0

    if modo == "test-evento":
        if len(sys.argv) < 3:
            print("Falta archivo de evento JSON")
            return 2
        evento = cargar_evento_desde_archivo(sys.argv[2])
        resultado = orquestador.procesar_webhook(evento)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))

        if resultado.get("estado") == "requires_confirmation" and registrar:
            clave = resultado.get("clave_idempotencia")
            if clave:
                print("--- Registro (confirmacion simulada) ---")
                orquestador.confirmar_registro(clave, confirmacion_explicita=True)
        return 0

    print(f"Modo desconocido: {modo}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
