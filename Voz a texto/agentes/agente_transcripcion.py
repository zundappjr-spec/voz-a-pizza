"""Agente 2 - TRANSCRIPCION (agente_transcripcion).

Descarga el audio de WhatsApp (componente autorizado, legado por URL) o
transcribe un archivo de audio local subido desde la interfaz web mediante
faster-whisper (modelo small, espanol, CPU, int8). Borra el audio temporal
luego de transcribir (politica de datos).

Contratos reutilizados:
- agentes.transcriptor.transcribir(ruta_audio)  -> texto real (faster-whisper)
- orchestrator.descargar_audio(mensaje_id, audio_url)  -> legado por URL
- orchestrator.transcribir_audio(ruta_audio, idioma)  -> legado simulado por URL
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from _paths import _ORCH  # noqa: E402

if _ORCH not in sys.path:
    sys.path.insert(0, _ORCH)

from transcriptor import transcribir, extension_valida  # noqa: E402
from contexto import estado  # noqa: E402
from orchestrator import descargar_audio, transcribir_audio  # noqa: E402


def run(ctx: Dict[str, Any]) -> Dict[str, Any]:
    if ctx.get("transcript"):
        ctx["estado"] = "transcribed"
        return ctx

    audio_path = ctx.get("audio_path")
    audio_url = ctx.get("audio_url")
    message_id = ctx.get("message_id")

    # 1. Archivo local subido desde la interfaz web (transcripcion real).
    if audio_path and os.path.exists(audio_path):
        if not extension_valida(audio_path):
            ctx["estado"] = "rejected"
            ctx["errores"].append(
                f"Extension de audio no soportada: {audio_path}. "
                "Usa MP3, WAV u OGG."
            )
            return ctx
        try:
            transcript = transcribir(audio_path)
            ctx["transcript"] = transcript
            ctx["estado"] = "transcribed"
            # Politica de datos: borrar audio temporal tras transcribir.
            try:
                os.remove(audio_path)
            except OSError:
                pass
        except Exception as exc:  # noqa: BLE001
            ctx["estado"] = "rejected"
            ctx["errores"].append(f"Fallo al transcribir el audio: {exc}")
        return ctx

    # 2. Legado: audio por URL de WhatsApp Business Platform.
    if audio_url:
        if not message_id:
            ctx["estado"] = "rejected"
            ctx["errores"].append("message_id ausente para descargar el audio")
            return ctx
        try:
            ruta_audio = descargar_audio(str(message_id), audio_url)
            transcript = transcribir_audio(ruta_audio)
            try:
                os.remove(ruta_audio)
            except OSError:
                pass
            ctx["transcript"] = transcript
            ctx["estado"] = "transcribed"
        except Exception as exc:  # noqa: BLE001
            ctx["estado"] = "rejected"
            ctx["errores"].append(f"Fallo al descargar o transcribir audio: {exc}")
        return ctx

    # 3. Sin audio ni transcripcion.
    ctx["estado"] = "requires_clarification"
    ctx["errores"].append("No se encontro audio ni transcripcion en el evento")
    return ctx


def main() -> int:
    import json

    if len(sys.argv) < 2:
        print("Uso: python agente_transcripcion.py <contexto.json>")
        return 2
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        ctx = json.load(f)
    resultado = run(ctx)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
