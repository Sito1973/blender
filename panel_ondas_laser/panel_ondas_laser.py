"""
Panel decorativo de ondas en relieve para CORTE LÁSER (2 capas de madera/MDF).

Cómo usarlo
-----------
  * Dentro de Blender:  pestaña "Scripting" > Abrir este archivo > Ejecutar (Alt+P).
  * Por consola:        blender --background --python panel_ondas_laser.py

Qué genera (en la carpeta de este script)
-----------------------------------------
  corte/capa1_base.svg|dxf      -> cuadrado liso (la base)
  corte/capa2_relieve.svg|dxf   -> marco + ondas (lo que corta el láser)
  planos/plano_general.svg      -> plano con medidas y lista de piezas
  panel_ondas.blend             -> modelo 3D (solo por consola)
  renders/*.png                 -> vistas previas (solo por consola)

Todas las medidas de los PARÁMETROS están en milímetros.
Si editas las curvas a mano en Blender, pon MODO = "EXPORTAR" y vuelve a
ejecutar: se reescriben los archivos de corte a partir de las curvas de la escena.
"""

import math
import os
import random

try:
    import bpy
    from mathutils import Vector
except ImportError:  # permite generar SVG/DXF sin Blender
    bpy = None

# ───────────────────────────── PARÁMETROS (mm) ─────────────────────────────
MODO = "GENERAR"          # "GENERAR" crea todo de cero · "EXPORTAR" solo reexporta la escena

ANCHO = 400.0             # ancho del panel
ALTO = 400.0              # alto del panel
MARCO = 8.0               # ancho del marco perimetral
ESPESOR_BASE = 9.0        # capa 1 (cuadrado liso)
ESPESOR_RELIEVE = 9.0     # capa 2 (marco + ondas)
MATERIAL = "MDF"          # solo para rotular el plano
CANTIDAD_PANELES = 6      # paneles del conjunto

NUM_BANDAS = 11           # impar. Huecos = (NUM_BANDAS - 1) / 2
SEMILLA = 9               # cambia el dibujo de las ondas
PENDIENTE_MAX = 1.15      # qué tan "tumbadas" pueden ir las ondas (1 = 45°)
ANCHO_MIN_RELIEVE = 6.0   # tira de madera más fina permitida
ANCHO_MIN_HUECO = 4.0     # ranura más fina permitida
LINEAS_GRABADO = True     # líneas finas grabadas (azul) sobre las zonas en relieve
PASO_NODOS = 4.0          # separación entre nodos Bézier

RENDERIZAR = True         # solo se aplica al ejecutar por consola (--background)
MUESTRAS_RENDER = 64

COLECCION_PANEL = "Panel ondas (planos de corte)"
COLECCION_CONJUNTO = "Conjunto de paneles"
E = 0.001                 # mm -> unidades de Blender (metros)


# ───────────────────────────── GEOMETRÍA DEL PATRÓN ─────────────────────────────
def _suave(x):
    """Escalón suave 0..1 con derivadas nulas en los extremos."""
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (6.0 * x - 15.0) + 10.0)


