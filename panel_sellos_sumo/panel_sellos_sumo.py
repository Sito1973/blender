"""
Paneles con los SELLOS DE SUMO en relieve para CORTE LÁSER (2 capas de madera/MDF).

Cada panel lleva un sello grande: la línea del sello se corta en una capa y se
encola sobre una base cuadrada lisa. La base trae el contorno del sello marcado
(azul) como guía para pegar cada pieza en su sitio.

Cómo usarlo
-----------
  * Por consola:        blender --background --python panel_sellos_sumo.py
  * Dentro de Blender:  pestaña "Scripting" > Abrir este archivo > Ejecutar (Alt+P).

El arte de los sellos está en `sellos_sumo.json` (en esta misma carpeta). El .blend
guarda una copia, así que el script también funciona con el .blend solo.

Qué genera
----------
  corte/sello_NN_relieve.svg|dxf  -> lo que corta el láser (la línea del sello)
  corte/sello_NN_base.svg|dxf     -> cuadrado de la base + marca guía para pegar
  planos/plano_sellos.svg         -> los 12 sellos, medidas y lista de piezas
  panel_sellos_sumo.blend         -> modelo 3D (solo por consola)
  renders/*.png                   -> vistas previas (solo por consola)

Todas las medidas de los PARÁMETROS están en milímetros.
"""

import json
import math
import os
import re

try:
    import bpy
    from mathutils import Vector
except ImportError:  # permite generar SVG/DXF sin Blender
    bpy = None

# ───────────────────────────── PARÁMETROS (mm) ─────────────────────────────
MODO = "GENERAR"          # "GENERAR" crea todo de cero · "EXPORTAR" solo reexporta la escena

LADO = 400.0              # lado del panel cuadrado
DIAMETRO = 350.0          # diámetro del sello sobre el panel
ESPESOR_BASE = 9.0        # capa 1 (cuadrado liso)
ESPESOR_RELIEVE = 9.0     # capa 2 (línea del sello)
MATERIAL = "MDF"          # solo para rotular el plano
SELLOS = None             # cuáles generar, p. ej. [2, 6, 12] · None = todos los del archivo
MARCA_EN_BASE = True      # dibuja en la base el contorno del sello (azul) como guía de pegado
PIEZA_MIN_PCT = 0.057     # motas menores que este % del área del sello se descartan (no se pueden pegar)
HUECO_MIN_PCT = 0.014     # agujeros menores que este % del área del sello se descartan

COLUMNAS = 5              # disposición de los paneles en la escena de Blender
SEPARACION = 40.0
RENDERIZAR = True         # solo se aplica al ejecutar por consola (--background)
MUESTRAS_RENDER = 48

E = 0.001                 # mm -> unidades de Blender (metros)
PREFIJO = "Sello_"
ARCHIVO_ARTE = "sellos_sumo.json"


# ───────────────────────────── CARPETA DE TRABAJO ─────────────────────────────
def _carpeta():
    if bpy and bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath)
    aqui = globals().get("__file__", "")
    if aqui and os.path.isfile(aqui):
        return os.path.dirname(os.path.abspath(aqui))
    raise RuntimeError("Guarda primero el .blend: los archivos se escriben en su misma carpeta.")


# ───────────────────────────── TRAZADOS Y ARCHIVOS DE CORTE ─────────────────────────────
# Un trazado es dict(capa, tipo "CORTE"/"GRABADO", cerrado, nudos=[(asa_izq, punto, asa_der)]), en mm.
def _segmentos(tr):
    """Segmentos cúbicos (p0, c1, c2, p1) de un trazado."""
    n = tr["nudos"]
    pares = list(zip(n, n[1:])) + ([(n[-1], n[0])] if tr["cerrado"] else [])
    return [(a[1], a[2], b[0], b[1]) for a, b in pares]


def _es_recto(seg):
    p0, c1, c2, p1 = seg
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    largo = math.hypot(dx, dy) or 1.0
    return all(abs((c[0] - p0[0]) * dy - (c[1] - p0[1]) * dx) / largo < 1e-4 for c in (c1, c2))


def _polilinea(tr, pasos=8):
    """Convierte el trazado a puntos (para DXF y para medir)."""
    pts = [tr["nudos"][0][1]]
    for seg in _segmentos(tr):
        p0, c1, c2, p1 = seg
        if _es_recto(seg):
            pts.append(p1)
            continue
        for i in range(1, pasos + 1):
            t = i / pasos
            a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
            pts.append((a * p0[0] + b * c1[0] + c * c2[0] + d * p1[0],
                        a * p0[1] + b * c1[1] + c * c2[1] + d * p1[1]))
    if tr["cerrado"]:
        pts.pop()                             # el último repite al primero
    return pts


