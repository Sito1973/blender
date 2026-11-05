"""
Arma web/index.html (la página publicada en roseta.cocinandosonrisas.co) a partir de
disenador_roseta.html, que es la misma página que se publica como artefacto en Claude.

El artefacto no lleva <!doctype>, <head> ni <body> porque Claude los agrega al publicar;
aquí se agregan con el mismo reinicio de estilos, una descripción y un ícono.

Uso:  python3 construir.py
"""
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(AQUI, "disenador_roseta.html"), encoding="utf-8").read()
cut = src.index('<div class="app">')
cabeza = src[:cut].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
cuerpo = src[cut:]
icono = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='13' fill='none' "
         "stroke='%23bf9455' stroke-width='3'/%3E%3Cpath d='M16 3v26M3 16h26M6.8 6.8l18.4 18.4M25.2 6.8 6.8 25.2' stroke='%23bf9455' "
         "stroke-width='1.6'/%3E%3Ccircle cx='16' cy='16' r='4' fill='%23855818'/%3E%3C/svg%3E")
doc = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       '<meta name="description" content="Diseñador de la lámpara roseta en varilla de 1/4&quot;: modelo 3D, plantillas 1:1, '
       'corte láser del aro y del disco, y compra de varilla.">\n'
       f'<link rel="icon" href="{icono}">\n'
       '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}'
       'body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style>\n'
       + cabeza + "</head>\n<body>\n" + cuerpo + "</body>\n</html>\n")
open(os.path.join(AQUI, "index.html"), "w", encoding="utf-8").write(doc)
print("index.html:", len(doc.encode("utf-8")), "bytes")
