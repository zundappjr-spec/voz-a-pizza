import json
import sys
import os

sys.path.insert(0, r"C:\Voz a texto\agentes")
sys.path.insert(0, r"C:\Voz a texto")

import imageio_ffmpeg as i
os.environ["PATH"] = os.path.dirname(i.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

from contexto import nuevo_contexto, hay_errores, estado
from agente_receptor import run as run_receptor
from agente_transcripcion import run as run_transcripcion
from agente_interpretacion import run as run_interpretacion
from agente_validacion import run as run_validacion
from agente_calculo import run as run_calculo
from agente_confirmacion import run as run_confirmacion
from agente_registro import run as run_registro

with open(r"C:\Voz a texto\tests_audio\evento_transcripcion_real.json", "r", encoding="utf-8") as f:
    evento = json.load(f)

ctx = nuevo_contexto("comercio-demo", evento)

agentes = [
    ("1. RECEPTOR", run_receptor, {}),
    ("2. TRANSCRIPCION", run_transcripcion, {}),
    ("3. INTERPRETACION", run_interpretacion, {}),
    ("4. VALIDACION", run_validacion, {}),
    ("5. CALCULO", run_calculo, {}),
    ("6. CONFIRMACION", run_confirmacion, {"numero_cliente": None, "confirmacion": None}),
]

for nombre, fn, kwargs in agentes:
    print(f"\n{'='*70}")
    print(f"{nombre}")
    print(f"{'='*70}")
    ctx = fn(ctx, **kwargs)
    print(json.dumps(ctx, ensure_ascii=False, indent=2))
    if hay_errores(ctx) and ctx["estado"] in ("rejected",):
        print("\n>>> Pipeline detenido por error en", nombre)
        break
    st = estado(ctx)
    print(f"\n>>> Estado tras {nombre}: {st}")

print(f"\n{'='*70}")
print("ESTADO FINAL")
print(f"{'='*70}")
print(json.dumps(ctx, ensure_ascii=False, indent=2))
