"""Pipeline que encadena los 7 agentes especializados.

Flujo:
receptor -> transcripcion -> interpretacion -> validacion -> calculo ->
confirmacion -> registro

Cada agente recibe el contexto y lo devuelve mutado. El pipeline detiene la
ejecucion ante errores o cuando se requiere interaccion con el cliente.

Soporta un callback opcional de eventos de progreso para observabilidad en
tiempo real sin modificar el contrato publico de los agentes.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _paths import _ORCH  # noqa: E402

if _ORCH not in sys.path:
    sys.path.insert(0, _ORCH)

from agente_receptor import run as run_receptor  # noqa: E402
from agente_transcripcion import run as run_transcripcion  # noqa: E402
from agente_interpretacion import run as run_interpretacion  # noqa: E402
from agente_validacion import run as run_validacion  # noqa: E402
from agente_calculo import run as run_calculo  # noqa: E402
from agente_confirmacion import run as run_confirmacion  # noqa: E402
from agente_registro import run as run_registro  # noqa: E402
from contexto import nuevo_contexto, hay_errores, estado  # noqa: E402

AGENTES: List[str] = [
    "receptor",
    "transcripcion",
    "interpretacion",
    "validacion",
    "calculo",
    "confirmacion",
    "registro",
]

# Politicas aplicadas por agente (para observabilidad, sin modificar reglas)
AGENT_POLICIES: Dict[str, str] = {
    "receptor": "Validacion de esquema e idempotencia inicial",
    "transcripcion": "Descarga y transcripcion de audio (faster-whisper, CPU, int8)",
    "interpretacion": "Normalizacion y coincidencia contra catalogo del comercio",
    "validacion": "No inventar productos ni precios; validar contra catalogo",
    "calculo": "Utilizar exclusivamente precios validados del catalogo",
    "confirmacion": "No confirmar pedidos incompletos ni sin consentimiento",
    "registro": "Registro simulado por defecto (REGISTRAR_PEDIDOS=0)",
}

# Acciones descritas por agente (para observabilidad)
AGENT_ACTIONS: Dict[str, str] = {
    "receptor": "Validar evento webhook y extraer message_id",
    "transcripcion": "Descargar audio y transcribir a texto",
    "interpretacion": "Interpretar transcripcion contra catalogo",
    "validacion": "Validar productos, cantidades y disponibilidad",
    "calculo": "Calcular subtotal y total con aritmetica decimal",
    "confirmacion": "Generar resumen de confirmacion o aclaracion",
    "registro": "Registrar pedido confirmado (simulado)",
}

# Nombres amigables para la UI (con tildes)
AGENT_DISPLAY_NAMES: Dict[str, str] = {
    "receptor": "Receptor",
    "transcripcion": "TranscripciÃ³n",
    "interpretacion": "InterpretaciÃ³n",
    "validacion": "ValidaciÃ³n",
    "calculo": "CÃ¡lculo",
    "confirmacion": "ConfirmaciÃ³n",
    "registro": "Registro",
}


def _normalizar_agent_id(nombre_texto: str) -> str:
    """Normaliza un nombre de agente a su identificador tÃ©cnico estable.

    Quita tildes, espacios, mayÃºsculas y caracteres especiales para generar
    una clave tÃ©cnica consistente (ej. "TranscripciÃ³n" -> "transcripcion").
    """
    import unicodedata
    texto = str(nombre_texto).lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.replace(" ", "").replace("-", "").replace("_", "")
    return texto


def _emit_event_modulo(
    event_callback: Optional[Callable[[Dict[str, Any]], None]],
    trace_id_val: str,
    agent_id: str,
    agent_name: str,
    status: str,
    action: str,
    policy: str,
    result: str,
) -> None:
    """Emite un evento de progreso al callback si existe."""
    if event_callback is None:
        return
    event_callback({
        "trace_id": trace_id_val,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "status": status,
        "action": action,
        "policy": policy,
        "result": result,
        "timestamp": time.time(),
    })


def ejecutar(
    commerce_id: str,
    evento: Dict[str, Any],
    numero_cliente: str | None = None,
    confirmacion: bool | None = None,
    registrar: bool | None = None,
    event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Ejecuta los 7 agentes en secuencia y retorna el contexto final.

    Parametros adicionales:
        event_callback: Funcion opcional que recibe eventos de progreso
            (agent_started, agent_completed, agent_blocked, agent_failed).
            No modifica el contrato publico de los agentes.
    """
    ctx = nuevo_contexto(commerce_id, evento)
    trace_id_val = ctx.get("trace_id", "desconocido")

    # Historial de eventos para reducción determinista en la UI.
    agent_events_historial: List[Dict[str, Any]] = []

    # Estado global inicial (antes de ejecutar cualquier agente).
    st_actual = estado(ctx)

    def _emit_local(
        agent_id: str,
        agent_name: str,
        status: str,
        action: str,
        policy: str,
        result: str,
    ) -> None:
        ev = {
            "trace_id": trace_id_val,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "status": status,
            "action": action,
            "policy": policy,
            "result": result,
            "timestamp": time.time(),
        }
        agent_events_historial.append(ev)
        if event_callback is not None:
            event_callback(ev)

    pasos = [
        ("receptor", run_receptor, {}),
        ("transcripcion", run_transcripcion, {}),
        ("interpretacion", run_interpretacion, {}),
        ("validacion", run_validacion, {}),
        ("calculo", run_calculo, {}),
        (
            "confirmacion",
            run_confirmacion,
            {"numero_cliente": numero_cliente, "confirmacion": confirmacion},
        ),
        ("registro", run_registro, {"registrar": registrar}),
    ]

    for nombre, fn, kwargs in pasos:
        agent_id = nombre  # identificador tÃ©cnico estable (sin tildes)
        agent_name = AGENT_DISPLAY_NAMES.get(nombre, nombre)  # nombre con tildes
        policy = AGENT_POLICIES.get(nombre, "")
        action = AGENT_ACTIONS.get(nombre, "")

        _emit_local(agent_id,
            agent_name,
            "procesando",
            action,
            policy,
            "Ejecutando agente...",
        )

        try:
            ctx = fn(ctx, **kwargs)
        except Exception as exc:  # noqa: BLE001
            ctx["estado"] = "rejected"
            ctx["errores"].append(f"Fallo en agente {nombre}: {exc}")
            _emit_local(agent_id,
                agent_name,
                "fallido",
                action,
                policy,
                f"Error: {exc}",
            )
            break

        if hay_errores(ctx) and ctx["estado"] in ("rejected",):
            _emit_local(agent_id,
                agent_name,
                "fallido",
                action,
                policy,
                "; ".join(ctx["errores"]),
            )
            break

        # Determinar el estado INDIVIDUAL del agente (no el estado global del pedido).
        pedido_ctx = ctx.get("pedido", {}) or {}
        missing_info = list(pedido_ctx.get("missing_information", []) or [])
        productos_no_id = list(pedido_ctx.get("productos_no_identificados", []) or [])
        productos_no_disp = list(pedido_ctx.get("productos_no_disponibles", []) or [])
        st_actual = estado(ctx)

        # --- Reglas de estado individual por agente ---
        if nombre == "interpretacion":
            # InterpretaciÃ³n detectÃ³ ambigÃ¼edad si hay productos no identificados,
            # productos no disponibles o missing_information.
            items_ctx = ctx.get("items", [])
            if productos_no_id or productos_no_disp or missing_info or not items_ctx:
                resultado_txt = []
                if productos_no_id:
                    resultado_txt.append(
                        f"{len(productos_no_id)} producto(s) no identificado(s)"
                    )
                if productos_no_disp:
                    resultado_txt.append(
                        f"{len(productos_no_disp)} no disponible(s)"
                    )
                if missing_info:
                    resultado_txt.append("requiere aclaraciÃ³n")
                if not items_ctx and not productos_no_id and not productos_no_disp and not missing_info:
                    resultado_txt.append("sin ítems válidos para interpretar")
                _emit_local(agent_id,
                    agent_name,
                    "bloqueado",
                    action,
                    policy,
                    "; ".join(resultado_txt),
                )
            else:
                _emit_local(agent_id,
                    agent_name,
                    "completado",
                    action,
                    policy,
                    f"{len(items_ctx)} producto(s) detectado(s)",
                )

        elif nombre == "validacion":
            # ValidaciÃ³n completÃ³ su tarea si validÃ³ los items interpretados.
            items_validos = len(ctx.get("items", []))
            _emit_local(agent_id,
                agent_name,
                "completado",
                action,
                policy,
                f"{items_validos} item(es) validado(s)",
            )

        elif nombre == "calculo":
            # CÃ¡lculo completÃ³ su tarea si obtuvo subtotal y total sin error propio.
            # requires_confirmation NO bloquea al CÃ¡lculo.
            subtotal = ctx.get("subtotal", "")
            total = ctx.get("total", "")
            items = ctx.get("items", [])
            # Si no hay ítems válidos, no marcar como fallido: bloqueado por precondiciÃ³n.
            if not items or subtotal == "" or total == "":
                _emit_local(agent_id,
                    agent_name,
                    "no_ejecutado",
                    action,
                    policy,
                    "PrecondiciÃ³n no cumplida: sin ítems vÃ¡lidos para calcular",
                )
                break
            _emit_local(agent_id,
                agent_name,
                "completado",
                action,
                policy,
                f"Subtotal {subtotal} / Total {total}",
            )

        elif nombre == "confirmacion":
            # ConfirmaciÃ³n solo puede completar si el cliente confirmÃ³ explÃ­citamente.
            if st_actual in ("requires_clarification", "requires_confirmation") and confirmacion is None:
                _emit_local(agent_id,
                    agent_name,
                    "bloqueado",
                    action,
                    policy,
                    "Esperando confirmaciÃ³n explÃ­cita del cliente",
                )
                break
            else:
                _emit_local(agent_id,
                    agent_name,
                    "completado",
                    action,
                    policy,
                    f"Estado: {st_actual}",
                )

        elif nombre == "registro":
            # Registro solo se ejecuta si el cliente confirmó explícitamente.
            # Modo simulación (registrar_flag=False): se marca como completado
            # pero con registration_status=simulated y persistence_status=not_persisted.
            if st_actual in ("requires_clarification", "rejected") or confirmacion is None:
                _emit_local(agent_id,
                    agent_name,
                    "no_ejecutado",
                    action,
                    policy,
                    "Pendiente de confirmación del cliente",
                )
                break
            else:
                _emit_local(agent_id,
                    agent_name,
                    "completado",
                    action,
                    policy,
                    f"Estado: {st_actual}",
                )

        else:
            # Receptor y TranscripciÃ³n: completado si no hubo error.
            _emit_local(agent_id,
                agent_name,
                "completado",
                action,
                policy,
                f"Estado: {st_actual}",
            )

    # ReducciÃ³n determinista: el evento final de cada agent_id define su estado.
    # agent_completado prevalece sobre agent_started.
    # agent_failed prevalece sobre cualquier otro.
    # agent_bloqueado prevalece sobre agent_completado solamente para ese agente.
    # no_ejecutado se muestra como gris.
    estados_agentes_finales: Dict[str, Dict[str, Any]] = {}
    for ev in reversed(agent_events_historial):
        aid = ev.get("agent_id")
        if aid and aid not in estados_agentes_finales:
            estados_agentes_finales[aid] = ev

    # Recalcular estado final del contexto (despues de todos los agentes).
    st_actual = estado(ctx)
    confirmacion_explicita = confirmacion is True

    # Determinar order_status, registration_status, persistence_status

    if st_actual == "requires_clarification":
        order_status = "pending_clarification"
    elif st_actual == "requires_confirmation":
        # Pedido completo, pendiente de confirmacion del cliente.
        # confirmed solo si confirmacion_explicita es True.
        # Detectar ambigüedades de cantidad no capturadas por el interprete:
        # si hay items con qty > 1 y hay varios productos distintos, y la
        # suma de cantidades excede el numero de productos por al menos 2,
        # puede haber distribucion ambigua (ej. "tres pizzas una de X y
        # otra de Y" interpretado como 3 de X y 1 de Y = 4 total, pero el
        # cliente pidio 3).
        items_ctx = ctx.get("items", []) or []
        missing_info = list((ctx.get("pedido", {}) or {}).get("missing_information", []) or [])
        productos_no_id = list((ctx.get("pedido", {}) or {}).get("productos_no_identificados", []) or [])
        qty_total = sum(it.get("quantity", 1) for it in items_ctx)
        num_productos = len(items_ctx)
        tiene_qty_multiple = any(it.get("quantity", 1) > 1 for it in items_ctx)
        hay_varios_productos = num_productos > 1
        excede_cantidad = qty_total > num_productos + 1
        if (
            tiene_qty_multiple
            and hay_varios_productos
            and excede_cantidad
            and not missing_info
            and not productos_no_id
            and not confirmacion_explicita
        ):
            order_status = "pending_clarification"
        elif confirmacion_explicita:
            order_status = "confirmed"
        else:
            order_status = "pending_confirmation"
    elif st_actual == "confirmed":
        order_status = "confirmed"
    elif st_actual == "registered":
        order_status = "confirmed"
    elif st_actual == "cancelled":
        order_status = "cancelled"
    elif st_actual == "rejected":
        order_status = "cancelled"
    elif st_actual == "borrador" and confirmacion_explicita:
        # Registro en simulacion completado despues de confirmacion explicita
        order_status = "confirmed"
    else:
        order_status = "pending_confirmation"

    registro_ev = estados_agentes_finales.get("registro", {})
    registro_status = registro_ev.get("status", "no_ejecutado")
    if registro_status == "completado":
        # Si el contexto dice borrador despues del registro, es simulacion
        if st_actual == "borrador":
            registration_status = "simulated"
            persistence_status = "not_persisted"
        else:
            registration_status = "registered"
            persistence_status = "persisted"
    elif registro_status == "no_ejecutado":
        registration_status = "pending_confirmation"
        persistence_status = "not_persisted"
    else:
        registration_status = registro_status
        persistence_status = "not_persisted"

    # Anotar estados separados en el contexto para la UI
    ctx["order_status"] = order_status
    ctx["registration_status"] = registration_status
    ctx["persistence_status"] = persistence_status
    ctx["agent_states"] = {
        aid: {
            "status": ev.get("status"),
            "agent_name": ev.get("agent_name"),
            "result": ev.get("result"),
            "policy": ev.get("policy"),
        }
        for aid, ev in estados_agentes_finales.items()
    }

    return ctx


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Uso: python pipeline.py <commerce_id> <evento.json> "
            "[numero_cliente] [--confirmar] [--registrar]"
        )
        return 2

    commerce_id = sys.argv[1]
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        evento = json.load(f)

    numero = sys.argv[3] if len(sys.argv) > 3 else None
    confirmar = "--confirmar" in sys.argv
    reg = "--registrar" in sys.argv

    ctx = ejecutar(
        commerce_id,
        evento,
        numero_cliente=numero,
        confirmacion=confirmar if confirmar else None,
        registrar=reg,
    )

    print(json.dumps(ctx, ensure_ascii=False, indent=2))
    return 0 if not hay_errores(ctx) else 1


if __name__ == "__main__":
    sys.exit(main())