def _fronteras(amplitud, muestras):
    """Posición x de cada frontera entre bandas para `muestras` alturas.

    Las bandas pares quedan en relieve y las impares son huecos. Cada banda
    tiene un ancho siempre positivo y la suma es constante, así que las curvas
    nunca se cruzan. En los bordes superior e inferior los anchos son
    simétricos, de modo que los paneles casan entre sí girados o sin girar.
    """
    rnd = random.Random(SEMILLA)
    k_tot = NUM_BANDAS
    mitad = (k_tot + 1) // 2
    base_m = [rnd.uniform(38, 70) if k % 2 == 0 else rnd.uniform(11, 20) for k in range(mitad)]
    base = base_m + base_m[-2::-1]
    minimo = [ANCHO_MIN_RELIEVE if k % 2 == 0 else ANCHO_MIN_HUECO for k in range(k_tot)]

    f1, f2 = rnd.uniform(0.55, 0.85), rnd.uniform(1.1, 1.6)
    p1, p2 = rnd.uniform(0, 1), rnd.uniform(0, 1)
    psi1 = rnd.choice([-1, 1]) * rnd.uniform(0.05, 0.11)
    psi2 = rnd.choice([-1, 1]) * rnd.uniform(0.08, 0.16)
    sf, sp = rnd.uniform(0.7, 1.05), rnd.uniform(0, 1)
    amp_k = [rnd.uniform(0.7, 1.3) for _ in range(k_tot)]
    fase_k = [rnd.uniform(-0.06, 0.06) for _ in range(k_tot)]

    interior = ANCHO - 2 * MARCO
    libre = interior - sum(minimo)
    dos_pi = 2 * math.pi
    filas = []
    for j in range(muestras):
        t = j / (muestras - 1)
        env = _suave((t - 0.03) / 0.42) * _suave((1 - t - 0.02) / 0.30)
        vaiven = 0.6 * amplitud * (math.sin(dos_pi * (sf * t + sp))
                                   + 0.35 * math.sin(dos_pi * (1.9 * sf * t + 2.3 * sp)))
        u = []
        for k in range(k_tot):
            g = (k / (k_tot - 1) - 0.5) * 2.0
            loc = (math.sin(dos_pi * (f1 * t + p1 + psi1 * k + fase_k[k]))
                   + 0.55 * math.sin(dos_pi * (f2 * t + p2 + psi2 * k)))
            if k % 2 == 1:
                s = env * amplitud * amp_k[k] * (1.1 + loc)
            else:
                s = -0.35 * env * amplitud * amp_k[k] * loc
            u.append(base[k] * math.exp(s + env * vaiven * g))
        total = sum(u)
        x = MARCO
        fila = [x]
        for k in range(k_tot):
            x += minimo[k] + libre * u[k] / total
            fila.append(x)
        filas.append(fila)
    return filas


def _pendiente_max(filas, dy):
    return max(abs(filas[j][i] - filas[j - 1][i]) / dy
               for j in range(1, len(filas)) for i in range(len(filas[0])))


def generar_trazados():
    """Devuelve los trazados del panel como curvas Bézier (medidas en mm).

    Cada trazado: dict(capa, tipo "CORTE"/"GRABADO", cerrado, nudos=[(asa_izq, punto, asa_der)]).
    """
    if NUM_BANDAS % 2 == 0 or NUM_BANDAS < 3:
        raise ValueError("NUM_BANDAS debe ser impar y mayor o igual que 3")
    alto_int = ALTO - 2 * MARCO
    tramos = max(8, round(alto_int / PASO_NODOS))
    sub = 4                                   # muestras finas por tramo
    muestras = tramos * sub + 1
    dy = alto_int / (muestras - 1)

    # Sube la amplitud hasta alcanzar la pendiente máxima permitida.
    lo, hi = 0.05, 2.2
    for _ in range(18):
        medio = (lo + hi) / 2
        if _pendiente_max(_fronteras(medio, muestras), dy) > PENDIENTE_MAX:
            hi = medio
        else:
            lo = medio
    filas = _fronteras(lo, muestras)

    def curva(fx):
        """Nudos Bézier de una curva x = fx(j) que sube de abajo arriba."""
        xs = [fx(j) for j in range(muestras)]
        nudos = []
        for n in range(tramos + 1):
            j = n * sub
            a, b = max(j - 1, 0), min(j + 1, muestras - 1)
            m = (xs[b] - xs[a]) / ((b - a) * dy)          # dx/dy
            h = sub * dy / 3.0
            p = (xs[j], MARCO + j * dy)
            nudos.append(((p[0] - m * h, p[1] - h), p, (p[0] + m * h, p[1] + h)))
        return nudos

    def recto(p, q):                          # asa a 1/3 del segmento recto p->q
        return (p[0] + (q[0] - p[0]) / 3.0, p[1] + (q[1] - p[1]) / 3.0)

    trazados = [
        dict(capa=1, tipo="CORTE", cerrado=True, nudos=_poligono(
            [(0, 0), (ANCHO, 0), (ANCHO, ALTO), (0, ALTO)])),
        dict(capa=2, tipo="CORTE", cerrado=True, nudos=_poligono(
            [(0, 0), (ANCHO, 0), (ANCHO, ALTO), (0, ALTO)])),
    ]
    for k in range(1, NUM_BANDAS, 2):         # huecos
        izq = curva(lambda j, k=k: filas[j][k])
        der = curva(lambda j, k=k: filas[j][k + 1])
        der_baja = [(hd, p, hi_) for (hi_, p, hd) in reversed(der)]
        a0, a1, b1, b0 = izq[0][1], izq[-1][1], der[-1][1], der[0][1]
        izq[0] = (recto(a0, b0), a0, izq[0][2])
        izq[-1] = (izq[-1][0], a1, recto(a1, b1))
        der_baja[0] = (recto(b1, a1), b1, der_baja[0][2])
        der_baja[-1] = (der_baja[-1][0], b0, recto(b0, a0))
        trazados.append(dict(capa=2, tipo="CORTE", cerrado=True, nudos=izq + der_baja))
    if LINEAS_GRABADO:
        for k in range(0, NUM_BANDAS, 2):     # una línea por el centro de cada relieve
            trazados.append(dict(capa=2, tipo="GRABADO", cerrado=False, nudos=curva(
                lambda j, k=k: 0.5 * (filas[j][k] + filas[j][k + 1]))))
    return trazados


