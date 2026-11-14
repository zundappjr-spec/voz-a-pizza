"""Interfaz web (Streamlit) — Tomador inteligente de pedidos por voz.

Interfaz rediseñada con look & feel moderno de dashboard de IA:
- Dos columnas (izquierda: configuracion y audio; derecha: estado de agentes)
- Componente "Flujo Inteligente" con animacion de los 7 agentes
- Tarjeta del Orquestador con barra de progreso real
- Eventos de progreso reales del pipeline (no simulados)
- Tarjeta de resultado final diferenciada por estado

Solo se modifica la presentacion visual y los mecanismos de observabilidad.
No se toca la logica de negocio, Whisper, catálogos, cálculos ni contratos.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone

# --- Asegurar que faster-whisper encuentre ffmpeg (MP3/WAV/OGG) -------------
import imageio_ffmpeg as _iio  # noqa: E402

_bin_dir = os.path.dirname(_iio.get_ffmpeg_exe())
os.environ["PATH"] = _bin_dir + os.pathsep + os.environ.get("PATH", "")

# --- Rutas del proyecto ------------------------------------------------------
_BASE = os.path.dirname(os.path.abspath(__file__))
_AGENTES = os.path.join(_BASE, "agentes")
for _p in (_BASE, _AGENTES):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st  # noqa: E402

from transcriptor import transcribir, extension_valida  # noqa: E402
from contexto import nuevo_contexto, hay_errores, estado  # noqa: E402
from pipeline import ejecutar  # noqa: E402

# --- Cargador de catálogos externos ------------------------------------------
_CATALOGO_LOADER_DIR = os.path.abspath(
    os.path.join(_BASE, "orquestador-pedidos-whatsapp", "config")
)
if _CATALOGO_LOADER_DIR not in sys.path:
    sys.path.insert(0, _CATALOGO_LOADER_DIR)

try:
    from catalogo_loader import cargar_catalogo, listar_comercios_disponibles  # noqa: E402
except Exception:  # pragma: no cover
    cargar_catalogo = None  # type: ignore
    listar_comercios_disponibles = None  # type: ignore

CATALOGOS_POR_COMERCIO: dict[str, list[dict]] = {}


def _cargar_catalogo_comercio(comercio_id: str) -> list[dict]:
    """Carga el catalogo de un comercio desde archivo externo."""
    if comercio_id in CATALOGOS_POR_COMERCIO:
        return CATALOGOS_POR_COMERCIO[comercio_id]
    if cargar_catalogo:
        try:
            datos = cargar_catalogo(comercio_id)
            productos = list(datos.get("productos", []))
            CATALOGOS_POR_COMERCIO[comercio_id] = productos
            return productos
        except Exception:
            pass
    return []

# --- Paleta de colores -------------------------------------------------------
COLOR_PRIMARIO = "#102A43"      # Azul oscuro
COLOR_EXITO = "#12BFA0"         # Verde turquesa
COLOR_ACTIVO = "#2496FF"        # Azul activo
COLOR_ADVERTENCIA = "#F5A623"   # Naranja advertencia
COLOR_ERROR = "#E74C3C"         # Rojo error
COLOR_FONDO = "#F6F8FA"         # Fondo claro
COLOR_TEXTO = "#1A1A1A"
COLOR_BORDE = "#D1D9E6"

# --- Configuracion de pagina -------------------------------------------------
st.set_page_config(
    page_title="VozPedido - Tomador de pedidos por voz",
    page_icon="\U0001F4DE",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- CSS personalizado -------------------------------------------------------
st.markdown(
    f"""
    <style>
    :root {{
        --primario: {COLOR_PRIMARIO};
        --exito: {COLOR_EXITO};
        --activo: {COLOR_ACTIVO};
        --advertencia: {COLOR_ADVERTENCIA};
        --error: {COLOR_ERROR};
        --fondo: {COLOR_FONDO};
        --texto: {COLOR_TEXTO};
        --borde: {COLOR_BORDE};
    }}

    .stApp {{
        background-color: var(--fondo);
        color: var(--texto);
    }}

    /* Ocultar elementos por defecto de Streamlit */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* Tarjetas */
    .tarjeta {{
        background: #FFFFFF;
        border: 1px solid var(--borde);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}

    .tarjeta-orquestador {{
        background: linear-gradient(135deg, var(--primario) 0%, #1E4A70 100%);
        color: #FFFFFF;
        border: none;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 16px rgba(16,42,67,0.15);
    }}

    /* Encabezados */
    h1, h2, h3, h4 {{
        color: var(--primario);
        font-weight: 700;
        letter-spacing: -0.02em;
    }}

    h1 {{
        font-size: 1.75rem;
        margin-bottom: 0.25rem;
    }}

    .subtitulo {{
        color: #6B7280;
        font-size: 0.875rem;
        margin-bottom: 1.5rem;
    }}

    /* Badges de estado */
    .badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.1875rem 0.625rem;
        border-radius: 16px;
        font-size: 0.6875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        white-space: nowrap;
    }}
    .badge-pendiente {{ background: #E5E7EB; color: #6B7280; }}
    .badge-procesando {{ background: #DBEAFE; color: #1E40AF; }}
    .badge-completado {{ background: #D1FAE5; color: #065F46; }}
    .badge-bloqueado {{ background: #FEF3C7; color: #92400E; }}
    .badge-fallido {{ background: #FEE2E2; color: #991B1B; }}
    .badge-no-ejecutado {{ background: #F3F4F6; color: #9CA3AF; }}

    /* Animacion de pulso para procesando */
    @keyframes pulso {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.6; }}
    }}
    .pulso {{
        animation: pulso 1.5s ease-in-out infinite;
    }}

    /* Barra de progreso del orquestador */
    .progreso-contenedor {{
        background: #E5E7EB;
        border-radius: 8px;
        height: 8px;
        margin-top: 0.5rem;
        overflow: hidden;
    }}
    .progreso-barra {{
        background: linear-gradient(90deg, var(--activo), var(--exito));
        height: 100%;
        border-radius: 8px;
        transition: width 0.5s ease;
    }}

    /* Tarjetas de agentes */
    .agente-tarjeta {{
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.6rem 0.85rem;
        border: 1px solid var(--borde);
        border-radius: 8px;
        margin-bottom: 0.5rem;
        background: #FFFFFF;
        transition: all 0.2s ease;
    }}
    .agente-tarjeta:hover {{
        border-color: var(--primario);
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }}
    .agente-icono {{
        width: 32px;
        height: 32px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        flex-shrink: 0;
    }}
    .agente-icono-pendiente {{ background: #E5E7EB; color: #6B7280; }}
    .agente-icono-procesando {{ background: #DBEAFE; color: #1E40AF; }}
    .agente-icono-completado {{ background: #D1FAE5; color: #065F46; }}
    .agente-icono-bloqueado {{ background: #FEF3C7; color: #92400E; }}
    .agente-icono-fallido {{ background: #FEE2E2; color: #991B1B; }}
    .agente-icono-no-ejecutado {{ background: #F3F4F6; color: #9CA3AF; }}

    .agente-info {{
        flex: 1;
        min-width: 0;
    }}
    .agente-nombre {{
        font-weight: 600;
        font-size: 0.875rem;
        color: var(--texto);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .agente-resultado {{
        font-size: 0.75rem;
        color: #4B5563;
        margin-top: 0.125rem;
        font-family: ui-monospace, SFMono-Regular, monospace;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .agente-politica {{
        font-size: 0.65rem;
        color: #9CA3AF;
        margin-top: 0.125rem;
        font-style: italic;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    /* Resultado final */
    .resultado-tarjeta {{
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }}
    .resultado-valido {{
        background: #D1FAE5;
        border: 1px solid #86EFAC;
        color: #065F46;
    }}
    .resultado-incompleto {{
        background: #FEF3C7;
        border: 1px solid #FCD34D;
        color: #92400E;
    }}
    .resultado-error {{
        background: #FEE2E2;
        border: 1px solid #FECACA;
        color: #991B1B;
    }}

    /* Diagnostico colapsable */
    .diagnostico-titulo {{
        font-weight: 600;
        color: var(--primario);
        margin-bottom: 0.5rem;
    }}

    /* Columnas */
    .columna-izquierda {{
        padding-right: 1rem;
    }}
    .columna-derecha {{
        padding-left: 1rem;
    }}

    /* Etiquetas de campo */
    .campo-etiqueta {{
        font-size: 0.75rem;
        font-weight: 600;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.25rem;
        display: block;
    }}
    .campo-valor {{
        font-size: 0.9375rem;
        color: var(--texto);
        margin-bottom: 0.75rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Estado de sesion -------------------------------------------------------
if "transcript" not in st.session_state:
    st.session_state["transcript"] = ""
if "audio_path" not in st.session_state:
    st.session_state["audio_path"] = None
if "resultado" not in st.session_state:
    st.session_state["resultado"] = None
if "agent_events" not in st.session_state:
    st.session_state["agent_events"] = []


def _limpiar_eventos() -> None:
    st.session_state["agent_events"] = []


def _registrar_evento(evento: Dict[str, Any]) -> None:
    st.session_state["agent_events"].append(evento)


# --- Encabezado --------------------------------------------------------------
st.markdown(
    f"""
    <div class="tarjeta">
        <h1>\U0001F4DE VozPedido</h1>
        <p class="subtitulo">
            Tomador inteligente de pedidos por voz  •  WhatsApp  •  faster-whisper
            (small, espanol, CPU, int8)  •  Local, sin APIs de transcripcion
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Layout de dos columnas --------------------------------------------------
col_izq, col_der = st.columns([1, 1.2], gap="large")

# ============================================================================
# COLUMNA IZQUIERDA: Configuracion, audio, transcripcion, resultado
# ============================================================================
with col_izq:
    st.markdown('<div class="columna-izquierda">', unsafe_allow_html=True)

    # --- Seccion 1: Configuracion -------------------------------------------
    st.markdown('<span class="campo-etiqueta">1. Comercio</span>', unsafe_allow_html=True)
    comercios = listar_comercios_disponibles() if listar_comercios_disponibles else []
    comercio_opciones = {c: c.replace("-", " ").title() for c in comercios}

    comercio_seleccionado = st.selectbox(
        "Seleccionar comercio",
        options=comercios,
        format_func=lambda c: comercio_opciones.get(c, c),
        index=0 if comercios else None,
        label_visibility="collapsed",
    )

    customer_id = st.text_input(
        "Customer ID (telefono/cliente)",
        value="",
        placeholder="Ej: +5491122334455",
    )
    catalog_version = st.text_input(
        "Version del catalogo",
        value=datetime.now(timezone.utc).isoformat(),
    )

    catalogo: list[dict] = []
    catalogo_valido = True
    if comercio_seleccionado:
        catalogo = _cargar_catalogo_comercio(comercio_seleccionado)
        if not catalogo:
            catalogo_valido = False
            st.error(f"No se pudo cargar el catalogo para '{comercio_seleccionado}'.")

    st.divider()

    # --- Seccion 2: Audio ---------------------------------------------------
    st.markdown('<span class="campo-etiqueta">2. Audio del pedido</span>', unsafe_allow_html=True)
    archivo = st.file_uploader(
        "Subir archivo de audio",
        type=["mp3", "wav", "ogg"],
        label_visibility="collapsed",
    )

    if archivo is not None:
        if not extension_valida(archivo.name):
            st.error("Extension no soportada. Usa MP3, WAV u OGG.")
        else:
            tmp_dir = os.path.join(_BASE, "tmp_audio")
            os.makedirs(tmp_dir, exist_ok=True)
            tmp_path = os.path.join(tmp_dir, archivo.name)
            with open(tmp_path, "wb") as f:
                f.write(archivo.getbuffer())
            st.session_state["audio_path"] = tmp_path
            st.audio(tmp_path)

    if st.button(
        "Transcribir audio",
        disabled=not st.session_state.get("audio_path"),
        use_container_width=True,
    ):
        with st.spinner("Transcribiendo con faster-whisper..."):
            try:
                texto = transcribir(st.session_state["audio_path"], idioma="es")
                st.session_state["transcript"] = texto
                st.success("Transcripcion completa.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Fallo al transcribir: {exc}")

    texto = st.text_area(
        "Texto reconocido",
        value=st.session_state["transcript"],
        height=120,
        help="Puedes editar el texto antes de procesar el pedido.",
        label_visibility="collapsed",
    )
    st.session_state["transcript"] = texto

    st.divider()

    # --- Seccion 3: Procesar ------------------------------------------------
    st.markdown('<span class="campo-etiqueta">3. Procesar pedido</span>', unsafe_allow_html=True)

    numero_cliente = st.text_input(
        "Numero de WhatsApp del cliente (opcional)",
        value="",
        placeholder="Ej: +5491122334455",
    )
    confirmar = st.checkbox(
        "Confirmo el pedido y autorizo el registro (modo simulacion)",
        value=False,
    )

    if st.button(
        "Ejecutar siete agentes",
        disabled=not texto.strip(),
        use_container_width=True,
        type="primary",
    ):
        if not catalogo_valido:
            st.error("Corrige el catalogo antes de continuar.")
        elif not customer_id:
            st.error("Ingresa un Customer ID.")
        elif not comercio_seleccionado:
            st.error("Selecciona un comercio.")
        else:
            # Limpiar eventos previos
            _limpiar_eventos()

            evento = {
                "message_id": f"wamid-web-{uuid.uuid4().hex[:12]}",
                "customer_id": customer_id,
                "transcript": texto.strip(),
                "catalog_version": catalog_version,
                "catalog": catalogo,
            }

            # Ejecutar pipeline con callback de eventos de progreso
            progreso_container = st.empty()
            estado_container = st.empty()

            with st.spinner("Procesando pedido a traves de los siete agentes..."):
                try:
                    ctx = ejecutar(
                        comercio_seleccionado,
                        evento,
                        numero_cliente=numero_cliente or None,
                        confirmacion=True if confirmar else None,
                        registrar=None,  # simulacion por defecto
                        event_callback=_registrar_evento,
                    )
                    st.session_state["resultado"] = ctx
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Fallo en el pipeline: {exc}")

            progreso_container.empty()
            estado_container.empty()

    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# COLUMNA DERECHA: Estado del orquestador y flujo de agentes
# ============================================================================
with col_der:
    st.markdown('<div class="columna-derecha">', unsafe_allow_html=True)

    # --- Tarjeta del Orquestador --------------------------------------------
    st.markdown('<div class="tarjeta-orquestador">', unsafe_allow_html=True)
    st.markdown("### \U0001F680 Orquestador")

    resultado = st.session_state.get("resultado")
    agent_events = st.session_state.get("agent_events", [])

    if resultado is None:
        estado_orquestador = "Esperando audio"
        progreso_pct = 0
        detalle_orquestador = "Listo para recibir un archivo de audio y procesar el pedido."
    else:
        # Usar order_status (estado comercial del pedido) en lugar de estado global
        order_status = resultado.get("order_status", "")
        total_agentes = 7
        agentes_completados = len(
            [e for e in agent_events if e.get("status") == "completado"]
        )
        progreso_pct = int((agentes_completados / total_agentes) * 100)

        estado_map = {
            "pending_clarification": "Requiere aclaración",
            "requires_confirmation": "Pendiente de confirmación",
            "confirmed": "Confirmado",
            "registered": "Finalizado",
            "rejected": "Error",
            "error": "Error",
        }
        estado_orquestador = estado_map.get(order_status, order_status or "Desconocido")
        detalle_orquestador = (
            f"{agentes_completados} de {total_agentes} agentes ejecutados."
            if agent_events
            else "Listo para procesar."
        )

    st.markdown(
        f"""
        <div style="margin-bottom: 0.5rem;">
            <span style="font-size:0.75rem; font-weight:600; color:#93C5FD; text-transform:uppercase; letter-spacing:0.05em;">Estado</span>
            <div style="font-size:1rem; font-weight:700; margin-top:0.125rem;">{estado_orquestador}</div>
        </div>
        <div class="progreso-contenedor">
            <div class="progreso-barra" style="width: {progreso_pct}%;"></div>
        </div>
        <div style="font-size:0.75rem; color:#93C5FD; margin-top:0.25rem;">{detalle_orquestador}</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Flujo Inteligente: 7 agentes ---------------------------------------
    st.markdown("### \U0001F9E0 Flujo inteligente de agentes")

    AGENTES_ORDEN = [
        ("receptor", "\U0001F4E5", "Receptor"),
        ("transcripcion", "\U0001F4A1", "Transcripción"),
        ("interpretacion", "\U0001F50D", "Interpretación"),
        ("validacion", "\U0001F527", "Validación"),
        ("calculo", "\U0001F4B0", "Cálculo"),
        ("confirmacion", "\u2705", "Confirmación"),
        ("registro", "\U0001F4BE", "Registro"),
    ]

    # Mapear eventos por agent_id (clave técnica estable, sin tildes).
    # Para compatibilidad con eventos anteriores sin agent_id, se normaliza
    # agent_name quitando tildes, espacios y mayúsculas.
    import unicodedata as _ud

    def _normalizar_clave(texto: str) -> str:
        t = str(texto).lower()
        t = _ud.normalize("NFD", t)
        t = "".join(c for c in t if _ud.category(c) != "Mn")
        return t.replace(" ", "").replace("-", "").replace("_", "")

    eventos_por_id: Dict[str, Dict[str, Any]] = {}
    for ev in agent_events:
        aid = ev.get("agent_id") or _normalizar_clave(ev.get("agent_name", ""))
        eventos_por_id[aid] = ev

    estado_css_map = {
        "pendiente": ("pendiente", "\U0001F4E5", "agente-icono-pendiente", "badge-pendiente"),
        "procesando": ("procesando", "\U0001F4A1", "agente-icono-procesando pulso", "badge-procesando"),
        "completado": ("completado", "\u2705", "agente-icono-completado", "badge-completado"),
        "bloqueado": ("bloqueado", "\u26A0", "agente-icono-bloqueado", "badge-bloqueado"),
        "fallido": ("fallido", "\u274C", "agente-icono-fallido", "badge-fallido"),
        "no_ejecutado": ("no_ejecutado", "\u25A1", "agente-icono-no-ejecutado", "badge-no-ejecutado"),
    }

    clave_estado_espanol = {
        "pendiente": "Pendiente",
        "procesando": "Procesando",
        "completado": "Completado",
        "bloqueado": "Requiere aclaración",
        "fallido": "Error",
        "no_ejecutado": "No ejecutado",
    }

    for clave_agente, icono_defecto, nombre_amigable in AGENTES_ORDEN:
        ev = eventos_por_id.get(clave_agente)
        if ev is None:
            _, icono, clase_icono, badge_cls = estado_css_map["pendiente"]
            texto_estado = clave_estado_espanol["pendiente"]
            texto_resultado = "Esperando ejecución"
            texto_politica = ""
        else:
            st_estado = ev.get("status", "pendiente")
            _, icono, clase_icono, badge_cls = estado_css_map.get(
                st_estado, estado_css_map["pendiente"]
            )
            texto_estado = clave_estado_espanol.get(st_estado, st_estado)
            texto_resultado = ev.get("result", "")
            texto_politica = ev.get("policy", "")
            icono = icono_defecto

        st.markdown(
            f"""
            <div class="agente-tarjeta">
                <div class="agente-icono {clase_icono}">{icono}</div>
                <div class="agente-info">
                    <div class="agente-nombre">{nombre_amigable}</div>
                    <div class="agente-resultado">{texto_resultado}</div>
                    <div class="agente-politica">{texto_politica}</div>
                </div>
                <span class="badge {badge_cls}">{texto_estado}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # --- Resultado final ----------------------------------------------------
    if resultado is not None:
        pedido = resultado.get("pedido", {})
        items = pedido.get("items", [])
        no_identificados = pedido.get("productos_no_identificados", [])
        no_disponibles = pedido.get("productos_no_disponibles", [])
        missing = pedido.get("missing_information", [])
        registro = resultado.get("registro", {})

        # Usar order_status (estado comercial del pedido) en lugar de estado global
        order_status = resultado.get("order_status", "")
        registration_status = resultado.get("registration_status", "")
        persistence_status = resultado.get("persistence_status", "")

        # Determinar clase visual del resultado basada en order_status
        if order_status in ("requires_clarification", "rejected", "error", "pending_clarification"):
            clase_resultado = "resultado-error"
            tipo_resultado = "Pedido incompleto"
            icono_resultado = "\u26A0"
        elif order_status in ("requires_confirmation", "confirmed"):
            clase_resultado = "resultado-incompleto"
            tipo_resultado = "Pedido pendiente de confirmación"
            icono_resultado = "\u23F3"
        elif order_status == "registered":
            clase_resultado = "resultado-valido"
            tipo_resultado = "Pedido registrado"
            icono_resultado = "\u2705"
        else:
            clase_resultado = "resultado-incompleto"
            tipo_resultado = "Estado indeterminado"
            icono_resultado = "\u2753"

        st.markdown(f"""
        <div class="resultado-tarjeta {clase_resultado}">
            <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:1rem;">
                <span style="font-size:1.5rem;">{icono_resultado}</span>
                <span style="font-weight:700; font-size:1rem;">{tipo_resultado}</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<span class="campo-etiqueta">Comercio</span>', unsafe_allow_html=True)
        st.markdown(f'<span class="campo-valor">{resultado.get("commerce_id", "N/A")}</span>', unsafe_allow_html=True)

        st.markdown('<span class="campo-etiqueta">Productos identificados</span>', unsafe_allow_html=True)
        if items:
            for it in items:
                st.markdown(
                    f'<span class="campo-valor">\u2022 {it.get("quantity", 1)}x '
                    f'{it.get("name", it.get("sku", "?"))} '
                    f"({it.get('unidad', 'unidad')}) = ${it.get('unit_price', 0)}</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<span class="campo-valor">Ninguno</span>', unsafe_allow_html=True)

        st.markdown('<span class="campo-etiqueta">Subtotal / Total</span>', unsafe_allow_html=True)
        st.markdown(
            f'<span class="campo-valor">${pedido.get("subtotal", "-")} / '
            f'${pedido.get("total", "-")} {pedido.get("currency", "")}</span>',
            unsafe_allow_html=True,
        )

        if no_identificados:
            st.markdown('<span class="campo-etiqueta">Productos no identificados</span>', unsafe_allow_html=True)
            for ni in no_identificados:
                st.markdown(
                    f'<span class="campo-valor">\u2022 "{ni["texto_original"]}" '
                    f"(cantidad: {ni.get('cantidad', '?')}, "
                    f"unidad: {ni.get('unidad', 'no especificada')})</span>",
                    unsafe_allow_html=True,
                )

        if no_disponibles:
            st.markdown('<span class="campo-etiqueta">Productos no disponibles</span>', unsafe_allow_html=True)
            for nd in no_disponibles:
                st.markdown(
                    f'<span class="campo-valor">\u2022 {nd["nombre"]} '
                    f"(SKU: {nd['sku']}, cantidad: {nd.get('cantidad', '?')})</span>",
                    unsafe_allow_html=True,
                )

        if missing:
            st.markdown('<span class="campo-etiqueta">Preguntas pendientes</span>', unsafe_allow_html=True)
            for m in missing:
                st.markdown(f'<span class="campo-valor">\u2022 {m}</span>', unsafe_allow_html=True)

        st.markdown(
            f'<span class="campo-etiqueta">Estado del pedido</span>'
            f'<span class="campo-valor">{order_status}</span>',
            unsafe_allow_html=True,
        )

        if registro:
            st.markdown('<span class="campo-etiqueta">Registro</span>', unsafe_allow_html=True)
            reg_simulacion = registro.get("simulacion", True)
            st.markdown(
                f'<span class="campo-valor">\u2022 Estado: {registration_status} | '
                f"Simulacion: {'si' if reg_simulacion else 'no'}</span>",
                unsafe_allow_html=True,
            )
            if registro.get("clave_pedido"):
                st.markdown(
                    f'<span class="campo-valor">\u2022 Clave: {registro["clave_pedido"]}</span>',
                    unsafe_allow_html=True,
                )
            # Mostrar persistencia real
            st.markdown(
                f'<span class="campo-valor">\u2022 Persistencia: {persistence_status}</span>',
                unsafe_allow_html=True,
            )
            # No mostrar "registrado" si esta en simulacion
            if not reg_simulacion and registration_status == "registered":
                st.success("Pedido registrado exitosamente.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# --- Diagnostico de agentes (colapsable por defecto) -------------------------
with st.expander("\U0001F50D Diagnostico de agentes", expanded=False):
    resultado_diag = st.session_state.get("resultado")
    if resultado_diag:
        st.markdown("**Trace ID:** `" + str(resultado_diag.get("trace_id", "N/A")) + "`")
        st.markdown(
            "**Estado del pedido:** `" + str(resultado_diag.get("order_status", "")) + "`"
        )
        st.markdown(
            "**Registro:** `" + str(resultado_diag.get("registration_status", "")) + "`"
        )
        st.markdown(
            "**Persistencia:** `" + str(resultado_diag.get("persistence_status", "")) + "`"
        )
        st.markdown("**Errores:** " + (str(resultado_diag.get("errores", [])) or "Ninguno"))
        st.markdown("**Advertencias:** " + (str(resultado_diag.get("advertencias", [])) or "Ninguna"))

        evento_diag = resultado_diag.get("evento", {})
        st.markdown("**Transcripcion:**")
        st.code(str(evento_diag.get("transcript", "")), language="text")

        st.markdown("**Catalogo cargado:**")
        st.code(
            json.dumps(evento_diag.get("catalog", []), ensure_ascii=False, indent=2),
            language="json",
        )

        pedido_diag = resultado_diag.get("pedido", {})
        st.markdown("**Salida del interprete:**")
        st.code(json.dumps(pedido_diag, ensure_ascii=False, indent=2), language="json")

        st.markdown("**Eventos de agentes capturados:**")
        if agent_events:
            for ev in agent_events:
                st.code(
                    json.dumps(ev, ensure_ascii=False, indent=2),
                    language="json",
                )
        else:
            st.info("No hay eventos de agentes capturados.")

        st.markdown("**Estado por agente (resumen):**")
        agent_states = resultado_diag.get("agent_states", {})
        if agent_states:
            # Orden fijo para mostrar en el diagnóstico
            orden_agentes = [
                "receptor", "transcripcion", "interpretacion",
                "validacion", "calculo", "confirmacion", "registro",
            ]
            for aid in orden_agentes:
                ev = agent_states.get(aid)
                if ev:
                    nombre = ev.get("agent_name", aid)
                    stt = ev.get("status", "desconocido")
                    res = ev.get("result", "")
                    st.write(f"- {nombre}: {stt} — {res}")
                else:
                    st.write(f"- {aid}: No ejecutado")
        else:
            st.write("- Receptor: evento validado y message_id extraído")
            st.write(
                "- Transcripción: "
                + ("presente" if resultado_diag.get("transcript") else "ausente")
            )
            st.write(
                "- Interpretación: "
                + str(len(pedido_diag.get("items", [])))
                + " ítems identificados"
            )
            st.write(
                "- Validación: " + ("ok" if not resultado_diag.get("errores") else "con errores")
            )
            st.write(
                "- Cálculo: subtotal="
                + str(resultado_diag.get("subtotal", "-"))
                + ", total="
                + str(resultado_diag.get("total", "-"))
            )
            st.write("- Confirmación: " + str(resultado_diag.get("estado")))
            st.write(
                "- Registro: no ejecutado (pendiente de confirmación explícita del cliente)"
            )
    else:
        st.info("Ejecute los siete agentes para ver el diagnóstico aquí.")

st.divider()
st.caption(
    "Registro mantenido en simulacion (REGISTRAR_PEDIDOS no activo). "
    "Credenciales por variables de entorno. Audio temporal borrado tras transcribir. "
    "Los estados de agentes reflejan la ejecucion real del pipeline."
)
