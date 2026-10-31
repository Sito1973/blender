"""Genera la voz (narración) y los efectos de sonido del video con ElevenLabs.

Lee la clave de la variable de entorno `eleven_labs_api_key` (o ELEVENLABS_API_KEY).
Guarda los mp3 en public/audio/ y un resumen con duraciones en public/audio/audio.json.
Uso:  python3 scripts/generar_audio.py [voz|efectos|todo]
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

KEY = os.environ.get("eleven_labs_api_key") or os.environ.get("ELEVENLABS_API_KEY")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "audio")
VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # "Adam", voz predeterminada de ElevenLabs
MODEL = "eleven_multilingual_v2"

# (archivo, inicio en segundos, duración máxima, texto)
VOZ = [
    ("v01", 0.3, 4.6, "Así se hace la varilla de la lámpara roseta, paso a paso."),
    ("v02", 5.3, 3.6, "La lámpara tiene cuarenta y ocho curvas..."),
    ("v03", 9.0, 3.8, "y todas son la misma pieza."),
    ("v04", 13.2, 7.4, "Es un arco plano de varilla de seis milímetros, con un radio de doscientos ochenta y seis milímetros."),
    ("v05", 21.3, 5.6, "Paso uno: corta cuarenta y ocho tramos de seiscientos milímetros."),
    ("v06", 27.3, 6.8, "Paso dos: con un clavo y un cordel de doscientos ochenta y seis, traza el arco."),
    ("v07", 34.3, 6.6, "Paso tres: corta una horma un poco más cerrada, porque el acero se abre al soltarlo."),
    ("v08", 41.2, 4.5, "Paso cuatro: prensa la punta y dobla de a poco contra la horma."),
    ("v09", 45.8, 3.0, "Al soltarla, queda justo en el trazo."),
    ("v10", 48.9, 5.2, "Paso cinco: recorta las puntas y revisa que quede plana."),
    ("v11", 54.3, 5.4, "Repite la misma curva cuarenta y ocho veces, y arma tu lámpara."),
]

# (archivo, duración en segundos, descripción)
EFECTOS = [
    ("sfx_whoosh", 1.6, "Soft cinematic whoosh rising, a metal rod lifting into the air, clean, no music"),
    ("sfx_cortes", 3.0, "Angle grinder cutting a thin steel rod several times in quick short bursts, workshop, close up"),
    ("sfx_lapiz", 3.8, "Pencil drawing one long smooth curved line on a wooden board, close up, quiet room"),
    ("sfx_sierra", 2.6, "Electric jigsaw cutting a curve through an MDF wood board, close up"),
    ("sfx_doblar", 3.4, "Steel rod being slowly bent by hand around a wooden form, metallic creaking strain, close up"),
    ("sfx_soltar", 1.0, "Short metallic spring twang as a bent steel rod is released from a clamp"),
    ("sfx_check", 0.6, "Soft short positive confirmation ding, clean user interface sound"),
    ("sfx_armar", 3.8, "Light metal rods clinking and tapping into place while assembling a metal lamp frame, gentle, workshop"),
]


def post(url, payload, dest):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"xi-api-key": KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    for intento in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
                cost = r.headers.get("character-cost")
            with open(dest, "wb") as f:
                f.write(data)
            return cost
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:300]
            if e.code in (429, 500, 502, 503) and intento < 3:
                time.sleep(2 ** (intento + 1))
                continue
            raise SystemExit(f"ElevenLabs respondió {e.code}: {msg}")


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def voz(resumen, solo=None):
    textos = [t for *_, t in VOZ]
    previas = {x["archivo"]: x for x in resumen.get("voz", [])}
    resumen["voz"] = []
    for i, (name, start, maxd, text) in enumerate(VOZ):
        dest = os.path.join(OUT, name + ".mp3")
        prev = previas.get(f"audio/{name}.mp3")
        if solo and name not in solo and prev and os.path.exists(dest):
            prev.update({"inicio": start, "max": maxd})
            resumen["voz"].append(prev)
            continue
        speed = 1.0
        for _ in range(3):
            cost = post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128", {
                "text": text, "model_id": MODEL,
                "previous_text": textos[i - 1] if i else None,
                "next_text": textos[i + 1] if i + 1 < len(textos) else None,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.15, "use_speaker_boost": True, "speed": speed},
            }, dest)
            d = dur(dest)
            if d <= maxd or speed >= 1.15:
                break
            speed = min(1.15, round(speed * d / maxd + 0.02, 2))
        resumen["voz"].append({"archivo": f"audio/{name}.mp3", "inicio": start, "duracion": round(d, 2), "max": maxd, "velocidad": speed, "texto": text})
        print(f"{name}: {d:.2f}s (máx {maxd}) velocidad {speed} caracteres {cost}")


def efectos(resumen):
    for name, d, text in EFECTOS:
        dest = os.path.join(OUT, name + ".mp3")
        post("https://api.elevenlabs.io/v1/sound-generation", {"text": text, "duration_seconds": d, "prompt_influence": 0.55}, dest)
        resumen["efectos"].append({"archivo": f"audio/{name}.mp3", "duracion": round(dur(dest), 2), "descripcion": text})
        print(f"{name}: {dur(dest):.2f}s")


if __name__ == "__main__":
    if not KEY:
        raise SystemExit("Falta la variable de entorno eleven_labs_api_key")
    os.makedirs(OUT, exist_ok=True)
    que = sys.argv[1] if len(sys.argv) > 1 else "todo"
    path = os.path.join(OUT, "audio.json")
    resumen = json.load(open(path)) if os.path.exists(path) else {"voz": [], "efectos": []}
    if que in ("voz", "todo"):
        voz(resumen, set(sys.argv[2:]) or None)
    if que in ("efectos", "todo"):
        resumen["efectos"] = []
        efectos(resumen)
    resumen["voz_id"] = VOICE_ID
    resumen["modelo"] = MODEL
    json.dump(resumen, open(path, "w"), ensure_ascii=False, indent=2)