def _poligono(puntos):
    return [(p, p, p) for p in puntos]


# ───────────────────────────── UTILIDADES DE TRAZADOS ─────────────────────────────
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


# ───────────────────────────── ARCHIVOS DE CORTE ─────────────────────────────
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
         f'width="{ANCHO:g}mm" height="{ALTO:g}mm" viewBox="0 0 {ANCHO:g} {ALTO:g}">',
         f'<title>{titulo}</title>']
    for nombre, color, grupo in (("GRABADO", "#0000ff", grab), ("CORTE", "#ff0000", corte)):
        if grupo:
            s.append(f'<g id="{nombre}" inkscape:groupmode="layer" inkscape:label="{nombre}" '
                     f'fill="none" stroke="{color}" stroke-width="0.1">')
            s += [f'<path d="{_d_svg(t, ALTO)}"/>' for t in grupo]
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
         "9", "$EXTMAX", "10", f"{ANCHO:.4f}", "20", f"{ALTO:.4f}", "30", "0.0",
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


# ───────────────────────────── PLANO GENERAL (con medidas) ─────────────────────────────
def _cruces(trazados, y):
    """Tramos [x0, x1] que quedan huecos sobre la horizontal de altura y."""
    tramos = []
    for t in trazados:
        pts = _polilinea(t)
        xs = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        tramos += list(zip(xs[0::2], xs[1::2]))
    return sorted(tramos)