def _area_caja(tr):
    xs = [n[1][0] for n in tr["nudos"]]
    ys = [n[1][1] for n in tr["nudos"]]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def _ordenar(trazados):
    """Orden de trabajo del láser: grabado, cortes interiores y contorno al final."""
    grab = [t for t in trazados if t["tipo"] == "GRABADO"]
    corte = sorted((t for t in trazados if t["tipo"] == "CORTE"), key=_area_caja)
    return grab, corte


def _d_svg(tr, alto, escala=1.0, dx=0.0, dy=0.0):
    def c(p):
        return f"{dx + p[0] * escala:.3f},{dy + (alto - p[1]) * escala:.3f}"
    d = ["M" + c(tr["nudos"][0][1])]
    for seg in _segmentos(tr):
        d.append("L" + c(seg[3]) if _es_recto(seg) else f"C{c(seg[1])} {c(seg[2])} {c(seg[3])}")
    return " ".join(d) + (" Z" if tr["cerrado"] else "")


def escribir_svg(ruta, trazados, titulo):
    """SVG a escala 1:1 en mm. Rojo = cortar, azul = grabar línea."""
    grab, corte = _ordenar(trazados)
    s = [f'<?xml version="1.0" encoding="UTF-8"?>',
         f'<svg xmlns="http://www.w3.org/2000/svg" '
         f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
         f'width="{LADO:g}mm" height="{LADO:g}mm" viewBox="0 0 {LADO:g} {LADO:g}">',
         f'<title>{titulo}</title>']
    for nombre, color, grupo in (("GRABADO", "#0000ff", grab), ("CORTE", "#ff0000", corte)):
        if grupo:
            s.append(f'<g id="{nombre}" inkscape:groupmode="layer" inkscape:label="{nombre}" '
                     f'fill="none" stroke="{color}" stroke-width="0.1">')
            s += [f'<path d="{_d_svg(t, LADO)}"/>' for t in grupo]
            s.append('</g>')
    s.append('</svg>')
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(s) + "\n")


def escribir_dxf(ruta, trazados):
    """DXF R12 (el más compatible) en mm. Capas CORTE (rojo) y GRABADO (azul)."""
    grab, corte = _ordenar(trazados)
    o = ["0", "SECTION", "2", "HEADER",
         "9", "$ACADVER", "1", "AC1009",
         "9", "$INSUNITS", "70", "4",
         "9", "$EXTMIN", "10", "0.0", "20", "0.0", "30", "0.0",
         "9", "$EXTMAX", "10", f"{LADO:.4f}", "20", f"{LADO:.4f}", "30", "0.0",
         "0", "ENDSEC",
         "0", "SECTION", "2", "TABLES",
         "0", "TABLE", "2", "LTYPE", "70", "1",
         "0", "LTYPE", "2", "CONTINUOUS", "70", "0", "3", "Solid line", "72", "65", "73", "0", "40", "0.0",
         "0", "ENDTAB",
         "0", "TABLE", "2", "LAYER", "70", "2",
         "0", "LAYER", "2", "CORTE", "70", "0", "62", "1", "6", "CONTINUOUS",
         "0", "LAYER", "2", "GRABADO", "70", "0", "62", "5", "6", "CONTINUOUS",
         "0", "ENDTAB", "0", "ENDSEC",
         "0", "SECTION", "2", "ENTITIES"]
    for capa, grupo in (("GRABADO", grab), ("CORTE", corte)):
        for t in grupo:
            o += ["0", "POLYLINE", "8", capa, "66", "1", "70", "1" if t["cerrado"] else "0",
                  "10", "0.0", "20", "0.0", "30", "0.0"]
            for x, y in _polilinea(t):
                o += ["0", "VERTEX", "8", capa, "10", f"{x:.4f}", "20", f"{y:.4f}", "30", "0.0"]
            o += ["0", "SEQEND", "8", capa]
    o += ["0", "ENDSEC", "0", "EOF"]
    with open(ruta, "w", encoding="ascii") as f:
        f.write("\n".join(o) + "\n")


