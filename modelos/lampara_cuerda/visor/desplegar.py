#!/usr/bin/env python3
"""Publica el visor 3D de la lámpara en Easypanel.

El servicio es un nginx con tres archivos montados (index.html, muestras.js
con las fotos de las cuerdas y la configuración de nginx), igual que el
diseñador "roseta". Si el servicio no
existe lo crea con su dominio; si ya existe, actualiza los archivos y lo
vuelve a desplegar.

Uso:
    EASYPANEL_TOKEN=<token de Easypanel> python3 desplegar.py

Variables opcionales:
    EASYPANEL_URL       (por defecto https://easypaneln.cocinandosonrisas.co)
    EASYPANEL_PROYECTO  (por defecto cocson)
    EASYPANEL_SERVICIO  (por defecto lampara)
    VISOR_DOMINIO       (por defecto lampara.cocinandosonrisas.co)
"""

import json
import os
import secrets
import string
import sys
import urllib.error
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
URL = os.environ.get("EASYPANEL_URL", "https://easypaneln.cocinandosonrisas.co").rstrip("/")
TOKEN = os.environ.get("EASYPANEL_TOKEN", "")
PROYECTO = os.environ.get("EASYPANEL_PROYECTO", "cocson")
SERVICIO = os.environ.get("EASYPANEL_SERVICIO", "lampara")
DOMINIO = os.environ.get("VISOR_DOMINIO", "lampara.cocinandosonrisas.co")
IMAGEN = "nginx:1.27-alpine"

ARCHIVOS = [
    ("/usr/share/nginx/html/index.html", AQUI / "index.html"),
    ("/usr/share/nginx/html/muestras.js", AQUI / "muestras.js"),
    ("/etc/nginx/conf.d/default.conf", AQUI / "nginx.conf"),
]


class ErrorApi(Exception):
    pass


def api(procedimiento, datos):
    req = urllib.request.Request(
        f"{URL}/api/trpc/{procedimiento}",
        data=json.dumps({"json": datos}).encode("utf-8"),
        method="POST",
        # Cloudflare (delante del panel) rechaza el agente por defecto de Python.
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "desplegar-visor-lampara/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            cuerpo = json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", errors="replace")[:500]
        raise ErrorApi(f"{procedimiento}: HTTP {e.code} {detalle}") from None
    return cuerpo.get("json")


def nuevo_id():
    letras = string.ascii_lowercase + string.digits
    return "c" + "".join(secrets.choice(letras) for _ in range(24))


def main():
    if not TOKEN:
        sys.exit("Falta EASYPANEL_TOKEN (Easypanel > Settings > API).")
    base = {"projectName": PROYECTO, "serviceName": SERVICIO}
    montajes = [
        {"type": "file", "mountPath": ruta, "content": archivo.read_text(encoding="utf-8")}
        for ruta, archivo in ARCHIVOS
    ]

    try:
        api("services.app.inspectService", base)
        existe = True
    except ErrorApi as e:
        if "NOT_FOUND" not in str(e) and "404" not in str(e):
            raise
        existe = False

    if not existe:
        api("services.app.createService", {
            **base,
            "source": {"type": "image", "image": IMAGEN},
            "mounts": montajes,
            "domains": [{"host": DOMINIO, "https": True, "port": 80, "path": "/"}],
        })
        print(f"Servicio {PROYECTO}/{SERVICIO} creado.")
    else:
        actuales = api("mounts.listMounts", base) or []
        for m in montajes:
            indice = next((i for i, x in enumerate(actuales) if x.get("mountPath") == m["mountPath"]), None)
            if indice is None:
                api("mounts.createMount", {**base, "values": m})
            else:
                api("mounts.updateMount", {**base, "index": indice, "values": m})
        api("services.app.updateSourceImage", {**base, "image": IMAGEN})
        dominios = api("domains.listDomains", base) or []
        if not any(d.get("host") == DOMINIO for d in dominios):
            api("domains.createDomain", {
                "id": nuevo_id(), "host": DOMINIO, "https": True, "path": "/",
                "wildcard": False, "middlewares": [], "certificateResolver": "",
                "destinationType": "service",
                "serviceDestination": {"protocol": "http", "port": 80, "path": "/", **base},
            })
        print(f"Servicio {PROYECTO}/{SERVICIO} actualizado.")

    api("services.app.deployService", base)
    print("Despliegue enviado. Dominios:")
    for d in api("domains.listDomains", base) or []:
        print(f"  https://{d['host']}")


if __name__ == "__main__":
    main()