def escribir_plano(ruta, trazados):
    """Hoja A3 apaisada con vistas acotadas, perfil y lista de piezas."""
    capa2 = [t for t in trazados if t["capa"] == 2]
    _, corte = _ordenar(capa2)
    huecos, grab = corte[:-1], [t for t in capa2 if t["tipo"] == "GRABADO"]
    total = ESPESOR_BASE + ESPESOR_RELIEVE
    tinta, gris, acento = "#1f2a37", "#6b7280", "#b45309"
    s = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297" '
         'font-family="Inter, Helvetica, Arial, sans-serif">',
         '<rect width="420" height="297" fill="#ffffff"/>',
         f'<rect x="8" y="8" width="404" height="281" fill="none" stroke="{tinta}" stroke-width="0.5"/>',
         f'<line x1="8" y1="28" x2="412" y2="28" stroke="{tinta}" stroke-width="0.5"/>',
         f'<text x="14" y="21.5" font-size="8" font-weight="700" fill="{tinta}">'
         f'PANEL DE ONDAS EN RELIEVE — PLANO PARA CORTE LÁSER</text>',
         f'<text x="406" y="18" font-size="4" fill="{gris}" text-anchor="end">Medidas en milímetros</text>',
         f'<text x="406" y="24" font-size="4" fill="{gris}" text-anchor="end">'
         f'Archivos de corte a escala 1:1</text>']

    def texto(x, y, txt, tam=4.0, color=tinta, peso="400", ancla="start", giro=None):
        g = f' transform="rotate({giro} {x} {y})"' if giro is not None else ""
        s.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{tam}" fill="{color}" '
                 f'font-weight="{peso}" text-anchor="{ancla}"{g}>{txt}</text>')

    def cota_h(x0, x1, y, txt, arriba=False):
        s.append(f'<g stroke="{acento}" stroke-width="0.25" fill="none">'
                 f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/>'
                 f'<line x1="{x0}" y1="{y - 2}" x2="{x0}" y2="{y + 2}"/>'
                 f'<line x1="{x1}" y1="{y - 2}" x2="{x1}" y2="{y + 2}"/></g>')
        texto((x0 + x1) / 2, y - 1.5 if arriba else y + 5, txt, 4.2, acento, "600", "middle")

    def cota_v(x, y0, y1, txt, derecha=False):
        s.append(f'<g stroke="{acento}" stroke-width="0.25" fill="none">'
                 f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}"/>'
                 f'<line x1="{x - 2}" y1="{y0}" x2="{x + 2}" y2="{y0}"/>'
                 f'<line x1="{x - 2}" y1="{y1}" x2="{x + 2}" y2="{y1}"/></g>')
        if derecha:
            texto(x + 2.5, (y0 + y1) / 2 + 1.5, txt, 4.2, acento, "600")
        else:
            texto(x - 2, (y0 + y1) / 2, txt, 4.2, acento, "600", "middle", -90)

    # Vista 1 · capa 2 (relieve)
    e2 = 200.0 / max(ANCHO, ALTO)
    x2, y2 = 30.0, 48.0
    w2, h2 = ANCHO * e2, ALTO * e2
    texto(x2, y2 - 9, "CAPA 2 · RELIEVE", 5.5, tinta, "700")
    texto(x2, y2 - 3.5, f"1 pieza por panel · {MATERIAL} {ESPESOR_RELIEVE:g} mm · {len(huecos)} huecos "
          f"(zona oscura = se retira)", 3.6, gris)
    s.append(f'<rect x="{x2}" y="{y2}" width="{w2}" height="{h2}" fill="#f6efe4" '
             f'stroke="{tinta}" stroke-width="0.45"/>')
    for t in huecos:
        s.append(f'<path d="{_d_svg(t, ALTO, e2, x2, y2)}" fill="#d3bf9f" '
                 f'stroke="{tinta}" stroke-width="0.35"/>')
    for t in grab:
        s.append(f'<path d="{_d_svg(t, ALTO, e2, x2, y2)}" fill="none" stroke="#2563eb" '
                 f'stroke-width="0.25" stroke-dasharray="1.6 1"/>')
    cota_h(x2, x2 + w2, y2 + h2 + 5, f"{ANCHO:g}")
    cota_v(x2 - 12, y2, y2 + h2, f"{ALTO:g}")
    # cota del marco y línea de sección A-A
    xm = x2 + w2 + 4
    s.append(f'<g stroke="{acento}" stroke-width="0.25"><line x1="{xm}" y1="{y2}" x2="{xm}" '
             f'y2="{y2 + MARCO * e2}"/><line x1="{xm - 1.5}" y1="{y2}" x2="{xm + 1.5}" y2="{y2}"/>'
             f'<line x1="{xm - 1.5}" y1="{y2 + MARCO * e2}" x2="{xm + 1.5}" y2="{y2 + MARCO * e2}"/></g>')
    texto(xm + 2.5, y2 + MARCO * e2 / 2 + 1.4, f"marco {MARCO:g}", 3.6, acento, "600")
    ya = y2 + h2 / 2
    s.append(f'<line x1="{x2 - 3}" y1="{ya}" x2="{x2 + w2 + 3}" y2="{ya}" stroke="{tinta}" '
             f'stroke-width="0.3" stroke-dasharray="5 1.5 1 1.5"/>')
    texto(x2 + w2 + 4.5, ya + 1.5, "A", 4.5, tinta, "700")
    texto(x2 - 4.5, ya + 1.5, "A", 4.5, tinta, "700", "end")

    # Vista 2 · capa 1 (base)
    x1, y1 = 268.0, 48.0
    e1 = 78.0 / max(ANCHO, ALTO)
    w1, h1 = ANCHO * e1, ALTO * e1
    texto(x1, y1 - 9, "CAPA 1 · BASE", 5.5, tinta, "700")
    texto(x1, y1 - 3.5, f"1 pieza por panel · {MATERIAL} {ESPESOR_BASE:g} mm · cuadrado liso", 3.6, gris)
    s.append(f'<rect x="{x1}" y="{y1}" width="{w1}" height="{h1}" fill="#f6efe4" '
             f'stroke="{tinta}" stroke-width="0.45"/>')
    cota_h(x1, x1 + w1, y1 + h1 + 5, f"{ANCHO:g}")
    cota_v(x1 + w1 + 6, y1, y1 + h1, f"{ALTO:g}", derecha=True)

    # Perfil A-A (espesores ampliados)
    xp, yp = 268.0, 168.0
    ep = 130.0 / ANCHO
    ez = 0.9                                   # mm de dibujo por mm de espesor
    texto(xp, yp - 9, "SECCIÓN A–A", 5.5, tinta, "700")
    texto(xp, yp - 3.5, "espesores dibujados ampliados", 3.6, gris)
    zb, zr = ESPESOR_BASE * ez, ESPESOR_RELIEVE * ez
    s.append(f'<rect x="{xp}" y="{yp + zr}" width="{ANCHO * ep}" height="{zb}" fill="#e3d3ba" '
             f'stroke="{tinta}" stroke-width="0.35"/>')
    bordes = [0.0] + [v for tramo in _cruces(huecos, ALTO / 2) for v in tramo] + [ANCHO]
    for a, b in zip(bordes[0::2], bordes[1::2]):
        s.append(f'<rect x="{xp + a * ep:.2f}" y="{yp}" width="{(b - a) * ep:.2f}" height="{zr}" '
                 f'fill="#f6efe4" stroke="{tinta}" stroke-width="0.35"/>')
    xc = xp + ANCHO * ep + 5
    cota_v(xc, yp, yp + zr, f"{ESPESOR_RELIEVE:g}", derecha=True)
    cota_v(xc, yp + zr, yp + zr + zb, f"{ESPESOR_BASE:g}", derecha=True)
    cota_v(xp - 5, yp, yp + zr + zb, f"{total:g}")
    texto(xp, yp + zr + zb + 6, "capa 2 (relieve) encolada sobre capa 1 (base)", 3.6, gris)

    # Lista de piezas
    xt, yt = 268.0, 208.0
    texto(xt, yt, "LISTA DE PIEZAS", 5.5, tinta, "700")
    cols = [0, 58, 98, 115]
    filas = [("Pieza", "Medida (mm)", "1 panel", f"{CANTIDAD_PANELES} paneles"),
             ("Capa 1 · base lisa", f"{ANCHO:g} × {ALTO:g} × {ESPESOR_BASE:g}", "1",
              str(CANTIDAD_PANELES)),
             ("Capa 2 · relieve calado", f"{ANCHO:g} × {ALTO:g} × {ESPESOR_RELIEVE:g}", "1",
              str(CANTIDAD_PANELES)),
             ("Total de tableros", f"{ANCHO:g} × {ALTO:g}", "2", str(2 * CANTIDAD_PANELES))]
    for i, fila in enumerate(filas):
        y = yt + 8 + i * 7
        peso = "700" if i in (0, len(filas) - 1) else "400"
        for cx, celda in zip(cols, fila):
            texto(xt + cx, y, celda, 3.8, gris if i == 0 else tinta, peso)
        s.append(f'<line x1="{xt}" y1="{y + 2.2}" x2="{xt + 138}" y2="{y + 2.2}" '
                 f'stroke="#d1d5db" stroke-width="0.25"/>')
    notas = [f"Panel terminado: {ANCHO:g} × {ALTO:g} × {total:g} mm.",
             "Rojo = cortar · Azul = grabar línea (opcional).",
             "Los 6 paneles son iguales: se combinan girándolos 180°."]
    for i, n in enumerate(notas):
        texto(xt, yt + 44 + i * 5.5, n, 3.7, tinta)
    s.append('</svg>')
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(s) + "\n")