# ───────────────────────────── GEOMETRÍA DE LOS SELLOS ─────────────────────────────
def _subtrazos(d):
    """Convierte un trazado SVG (órdenes M, L, C y Z absolutas) en contornos Bézier.

    Devuelve una lista de contornos; cada uno es [(asa_izq, punto, asa_der), …].
    """
    fichas = re.findall(r"[MCLZ]|-?\d+\.?\d*", d)
    contornos, actual, i = [], None, 0
    while i < len(fichas):
        orden = fichas[i]
        i += 1
        n = {"M": 2, "L": 2, "C": 6, "Z": 0}[orden]
        v = [float(t) for t in fichas[i:i + n]]
        i += n
        if orden == "M":
            actual = [[None, (v[0], v[1]), None]]
            contornos.append(actual)
        elif orden == "L":
            a, b = actual[-1][1], (v[0], v[1])
            actual[-1][2] = (a[0] + (b[0] - a[0]) / 3, a[1] + (b[1] - a[1]) / 3)
            actual.append([(b[0] - (b[0] - a[0]) / 3, b[1] - (b[1] - a[1]) / 3), b, None])
        elif orden == "C":
            actual[-1][2] = (v[0], v[1])
            actual.append([(v[2], v[3]), (v[4], v[5]), None])
    for c in contornos:                        # cierre del contorno
        a, b = c[0][1], c[-1][1]
        if len(c) > 1 and math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-3:
            c[0][0] = c[-1][0]                 # el último punto repite al primero: se funden
            c.pop()
        else:                                  # se cierra con un tramo recto
            c[0][0] = (a[0] + (b[0] - a[0]) / 3, a[1] + (b[1] - a[1]) / 3)
            c[-1][2] = (b[0] + (a[0] - b[0]) / 3, b[1] + (a[1] - b[1]) / 3)
    return [[tuple(nudo) for nudo in c] for c in contornos]


