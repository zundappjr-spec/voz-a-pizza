"""Transcriptor de audio local con faster-whisper.

Motor: faster-whisper
Modelo: small
Idioma: espanol
Dispositivo: CPU
compute_type: int8
Ejecucion local, sin APIs externas de transcripcion.

El modelo se descarga en la primera ejecucion y se reutiliza desde la cache
local (carpeta modelos/whisper).
"""

from __future__ import annotations

import os
from functools import lru_cache

MODELO = "small"
IDIOMA = "es"
DISPOSITIVO = "cpu"
COMPUTE_TYPE = "int8"

_ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg"}

_BASE = os.path.dirname(os.path.abspath(__file__))
_CACHEDIR = os.path.abspath(os.path.join(_BASE, "..", "modelos", "whisper"))


def extension_valida(nombre_archivo: str) -> bool:
    return os.path.splitext(nombre_archivo or "")[1].lower() in _ALLOWED_EXTENSIONS


@lru_cache(maxsize=1)
def _cargar_modelo():
    from faster_whisper import WhisperModel

    os.makedirs(_CACHEDIR, exist_ok=True)
    return WhisperModel(
        MODELO,
        device=DISPOSITIVO,
        compute_type=COMPUTE_TYPE,
        download_root=_CACHEDIR,
        local_files_only=False,
    )


def transcribir(ruta_audio: str, idioma: str = IDIOMA) -> str:
    """Transcribe un archivo de audio local y devuelve el texto reconocido."""
    modelo = _cargar_modelo()
    segmentos, _info = modelo.transcribe(
        ruta_audio,
        language=idioma,
        vad_filter=True,
    )
    texto = "".join(seg.text for seg in segmentos).strip()
    return texto