def exportar(trazados, carpeta):
    corte = os.path.join(carpeta, "corte")
    planos = os.path.join(carpeta, "planos")
    os.makedirs(corte, exist_ok=True)
    os.makedirs(planos, exist_ok=True)
    for capa, nombre in ((1, "capa1_base"), (2, "capa2_relieve")):
        tr = [t for t in trazados if t["capa"] == capa]
        escribir_svg(os.path.join(corte, nombre + ".svg"), tr, nombre)
        escribir_dxf(os.path.join(corte, nombre + ".dxf"), tr)
    escribir_plano(os.path.join(planos, "plano_general.svg"), trazados)
    print(f"[panel] Archivos de corte y plano escritos en: {carpeta}")


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


def construir_escena(trazados):
    """Crea las curvas de corte (editables) y el modelo 3D de vista previa."""
    esc = bpy.context.scene
    esc.unit_settings.system = "METRIC"
    esc.unit_settings.length_unit = "MILLIMETERS"
    madera = _material("Madera", (0.52, 0.34, 0.19), canto=(0.07, 0.04, 0.025))
    quemado = _material("Linea grabada", (0.10, 0.06, 0.035), 0.9)

    col = _coleccion(COLECCION_PANEL)
    col.instance_offset = (ANCHO * E / 2, ALTO * E / 2, 0.0)

    def sel(capa, tipo):
        return [t for t in trazados if t["capa"] == capa and t["tipo"] == tipo]

    _objeto_curva("Capa1_Base", sel(1, "CORTE"), col, 1, "CORTE",
                  ESPESOR_BASE / 2, ESPESOR_BASE, mat=madera)
    _objeto_curva("Capa2_Relieve", sel(2, "CORTE"), col, 2, "CORTE",
                  ESPESOR_BASE + ESPESOR_RELIEVE / 2, ESPESOR_RELIEVE, mat=madera)
    if sel(2, "GRABADO"):
        _objeto_curva("Capa2_Grabado", sel(2, "GRABADO"), col, 2, "GRABADO",
                      ESPESOR_BASE + ESPESOR_RELIEVE, bisel=0.45, mat=quemado)

    # Conjunto de paneles: copias enlazadas, alternando giros de 180°.
    conj = _coleccion(COLECCION_CONJUNTO)
    columnas = max(1, math.ceil(CANTIDAD_PANELES / 2))
    junta = 3.0
    x_ini = ANCHO * 1.6
    for i in range(CANTIDAD_PANELES):
        c, f = i % columnas, i // columnas
        inst = bpy.data.objects.new(f"Panel_{i + 1}", None)
        inst.instance_type = "COLLECTION"
        inst.instance_collection = col
        inst.empty_display_size = 0.05
        inst.location = ((x_ini + c * (ANCHO + junta) + ANCHO / 2) * E,
                         (-f * (ALTO + junta) + ALTO / 2) * E, 0.0)
        inst.rotation_euler.z = math.pi * ((c + f) % 2)
        conj.objects.link(inst)
    bpy.context.view_layer.update()
    return dict(columnas=columnas, filas=math.ceil(CANTIDAD_PANELES / columnas),
                x_ini=x_ini, junta=junta)


