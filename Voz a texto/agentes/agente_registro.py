"""Agente 7 - REGISTRO (agente_registro).

Registra el pedido confirmado mediante el unico componente autorizado.
Opera en modo simulacion por defecto (REGISTRAR_PEDIDOS=1 para registro real).
Genera la clave independiente del pedido (distinta del message_id) y anonimiza
los datos antes de loguear.

Contratos reutilizados:
- registrar_pedido.registrar_pedido(pedido, commerce_id, registrar)
- registrar_pedido.generar_clave_pedido(commerce_id, pedido)
- anonimizar.anonimizar_para_log(registro)
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from _paths import _SCRIPTS  # noqa: E402

if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from registrar_pedido import registrar_pedido, generar_clave_pedido  # noqa: E402
from anonimizar import anonimizar_para_log  # noqa: E402
from contexto import hay_errores  # noqa: E402


def run(ctx: Dict[str, Any], registrar: bool | None = None) -> Dict[str, Any]:
    if registrar is None:
        registrar = os.environ.get("REGISTRAR_PEDIDOS", "0").lower() in (
            "1",
            "true",
            "yes",
        )

    pedido = ctx.get("pedido", {})
    comercio = ctx.get("commerce_id") or "comercio"

    if not pedido:
        ctx["estado"] = "rejected"
        ctx["errores"].append("No hay pedido validado para registrar")
        return ctx

    clave_pedido = generar_clave_pedido(comercio, pedido)
    registro = registrar_pedido(pedido, comercio, registrar=registrar)

    ctx["clave_pedido"] = clave_pedido
    ctx["registro"] = registro
    ctx["simulacion"] = not registrar

    estado_registro = registro.get("estado", "borrador")
    if estado_registro == "registrado":
        ctx["estado"] = "registered"
    elif estado_registro == "borrador":
        ctx["estado"] = "borrador"
    else:
        ctx["estado"] = "error"
        ctx["errores"].append(registro.get("mensaje", "Fallo al registrar el pedido"))

    # Log anonimizado (politica de datos): nunca credenciales ni datos de pago.
    # Se escribe a stderr para no contaminar el JSON de salida del pipeline.
    try:
        print(
            json.dumps(
                anonimizar_para_log(
                    {
                        "clave_pedido": clave_pedido,
                        "pedido": pedido,
                        "registro": registro,
                        "commerce_id": comercio,
                    }
                ),
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
    except Exception:  # noqa: BLE001
        pass

    return ctx


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python agente_registro.py <contexto.json> [--registrar]")
        return 2
    import json

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        ctx = json.load(f)
    registrar = "--registrar" in sys.argv
    resultado = run(ctx, registrar=registrar)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if not hay_errores(resultado) else 1


if __name__ == "__main__":
    sys.exit(main())