def _area(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def _dentro(p, pts):
    x, y = p
    dentro = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            dentro = not dentro
    return dentro


def trazados_sello(d):
    """Trazados de un panel (mm, origen en la esquina inferior izquierda) y su resumen."""
    k = DIAMETRO / 100.0

    def mm(p):                                 # del arte (Ø100, Y hacia abajo) al panel
        return (LADO / 2 + (p[0] - 50.0) * k, LADO / 2 + (50.0 - p[1]) * k)

    contornos = []
    for c in _subtrazos(d):
        nudos = [(mm(hi), mm(p), mm(hd)) for hi, p, hd in c]
        pts = _polilinea(dict(cerrado=True, nudos=nudos))
        contornos.append(dict(nudos=nudos, pts=pts, area=_area(pts)))
    for c in contornos:                        # profundidad par = pieza · impar = hueco
        c["prof"] = sum(_dentro(c["pts"][0], o["pts"]) for o in contornos if o is not c)
    disco = math.pi * (DIAMETRO / 2) ** 2      # los umbrales van en % para que no dependan del tamaño
    buenos = [c for c in contornos
              if c["area"] >= disco * (PIEZA_MIN_PCT if c["prof"] % 2 == 0 else HUECO_MIN_PCT) / 100]
    piezas = sum(1 for c in buenos if c["prof"] % 2 == 0)
    cuadrado = [(p, p, p) for p in ((0, 0), (LADO, 0), (LADO, LADO), (0, LADO))]
    trazados = [dict(capa=1, tipo="CORTE", cerrado=True, nudos=cuadrado)]
    for c in buenos:
        if MARCA_EN_BASE:
            trazados.append(dict(capa=1, tipo="GRABADO", cerrado=True, nudos=c["nudos"]))
        trazados.append(dict(capa=2, tipo="CORTE", cerrado=True, nudos=c["nudos"]))
    return trazados, dict(piezas=piezas, huecos=len(buenos) - piezas,
                          descartados=len(contornos) - len(buenos))


def generar_todo(carpeta):
    ruta = os.path.join(carpeta, ARCHIVO_ARTE)
    if os.path.isfile(ruta):
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    elif bpy and ARCHIVO_ARTE in bpy.data.texts:      # copia guardada dentro del .blend
        datos = json.loads(bpy.data.texts[ARCHIVO_ARTE].as_string())
    else:
        raise RuntimeError(f"No encuentro {ARCHIVO_ARTE} junto al .blend ni dentro de él.")
    arte = {s["n"]: s for s in datos["sellos"]}
    paneles = {}
    for n in SELLOS or sorted(arte):
        trazados, info = trazados_sello(arte[n]["d"])
        info["nombre"] = arte[n].get("nombre", "")
        paneles[n] = (trazados, info)
    return paneles


# ───────────────────────────── ARCHIVOS DE CORTE Y PLANO ─────────────────────────────
def exportar(paneles, carpeta):
    """`paneles` = {número: (trazados, resumen)}."""
    corte = os.path.join(carpeta, "corte")
    os.makedirs(corte, exist_ok=True)
    for viejo in os.listdir(corte):            # quita los archivos de sellos que ya no están
        m = re.fullmatch(r"sello_(\d+)_(base|relieve)\.(svg|dxf)", viejo)
        if m and int(m.group(1)) not in paneles:
            os.remove(os.path.join(corte, viejo))
    for n, (trazados, _) in sorted(paneles.items()):
        for capa, nombre in ((1, "base"), (2, "relieve")):
            tr = [t for t in trazados if t["capa"] == capa]
            base = os.path.join(corte, f"sello_{n:02d}_{nombre}")
            escribir_svg(base + ".svg", tr, f"Sello SUMO {n:02d} - {nombre}")
            escribir_dxf(base + ".dxf", tr)
    planos = os.path.join(carpeta, "planos")
    os.makedirs(planos, exist_ok=True)
    escribir_plano(os.path.join(planos, "plano_sellos.svg"), paneles)
    print(f"[sellos] {len(paneles)} paneles: archivos de corte y plano escritos en {carpeta}")


def escribir_plano(ruta, paneles):
    """Hoja A3 apaisada: catálogo de sellos, medidas de un panel y lista de piezas."""
    total = ESPESOR_BASE + ESPESOR_RELIEVE
    margen = (LADO - DIAMETRO) / 2
    tinta, gris, acento, madera, fondo = "#1f2a37", "#6b7280", "#b45309", "#4d4946", "#f6efe4"
    s = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297" '
         'font-family="Inter, Helvetica, Arial, sans-serif">',
         '<rect width="420" height="297" fill="#ffffff"/>',
         f'<rect x="8" y="8" width="404" height="281" fill="none" stroke="{tinta}" stroke-width="0.5"/>',
         f'<line x1="8" y1="28" x2="412" y2="28" stroke="{tinta}" stroke-width="0.5"/>',
         f'<text x="14" y="21.5" font-size="8" font-weight="700" fill="{tinta}">'
         f'PANELES DE SELLOS SUMO EN RELIEVE — PLANO PARA CORTE LÁSER</text>',
         f'<text x="406" y="18" font-size="4" fill="{gris}" text-anchor="end">Medidas en milímetros</text>',
         f'<text x="406" y="24" font-size="4" fill="{gris}" text-anchor="end">'
         f'Archivos de corte a escala 1:1</text>']

    def texto(x, y, txt, tam=4.0, color=tinta, peso="400", ancla="start", giro=None):
        g = f' transform="rotate({giro} {x} {y})"' if giro is not None else ""
        s.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{tam}" fill="{color}" '
                 f'font-weight="{peso}" text-anchor="{ancla}"{g}>{txt}</text>')

    def cota(x0, y0, x1, y1, txt, lado=1):
        """Cota horizontal o vertical con topes; `lado` decide a qué lado va el número."""
        if abs(y1 - y0) < 1e-6:
            s.append(f'<g stroke="{acento}" stroke-width="0.25"><line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}"/>'
                     f'<line x1="{x0}" y1="{y0 - 1.6}" x2="{x0}" y2="{y0 + 1.6}"/>'
                     f'<line x1="{x1}" y1="{y0 - 1.6}" x2="{x1}" y2="{y0 + 1.6}"/></g>')
            texto((x0 + x1) / 2, y0 + (5 if lado > 0 else -1.6), txt, 4.0, acento, "600", "middle")
        else:
            s.append(f'<g stroke="{acento}" stroke-width="0.25"><line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}"/>'
                     f'<line x1="{x0 - 1.6}" y1="{y0}" x2="{x0 + 1.6}" y2="{y0}"/>'
                     f'<line x1="{x0 - 1.6}" y1="{y1}" x2="{x0 + 1.6}" y2="{y1}"/></g>')
            if lado > 0:
                texto(x0 + 2.4, (y0 + y1) / 2 + 1.4, txt, 4.0, acento, "600")
            else:
                texto(x0 - 2, (y0 + y1) / 2, txt, 4.0, acento, "600", "middle", -90)

    def dibujar(trazados, x, y, lado_dib):
        """Panel a escala: base clara y sello relleno."""
        esc = lado_dib / LADO
        s.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{lado_dib}" height="{lado_dib}" fill="{fondo}" '
                 f'stroke="{tinta}" stroke-width="0.3"/>')
        d = " ".join(_d_svg(t, LADO, esc, x, y) for t in trazados if t["capa"] == 2)
        s.append(f'<path d="{d}" fill="{madera}" fill-rule="evenodd"/>')

    # Catálogo de sellos
    texto(14, 38, "SELLOS", 5.5, tinta, "700")
    texto(38, 38, "en oscuro, lo que queda en relieve · «+ n» = piezas pequeñas que se pegan aparte",
          3.6, gris)
    numeros = sorted(paneles)
    cols = 4 if len(numeros) > 6 else 3
    filas = max(1, math.ceil(len(numeros) / cols))
    paso_x = 248.0 / cols
    paso_y = min(80.0, 240.0 / filas)
    lado_dib = min(paso_x - 8.0, paso_y - 19.0)
    for i, n in enumerate(numeros):
        trazados, info = paneles[n]
        x = 14 + (i % cols) * paso_x + (paso_x - lado_dib) / 2 - 4
        y = 44 + (i // cols) * paso_y
        dibujar(trazados, x, y, lado_dib)
        sueltas = info["piezas"] - 1
        detalle = "1 pieza" if sueltas == 0 else f"1 pieza + {sueltas}"
        texto(x, y + lado_dib + 5.5, f"{n:02d}", 5.0, tinta, "700")
        texto(x + 8, y + lado_dib + 5.3, info.get("nombre", ""), 3.8, tinta, "600")
        texto(x + 8, y + lado_dib + 10.0, detalle, 3.5, gris)

    # Medidas de un panel
    xr = 276.0
    n0 = numeros[0]
    texto(xr, 38, "MEDIDAS DE CADA PANEL", 5.5, tinta, "700")
    lado_m = 72.0
    xm, ym = xr + 12, 46.0
    dibujar(paneles[n0][0], xm, ym, lado_m)
    esc = lado_m / LADO
    cota(xm, ym + lado_m + 4.5, xm + lado_m, ym + lado_m + 4.5, f"{LADO:g}")
    cota(xm - 5, ym, xm - 5, ym + lado_m, f"{LADO:g}", lado=-1)
    cota(xm + lado_m + 5, ym + margen * esc, xm + lado_m + 5, ym + (LADO - margen) * esc,
         f"Ø {DIAMETRO:g}")
    cota(xm + lado_m + 5, ym, xm + lado_m + 5, ym + margen * esc, f"{margen:g}")

    # Sección
    ys = 146.0
    texto(xr, ys - 5, "SECCIÓN", 5.5, tinta, "700")
    texto(xr + 27, ys - 5, "espesores dibujados ampliados", 3.6, gris)
    ep, ez = 112.0 / LADO, 0.9
    zb, zr = ESPESOR_BASE * ez, ESPESOR_RELIEVE * ez
    xs = xr + 8
    s.append(f'<rect x="{xs}" y="{ys + zr}" width="{LADO * ep}" height="{zb}" fill="#e3d3ba" '
             f'stroke="{tinta}" stroke-width="0.35"/>')
    cruces = sorted(v for t in paneles[n0][0] if t["capa"] == 2
                    for v in _cortes_horizontales(t, LADO / 2))
    for a, b in zip(cruces[0::2], cruces[1::2]):
        s.append(f'<rect x="{xs + a * ep:.2f}" y="{ys}" width="{(b - a) * ep:.2f}" height="{zr}" '
                 f'fill="{madera}" stroke="{tinta}" stroke-width="0.3"/>')
    cota(xs + LADO * ep + 4.5, ys, xs + LADO * ep + 4.5, ys + zr, f"{ESPESOR_RELIEVE:g}")
    cota(xs + LADO * ep + 4.5, ys + zr, xs + LADO * ep + 4.5, ys + zr + zb, f"{ESPESOR_BASE:g}")
    cota(xs - 4.5, ys, xs - 4.5, ys + zr + zb, f"{total:g}", lado=-1)

    # Lista de piezas
    yt = 184.0
    texto(xr, yt, "CADA PANEL LLEVA", 5.5, tinta, "700")
    filas_t = [("Pieza", "Medida (mm)", "Cant."),
               ("Capa 1 · base lisa", f"{LADO:g} × {LADO:g} × {ESPESOR_BASE:g}", "1"),
               ("Capa 2 · sello calado", f"Ø {DIAMETRO:g} × {ESPESOR_RELIEVE:g}", "1 juego")]
    for i, fila in enumerate(filas_t):
        y = yt + 8 + i * 7
        for cx, celda in zip((0, 58, 106), fila):
            texto(xr + cx, y, celda, 3.8, gris if i == 0 else tinta, "700" if i == 0 else "400")
        s.append(f'<line x1="{xr}" y1="{y + 2.2}" x2="{xr + 130}" y2="{y + 2.2}" '
                 f'stroke="#d1d5db" stroke-width="0.25"/>')
    notas = [f"Panel terminado: {LADO:g} × {LADO:g} × {total:g} mm.",
             "Archivos por sello: «relieve» y «base».",
             "Rojo = cortar.",
             "Azul (solo en la base) = marcar suave, sin cortar:",
             "es la guía para pegar cada pieza en su sitio.",
             f"Material sugerido: {MATERIAL} de {ESPESOR_RELIEVE:g} mm."]
    for i, nota in enumerate(notas):
        texto(xr, yt + 36 + i * 5.5, nota, 3.7, tinta)
    s.append("</svg>")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(s) + "\n")