def leer_trazados_de_escena():
    """Lee las curvas de la colección del panel (por si se editaron a mano)."""
    col = bpy.data.collections.get(COLECCION_PANEL)
    if not col:
        raise RuntimeError(f"No existe la colección «{COLECCION_PANEL}». Ejecuta antes con MODO = 'GENERAR'.")
    bpy.context.view_layer.update()
    trazados = []
    for ob in col.objects:
        if ob.type != "CURVE" or "laser" not in ob:
            continue
        mw = ob.matrix_world

        def mm(v):
            w = mw @ Vector(v[:3])
            return (w.x / E, w.y / E)
        for sp in ob.data.splines:
            if sp.type == "BEZIER":
                nudos = [(mm(b.handle_left), mm(b.co), mm(b.handle_right)) for b in sp.bezier_points]
            else:
                nudos = [(mm(p.co),) * 3 for p in sp.points]
            trazados.append(dict(capa=int(ob["capa"]), tipo=ob["laser"],
                                 cerrado=sp.use_cyclic_u, nudos=nudos))
    return trazados


def _apuntar(ob, destino):
    ob.rotation_euler = (Vector(destino) - ob.location).to_track_quat("-Z", "Y").to_euler()


def renderizar(carpeta, info):
    """Dos vistas previas con Cycles (CPU)."""
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
    fondo = next((n for n in mundo.node_tree.nodes if n.type == "BACKGROUND"), None)
    if fondo:
        fondo.inputs["Color"].default_value = (1.0, 0.98, 0.95, 1.0)
        fondo.inputs["Strength"].default_value = 0.45

    esc_col = _coleccion("Vista previa (luz y camaras)")
    pared_m = bpy.data.meshes.new("Pared")
    r = 20.0
    pared_m.from_pydata([(-r, -r, 0), (r, -r, 0), (r, r, 0), (-r, r, 0)], [], [(0, 1, 2, 3)])
    pared = bpy.data.objects.new("Pared", pared_m)
    pared.location.z = -0.0002
    pared_m.materials.append(_material("Pared", (0.86, 0.85, 0.83), 0.9))
    esc_col.objects.link(pared)

    sol_d = bpy.data.lights.new("Sol", "SUN")
    sol_d.energy = 3.4
    sol_d.angle = math.radians(8)
    sol = bpy.data.objects.new("Sol", sol_d)           # luz rasante: marca el relieve
    sol.rotation_euler = Vector((0.80, -0.45, -0.42)).to_track_quat("-Z", "Y").to_euler()
    esc_col.objects.link(sol)

    def camara(nombre, pos, destino, lente=None, orto=None):
        cd = bpy.data.cameras.new(nombre)
        if orto:
            cd.type, cd.ortho_scale = "ORTHO", orto
        else:
            cd.lens = lente
        cam = bpy.data.objects.new(nombre, cd)
        cam.location = pos
        _apuntar(cam, destino)
        esc_col.objects.link(cam)
        return cam

    cx, cy = ANCHO * E / 2, ALTO * E / 2
    cam1 = camara("Camara_panel", (cx - 0.22, cy - 0.62, 0.86), (cx, cy - 0.015, 0.0), lente=50)
    ancho_c = info["columnas"] * ANCHO + (info["columnas"] - 1) * info["junta"]
    alto_c = info["filas"] * ALTO + (info["filas"] - 1) * info["junta"]
    mx = (info["x_ini"] + ancho_c / 2) * E
    my = (ALTO - alto_c / 2) * E
    lejos = max(ancho_c, 1.5 * alto_c) * E
    cam2 = camara("Camara_conjunto", (mx - 0.20 * lejos, my - 0.92 * lejos, 1.42 * lejos),
                  (mx + 0.005 * lejos, my - 0.01 * lejos, 0.0), lente=50)

    for cam, nombre, res in ((cam1, "vista_panel.png", (1500, 1500)),
                             (cam2, "vista_conjunto.png", (1800, 1200))):
        esc.camera = cam
        esc.render.resolution_x, esc.render.resolution_y = res
        esc.render.filepath = os.path.join(salida, nombre)
        bpy.ops.render.render(write_still=True)
        print(f"[panel] Render: {esc.render.filepath}")
    esc.camera = cam1


def _carpeta_salida():
    if bpy and bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath)
    aqui = globals().get("__file__", "")
    if aqui and os.path.isfile(aqui):
        return os.path.dirname(os.path.abspath(aqui))
    return os.path.join(os.path.expanduser("~"), "panel_ondas_laser")


def main():
    carpeta = _carpeta_salida()
    os.makedirs(carpeta, exist_ok=True)
    if bpy is None:                            # sin Blender: solo archivos de corte
        exportar(generar_trazados(), carpeta)
        return
    if MODO.upper() == "EXPORTAR":
        exportar(leer_trazados_de_escena(), carpeta)
        return
    consola = bpy.app.background
    if consola:                                # escena nueva y limpia
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    info = construir_escena(generar_trazados())
    exportar(leer_trazados_de_escena(), carpeta)   # se exporta lo que hay en Blender
    if consola:
        if RENDERIZAR:
            renderizar(carpeta, info)
        ruta = os.path.join(carpeta, "panel_ondas.blend")
        aqui = globals().get("__file__", "")
        if aqui and os.path.isfile(aqui):      # el script queda a mano en la pestaña Scripting
            bpy.data.texts.load(os.path.abspath(aqui))
        bpy.ops.wm.save_as_mainfile(filepath=ruta, compress=True, relative_remap=True)
        print(f"[panel] Escena guardada: {ruta}")


if __name__ == "__main__":
    main()