def _cortes_horizontales(trazado, y):
    """Coordenadas x donde el contorno cruza la horizontal de altura y."""
    pts = _polilinea(trazado)
    return [x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])
            if (y0 <= y < y1) or (y1 <= y < y0)]


# ───────────────────────────── BLENDER ─────────────────────────────
def _material(nombre, color, rugosidad=0.7, canto=None):
    """Material sencillo. Con `canto`, las caras laterales (el corte del láser,
    que queda tostado) toman ese color."""
    mat = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    if mat.node_tree is None:
        mat.use_nodes = True
    nodos, enlaces = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next((n for n in nodos if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rugosidad
    if bsdf and canto and not nodos.get("Canto"):
        geo = nodos.new("ShaderNodeNewGeometry")
        xyz = nodos.new("ShaderNodeSeparateXYZ")
        absz = nodos.new("ShaderNodeMath")
        absz.operation = "ABSOLUTE"
        cara = nodos.new("ShaderNodeMath")
        cara.operation = "GREATER_THAN"
        cara.inputs[1].default_value = 0.5
        mezcla = nodos.new("ShaderNodeMix")
        mezcla.name = "Canto"
        mezcla.data_type = "RGBA"
        ent = {s.identifier: s for s in mezcla.inputs}
        sal = {s.identifier: s for s in mezcla.outputs}
        ent["A_Color"].default_value = (*canto, 1.0)
        ent["B_Color"].default_value = (*color, 1.0)
        enlaces.new(geo.outputs["Normal"], xyz.inputs[0])
        enlaces.new(xyz.outputs["Z"], absz.inputs[0])
        enlaces.new(absz.outputs[0], cara.inputs[0])
        enlaces.new(cara.outputs[0], ent["Factor_Float"])
        enlaces.new(sal["Result_Color"], bsdf.inputs["Base Color"])
    mat.diffuse_color = (*color, 1.0)
    return mat


def _coleccion(nombre):
    vieja = bpy.data.collections.get(nombre)
    if vieja:
        for ob in list(vieja.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(vieja)
    col = bpy.data.collections.new(nombre)
    bpy.context.scene.collection.children.link(col)
    return col


def _objeto_curva(nombre, trazados, col, capa, tipo, z, extrusion=0.0, bisel=0.0, mat=None):
    cu = bpy.data.curves.new(nombre, "CURVE")
    cu.dimensions = "3D" if bisel else "2D"
    cu.resolution_u = 6
    if not bisel:
        cu.fill_mode = "BOTH"
        cu.extrude = extrusion * E / 2.0
    else:
        cu.bevel_depth = bisel * E
        cu.bevel_resolution = 2
    for t in trazados:
        if all(hi == p == hd for hi, p, hd in t["nudos"]):
            sp = cu.splines.new("POLY")
            sp.points.add(len(t["nudos"]) - 1)
            for pt, (_, p, _) in zip(sp.points, t["nudos"]):
                pt.co = (p[0] * E, p[1] * E, 0.0, 1.0)
        else:
            sp = cu.splines.new("BEZIER")
            sp.bezier_points.add(len(t["nudos"]) - 1)
            for bp, (hi, p, hd) in zip(sp.bezier_points, t["nudos"]):
                bp.handle_left_type = bp.handle_right_type = "FREE"
                bp.co = (p[0] * E, p[1] * E, 0.0)
                bp.handle_left = (hi[0] * E, hi[1] * E, 0.0)
                bp.handle_right = (hd[0] * E, hd[1] * E, 0.0)
        sp.use_cyclic_u = t["cerrado"]
    ob = bpy.data.objects.new(nombre, cu)
    ob.location.z = z * E
    ob["capa"], ob["laser"] = capa, tipo
    if mat:
        cu.materials.append(mat)
    col.objects.link(ob)
    return ob


def _apuntar(ob, destino):
    ob.rotation_euler = (Vector(destino) - ob.location).to_track_quat("-Z", "Y").to_euler()


def _posicion(i):
    return ((i % COLUMNAS) * (LADO + SEPARACION), -(i // COLUMNAS) * (LADO + SEPARACION))


def construir_escena(paneles):
    """Un grupo por sello: base, marca guía y relieve, colgando de un vacío «Sello_NN»."""
    esc = bpy.context.scene
    esc.unit_settings.system = "METRIC"
    esc.unit_settings.length_unit = "MILLIMETERS"
    madera = _material("Madera", (0.52, 0.34, 0.19), canto=(0.07, 0.04, 0.025))
    col = _coleccion("Sellos SUMO (planos de corte)")
    for i, n in enumerate(sorted(paneles)):
        trazados, info = paneles[n]
        x, y = _posicion(i)
        padre = bpy.data.objects.new(f"{PREFIJO}{n:02d}", None)
        padre.empty_display_size = 0.05
        padre.location = (x * E, y * E, 0.0)
        padre["sello"], padre["nombre"] = n, info.get("nombre", "")
        col.objects.link(padre)

        def sel(capa, tipo):
            return [t for t in trazados if t["capa"] == capa and t["tipo"] == tipo]

        partes = [_objeto_curva(f"{PREFIJO}{n:02d}_Base", sel(1, "CORTE"), col, 1, "CORTE",
                                      ESPESOR_BASE / 2, ESPESOR_BASE, mat=madera),
                  _objeto_curva(f"{PREFIJO}{n:02d}_Relieve", sel(2, "CORTE"), col, 2, "CORTE",
                                      ESPESOR_BASE + ESPESOR_RELIEVE / 2, ESPESOR_RELIEVE, mat=madera)]
        if sel(1, "GRABADO"):
            marca = _objeto_curva(f"{PREFIJO}{n:02d}_Marca", sel(1, "GRABADO"), col, 1,
                                        "GRABADO", ESPESOR_BASE)
            marca.data.fill_mode = "NONE"      # solo líneas: no se ve en el render
            marca.hide_render = True
            partes.append(marca)
        for ob in partes:
            ob.data.resolution_u = 8
            ob.parent = padre
    bpy.context.view_layer.update()


def leer_escena():
    """Lee los trazados de cada sello desde las curvas de Blender (por si se editaron)."""
    bpy.context.view_layer.update()
    paneles = {}
    for padre in bpy.data.objects:
        if padre.type != "EMPTY" or "sello" not in padre:
            continue
        inv = padre.matrix_world.inverted()
        trazados = []
        for ob in padre.children:
            if ob.type != "CURVE" or "laser" not in ob:
                continue
            m = inv @ ob.matrix_world

            def mm(v, m=m):
                w = m @ Vector(v[:3])
                return (w.x / E, w.y / E)
            for sp in ob.data.splines:
                if sp.type == "BEZIER":
                    nudos = [(mm(b.handle_left), mm(b.co), mm(b.handle_right)) for b in sp.bezier_points]
                else:
                    nudos = [(mm(p.co),) * 3 for p in sp.points]
                trazados.append(dict(capa=int(ob["capa"]), tipo=ob["laser"],
                                     cerrado=sp.use_cyclic_u, nudos=nudos))
        relieve = [dict(pts=_polilinea(t)) for t in trazados if t["capa"] == 2]
        for c in relieve:
            c["prof"] = sum(_dentro(c["pts"][0], o["pts"]) for o in relieve if o is not c)
        piezas = sum(1 for c in relieve if c["prof"] % 2 == 0)
        paneles[int(padre["sello"])] = (trazados, dict(piezas=piezas, huecos=len(relieve) - piezas,
                                                       descartados=0, nombre=padre.get("nombre", "")))
    if not paneles:
        raise RuntimeError("No hay sellos en la escena. Ejecuta antes con MODO = 'GENERAR'.")
    return paneles


def renderizar(carpeta, cantidad):
    esc = bpy.context.scene
    salida = os.path.join(carpeta, "renders")
    os.makedirs(salida, exist_ok=True)
    esc.render.engine = "CYCLES"
    esc.cycles.device = "CPU"
    esc.cycles.samples = MUESTRAS_RENDER
    esc.cycles.use_denoising = True
    esc.render.image_settings.file_format = "PNG"
    mundo = esc.world or bpy.data.worlds.new("Mundo")
    esc.world = mundo
    if mundo.node_tree is None:
        mundo.use_nodes = True
    fondo = next((nodo for nodo in mundo.node_tree.nodes if nodo.type == "BACKGROUND"), None)
    if fondo:
        fondo.inputs["Color"].default_value = (1.0, 0.98, 0.95, 1.0)
        fondo.inputs["Strength"].default_value = 0.45

    col = _coleccion("Vista previa (luz y camaras)")
    malla = bpy.data.meshes.new("Pared")
    r = 6.0
    malla.from_pydata([(-r, -r, 0), (r, -r, 0), (r, r, 0), (-r, r, 0)], [], [(0, 1, 2, 3)])
    pared = bpy.data.objects.new("Pared", malla)
    pared.location.z = -0.0002
    malla.materials.append(_material("Pared", (0.86, 0.85, 0.83), 0.9))
    col.objects.link(pared)
    sol_d = bpy.data.lights.new("Sol", "SUN")
    sol_d.energy = 3.4
    sol_d.angle = math.radians(8)
    sol = bpy.data.objects.new("Sol", sol_d)           # luz rasante: marca el relieve
    sol.rotation_euler = Vector((0.80, -0.45, -0.42)).to_track_quat("-Z", "Y").to_euler()
    col.objects.link(sol)

    def camara(nombre, columnas, filas, col0=0, fila0=0):
        """Cámara en picado que encuadra un bloque de paneles."""
        ancho = (columnas * LADO + (columnas - 1) * SEPARACION) * E
        alto = (filas * LADO + (filas - 1) * SEPARACION) * E
        mx = col0 * (LADO + SEPARACION) * E + ancho / 2
        my = (LADO - fila0 * (LADO + SEPARACION)) * E - alto / 2
        lejos = max(ancho, 1.5 * alto)
        datos = bpy.data.cameras.new(nombre)
        datos.lens = 50
        cam = bpy.data.objects.new(nombre, datos)
        cam.location = (mx - 0.20 * lejos, my - 0.92 * lejos, 1.42 * lejos)
        _apuntar(cam, (mx + 0.005 * lejos, my - 0.01 * lejos, 0.0))
        col.objects.link(cam)
        return cam

    columnas = min(COLUMNAS, cantidad)
    filas = math.ceil(cantidad / COLUMNAS)
    tomas = [(camara("Camara_todos", columnas, filas), "vista_sellos.png", (2000, 1334))]
    if cantidad >= 3:
        tomas.append((camara("Camara_detalle", min(3, columnas), 1), "vista_detalle.png", (2000, 1000)))
    for cam, nombre, res in tomas:
        esc.camera = cam
        esc.render.resolution_x, esc.render.resolution_y = res
        esc.render.filepath = os.path.join(salida, nombre)
        bpy.ops.render.render(write_still=True)
        print(f"[sellos] Render: {esc.render.filepath}")
    esc.camera = tomas[0][0]


def main():
    carpeta = _carpeta()
    if bpy is None:                            # sin Blender: solo archivos de corte
        exportar(generar_todo(carpeta), carpeta)
        return
    if MODO.upper() == "EXPORTAR":
        exportar(leer_escena(), carpeta)
        return
    consola = bpy.app.background
    if consola:                                # escena nueva y limpia
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    paneles = generar_todo(carpeta)
    for n, (_, info) in sorted(paneles.items()):
        print(f"[sellos] {n:02d}: {info['piezas']} piezas, {info['huecos']} huecos, "
              f"{info['descartados']} motas descartadas")
    construir_escena(paneles)
    exportar(leer_escena(), carpeta)   # se exporta lo que hay en Blender
    if consola:
        if RENDERIZAR:
            renderizar(carpeta, len(paneles))
        ruta = os.path.join(carpeta, "panel_sellos_sumo.blend")
        aqui = globals().get("__file__", "")
        if aqui and os.path.isfile(aqui):      # el script y el arte quedan dentro del .blend
            bpy.data.texts.load(os.path.abspath(aqui))
            arte = os.path.join(carpeta, ARCHIVO_ARTE)
            if os.path.isfile(arte) and ARCHIVO_ARTE not in bpy.data.texts:
                bpy.data.texts.load(arte)
        for pantalla in bpy.data.screens:      # al abrir, la vista 3D mira por la cámara
            for area in pantalla.areas:
                for esp in area.spaces:
                    if esp.type == "VIEW_3D" and esp.region_3d:
                        esp.region_3d.view_perspective = "CAMERA"
        bpy.ops.wm.save_as_mainfile(filepath=ruta, compress=True, relative_remap=True)
        print(f"[sellos] Escena guardada: {ruta}")


if __name__ == "__main__":
    main()
