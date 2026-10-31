"""
Genera los planos para el taller a partir de los datos que deja
generar_lampara.py (datos_pieza.json y geometria.json):

  - planos_lampara_roseta.pdf   ficha técnica, plano de la pieza, plano de
                                armado y plantillas 1:1 en hojas carta
  - plantilla_1a1_plotter.pdf   las dos plantillas 1:1 en una sola hoja (plotter)
  - curva_unica.dxf, meridiano.dxf, planta_armado.dxf   (mm, escala 1:1)

Uso:  python3 generar_planos.py [carpeta]
"""

import json
import math
import os
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

D = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
dat = json.load(open(os.path.join(D, "datos_pieza.json"), encoding="utf-8"))
geo = json.load(open(os.path.join(D, "geometria.json"), encoding="utf-8"))

cu = dat["curva"]
me = dat["meridiano"]
me.setdefault("flecha", me["radio_doblez_eje"] * (1 - math.cos(math.radians(me["angulo_arco_deg"]) / 2)))
ROD = dat["diam_varilla"]
N = dat["n_petalos"]
NC = dat["n_curvas"]
PASO = geo["paso_deg"]

GRIS = colors.Color(0.55, 0.55, 0.58)
GRIS_CL = colors.Color(0.82, 0.82, 0.84)
ROJO = colors.Color(0.78, 0.12, 0.10)
AZUL = colors.Color(0.12, 0.30, 0.65)
NEGRO = colors.black
ORO = colors.Color(0.72, 0.56, 0.33)


def f1(x):
    return ("%.1f" % x).replace(".", ",")


# ---------------------------------------------------------------------------
# Geometría plana de una pieza: arco de radio R y ángulo A (grados), con la
# cuerda horizontal sobre y=0 y la panza hacia arriba.
# ---------------------------------------------------------------------------
def arco_plano(R, A_deg, n=240):
    A = math.radians(A_deg)
    yc = -R * math.cos(A / 2)          # centro del doblez (debajo de la cuerda)

    def pts(r):
        out = []
        for i in range(n + 1):
            t = math.pi / 2 - A / 2 + A * i / n
            out.append((r * math.cos(t), yc + r * math.sin(t)))
        return out

    return yc, pts


def poly(c, pts, ox, oy, s, close=False):
    p = c.beginPath()
    p.moveTo(ox + pts[0][0] * s, oy + pts[0][1] * s)
    for x, y in pts[1:]:
        p.lineTo(ox + x * s, oy + y * s)
    if close:
        p.close()
    c.drawPath(p, stroke=1, fill=0)


def dibujar_pieza(c, R, A_deg, ox, oy, s, etiquetas=True, centro=True, nombre=""):
    """Dibuja la pieza en el canvas. (ox,oy) en puntos = punto medio de la cuerda.
    s = puntos por mm de pieza (escala)."""
    A = math.radians(A_deg)
    yc, pts = arco_plano(R, A_deg)
    cuerda = 2 * R * math.sin(A / 2)
    flecha = R * (1 - math.cos(A / 2))
    r = ROD / 2
    # contorno de la varilla
    c.setStrokeColor(NEGRO)
    c.setLineWidth(0.6)
    c.setDash()
    po, pi = pts(R + r), pts(R - r)
    poly(c, po, ox, oy, s)
    poly(c, pi, ox, oy, s)
    poly(c, [po[0], pi[0]], ox, oy, s)
    poly(c, [po[-1], pi[-1]], ox, oy, s)
    # eje
    c.setStrokeColor(AZUL)
    c.setLineWidth(0.4)
    c.setDash([6, 2, 1, 2])
    poly(c, pts(R), ox, oy, s)
    c.setDash()
    # cuerda y flecha
    c.setStrokeColor(ROJO)
    c.setLineWidth(0.4)
    e1, e2 = pts(R)[0], pts(R)[-1]
    poly(c, [e1, e2], ox, oy, s)
    poly(c, [(0, 0), (0, flecha)], ox, oy, s)
    if centro:
        poly(c, [(0, yc), e1], ox, oy, s)
        poly(c, [(0, yc), e2], ox, oy, s)
        c.circle(ox, oy + yc * s, 1.2 * mm, stroke=1, fill=0)
    if etiquetas:
        c.setFillColor(NEGRO)
        c.setFont("Helvetica", 8)
        c.drawCentredString(ox, oy - 4 * mm, "Cuerda = %s mm" % f1(cuerda))
        c.drawString(ox + 2 * mm, oy + flecha * s / 2, "Flecha = %s mm" % f1(flecha))
        if centro:
            c.drawCentredString(ox, oy + yc * s - 4.5 * mm, "centro del doblez")
            c.drawString(ox + e2[0] * s * 0.5 + 3 * mm, oy + (yc + e2[1]) * s * 0.5,
                         "R = %s mm (al eje)" % f1(R))
            c.drawCentredString(ox, oy + yc * s + 10 * mm, "%s°" % f1(A_deg))
    return cuerda, flecha, yc


def cabecera(c, titulo, sub=None, pag=None):
    W, H = landscape(letter)
    c.setFillColor(NEGRO)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(14 * mm, H - 15 * mm, titulo)
    if sub:
        c.setFont("Helvetica", 9)
        c.setFillColor(GRIS)
        c.drawString(14 * mm, H - 20.5 * mm, sub)
    c.setStrokeColor(GRIS_CL)
    c.setLineWidth(0.6)
    c.line(14 * mm, H - 23 * mm, W - 14 * mm, H - 23 * mm)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GRIS)
    c.drawString(14 * mm, 8 * mm, "Lámpara roseta – estructura metálica · medidas en mm · "
                 "Ø aro %s · altura %s" % (f1(dat["diametro_aro_eje"]), f1(dat["altura_domo_eje"])))
    if pag:
        c.drawRightString(W - 14 * mm, 8 * mm, pag)
    c.setFillColor(NEGRO)


def tabla(c, x, y, filas, anchos, alto=6.2 * mm, fs=8.5, cab=True):
    c.setLineWidth(0.4)
    for i, fila in enumerate(filas):
        yy = y - i * alto
        if i == 0 and cab:
            c.setFillColor(colors.Color(0.93, 0.91, 0.87))
            c.rect(x, yy - alto + 1.6 * mm, sum(anchos), alto, stroke=0, fill=1)
            c.setFont("Helvetica-Bold", fs)
        else:
            c.setFont("Helvetica", fs)
        c.setFillColor(NEGRO)
        xx = x
        for txt, w in zip(fila, anchos):
            c.drawString(xx + 1.5 * mm, yy - alto + 3.4 * mm, txt)
            xx += w
        c.setStrokeColor(GRIS_CL)
        c.line(x, yy - alto + 1.6 * mm, x + sum(anchos), yy - alto + 1.6 * mm)
    return y - len(filas) * alto


def notas(c, x, y, lineas, fs=8.5, sep=4.4 * mm, ancho=None):
    c.setFont("Helvetica", fs)
    for ln in lineas:
        if ln.startswith("##"):
            c.setFont("Helvetica-Bold", fs + 0.5)
            c.drawString(x, y, ln[2:].strip())
            c.setFont("Helvetica", fs)
        else:
            c.drawString(x, y, ln)
        y -= sep
    return y


# ---------------------------------------------------------------------------
# PDF principal
# ---------------------------------------------------------------------------
W, H = landscape(letter)
pdf_path = os.path.join(D, "planos_lampara_roseta.pdf")
c = canvas.Canvas(pdf_path, pagesize=(W, H))
c.setTitle("Lámpara roseta – estructura metálica")

total_varilla = NC * cu["largo_desarrollado_eje"] + (N * me["largo_desarrollado_eje"] if me["incluido"] else 0)

# ---- Página 1: ficha técnica ----
cabecera(c, "Lámpara roseta – estructura metálica",
         "Ficha técnica para taller. Medidas estimadas a partir de fotos; todo es paramétrico "
         "(se regenera con generar_lampara.py).", "1")
img_w = 124 * mm
img_h = img_w * 1050 / 1400
c.drawImage(os.path.join(D, "render_3_4.png"), 14 * mm, H - 27 * mm - img_h, img_w, img_h)
c.drawImage(os.path.join(D, "render_desde_abajo.png"), W - 14 * mm - img_w, H - 27 * mm - img_h, img_w, img_h)
y = H - 33 * mm - img_h
c.setFont("Helvetica-Bold", 10.5)
c.drawString(14 * mm, y, "Lista de piezas")
filas = [
    ("Pieza", "Cant.", "Material", "Forma y medidas (al eje de la varilla)"),
    ("Curva – PIEZA ÚNICA", str(NC), "Varilla lisa Ø%s" % f1(ROD),
     "Arco plano R %s · %s° · largo %s · cuerda %s" % (f1(cu["radio_doblez_eje"]), f1(cu["angulo_arco_deg"]),
                                                     f1(cu["largo_desarrollado_eje"]), f1(cu["cuerda"]))),
]
if me["incluido"]:
    filas.append(("Meridiano (opcional, tiras LED)", str(N), "Varilla lisa Ø%s" % f1(ROD),
                  "Arco plano R %s · %s° · largo %s · cuerda %s" % (f1(me["radio_doblez_eje"]), f1(me["angulo_arco_deg"]),
                                                                  f1(me["largo_desarrollado_eje"]), f1(me["cuerda"]))))
filas += [
    ("Aro exterior", "1", "Pletina %s×%s" % (f1(dat["aro"]["ancho"]), f1(dat["aro"]["espesor"])),
     "Anillo plano Ø ext %s / Ø int %s · desarrollo %s" % (f1(dat["aro"]["diam_exterior"]), f1(dat["aro"]["diam_interior"]),
                                                           f1(dat["aro"]["largo_desarrollado_eje"]))),
    ("Disco central", "1", "Lámina %s" % f1(dat["disco"]["espesor"]),
     "Disco Ø %s (perforar al centro para el cable/colgante)" % f1(dat["disco"]["diametro"])),
]
y = tabla(c, 14 * mm, y - 2 * mm, filas, [52 * mm, 13 * mm, 33 * mm, 153 * mm])
y -= 4 * mm
notas(c, 14 * mm, y, [
    "Varilla Ø%s total aprox.: %s m (sin desperdicio)  ·  Lámpara: Ø exterior %s mm, alto del domo %s mm al eje." % (
        f1(ROD), f1(total_varilla / 1000), f1(dat["diametro_exterior_total"]), f1(dat["altura_domo_eje"])),
    "Las %d curvas son IDÉNTICAS: arcos planos de radio fijo. Las que giran a la izquierda son la misma pieza volteada." % NC,
    "Donde las varillas se cruzan van soldadas (punto de soldadura). Cada extremo de curva se suelda al disco central y al aro.",
])
c.showPage()

# ---- Página 2: plano de la pieza única ----
cabecera(c, "Pieza única – curva (hacer %d)" % NC,
         "Varilla lisa Ø%s mm · arco PLANO de radio constante · escala 1:3 en hoja carta impresa al 100 %%" % f1(ROD), "2")
s = mm / 3.0
ox, oy = 14 * mm + 86 * mm, 118 * mm
cuerda, flecha, yc = dibujar_pieza(c, cu["radio_doblez_eje"], cu["angulo_arco_deg"], ox, oy, s)
c.setFont("Helvetica-Bold", 8)
c.drawString(ox - cuerda / 2 * s, oy - 9 * mm, "extremo AL ARO")
c.drawRightString(ox + cuerda / 2 * s, oy - 9 * mm, "extremo AL CENTRO")
yy = notas(c, W - 92 * mm, H - 32 * mm, [
    "## Medidas de la pieza",
    "Radio de doblez (eje): %s mm" % f1(cu["radio_doblez_eje"]),
    "Radio interior / exterior: %s / %s mm" % (f1(cu["radio_interior"]), f1(cu["radio_exterior"])),
    "Ángulo del arco: %s°" % f1(cu["angulo_arco_deg"]),
    "Largo desarrollado (eje): %s mm" % f1(cu["largo_desarrollado_eje"]),
    "Cuerda (extremo a extremo): %s mm" % f1(cu["cuerda"]),
    "Flecha (altura del arco): %s mm" % f1(cu["flecha"]),
    "",
    "## Cómo hacerla",
    "1. Cortar varilla a ~%d mm (sobra para recortar)." % (math.ceil(cu["largo_desarrollado_eje"] / 10) * 10 + 20),
    "2. Rolar/doblar a radio %s mm (usar la" % f1(cu["radio_doblez_eje"]),
    "   plantilla 1:1 de las últimas páginas).",
    "3. Recortar a la cuerda de %s mm." % f1(cu["cuerda"]),
    "4. Verificar: la pieza debe quedar PLANA,",
    "   apoyada toda sobre la mesa (sin torcer).",
    "5. Las %d piezas son iguales; en el armado" % NC,
    "   la mitad se monta volteada (espejo).",
])
c.showPage()

# ---- Página 3: plano de armado en planta ----
cabecera(c, "Plano de armado – vista en planta (desde arriba)",
         "Escala 1:6 al imprimir al 100 %. Rojo: curvas 01A y 01B · azul: la curva que forma la \"V\" con la 01A en el aro · punteado: meridianos.", "3")
s = mm / 6.0
cx, cy = 14 * mm + 80 * mm, 12 * mm + 88 * mm
a = dat["diametro_aro_eje"] / 2
ar = dat["aro"]
c.setStrokeColor(GRIS)
c.setLineWidth(0.5)
for rr in (ar["diam_exterior"] / 2, ar["diam_interior"] / 2):
    c.circle(cx, cy, rr * s, stroke=1, fill=0)
c.circle(cx, cy, dat["disco"]["diametro"] / 2 * s, stroke=1, fill=0)
c01 = geo["curva_01A_mundo"]


def rot(p, ang_deg, mirror=False):
    x, y = p[0], (-p[1] if mirror else p[1])
    t = math.radians(ang_deg)
    return (x * math.cos(t) - y * math.sin(t), x * math.sin(t) + y * math.cos(t))


def arco_k(k, lado):
    return [rot(p, k * PASO, lado == "B") for p in c01]


salto = dat["salto_v"]
for k in range(N):
    for lado in "AB":
        col, lw = GRIS, 0.45
        if k == 0:
            col, lw = ROJO, 1.1
        elif k == salto and lado == "B":
            col, lw = AZUL, 1.1
        c.setStrokeColor(col)
        c.setLineWidth(lw)
        poly(c, arco_k(k, lado), cx, cy, s)
if me["incluido"]:
    c.setStrokeColor(ORO)
    c.setLineWidth(0.4)
    c.setDash(3, 2)
    for k in range(N):
        t = math.radians(geo["mer_offset_deg"] + k * PASO)
        r0, r1 = geo["radio_fin_centro"], a
        c.line(cx + r0 * math.cos(t) * s, cy + r0 * math.sin(t) * s, cx + r1 * math.cos(t) * s, cy + r1 * math.sin(t) * s)
    c.setDash()
# marcas de ángulo cada 15°
c.setFont("Helvetica", 6.5)
c.setFillColor(GRIS)
for k in range(N):
    t = math.radians(k * PASO)
    c.drawCentredString(cx + (a + 24) * math.cos(t) * s - 0, cy + (a + 24) * math.sin(t) * s - 1, "%d°" % round(k * PASO))
c.setFillColor(NEGRO)
c.setStrokeColor(NEGRO)
c.setLineWidth(0.3)
c.line(cx - 6, cy, cx + 6, cy)
c.line(cx, cy - 6, cx, cy + 6)

ce, cm, ca = cu["extremo_centro_r_ang_z"], cu["punto_medio_r_ang_z"], cu["extremo_aro_r_ang_z"]
x0 = W - 98 * mm
yy = H - 31 * mm
c.setFont("Helvetica-Bold", 9.5)
c.drawString(x0, yy, "Ubicación de la curva 01A")
c.setFont("Helvetica", 7.5)
yy -= 4 * mm
c.drawString(x0, yy, "r = radio en planta desde el centro · z = altura sobre el aro")
filas = [("Punto", "r (mm)", "ángulo", "z (mm)"),
         ("Extremo centro", f1(ce[0]), f1(ce[1]) + "°", f1(ce[2])),
         ("Punto medio", f1(cm[0]), f1(cm[1]) + "°", f1(cm[2])),
         ("Extremo aro", f1(ca[0]), f1(ca[1]) + "°", f1(ca[2]))]
yy = tabla(c, x0, yy - 2 * mm, filas, [30 * mm, 18 * mm, 18 * mm, 18 * mm])
yy = notas(c, x0, yy - 4 * mm, [
    "Curva 01B: igual, con los ángulos en negativo",
    "(%s°, %s°, %s°)." % (f1(-ce[1]), f1(-cm[1]), f1(-ca[1])),
    "Curvas siguientes (02A/02B ... %02dA/%02dB):" % (N, N),
    "sumar %s° por cada número." % f1(PASO),
    "",
    "## Puntos de llegada",
    "Aro: %d puntos de \"V\" cada %s°, en 0°, %s°, %s°..." % (N, f1(PASO), f1(PASO), f1(2 * PASO)),
    "  (a cada punto llegan 2 curvas: una A y una B)",
    "Meridianos: a %s° + múltiplos de %s° (entre las V)." % (f1(geo["mer_offset_deg"]), f1(PASO)),
    "Centro: las curvas terminan en r = %s mm," % f1(geo["radio_fin_centro"]),
    "  apoyadas y soldadas sobre el disco Ø%s." % f1(dat["disco"]["diametro"]),
    "",
    "## Plano de cada curva",
    "El plano de la curva está inclinado %s°" % f1(cu["inclinacion_plano_vs_horizontal_deg"]),
    "respecto a la horizontal. Con los 2 extremos",
    "ubicados, girar la pieza hasta que el punto",
    "medio quede a z = %s mm sobre el aro." % f1(cm[2]),
], fs=8.3)
c.showPage()

# ---- Página 4: alzado + secuencia ----
cabecera(c, "Vista lateral y secuencia de armado", None, "4")
img_w = 150 * mm
img_h = img_w * 1050 / 1400
c.drawImage(os.path.join(D, "render_lateral.png"), 14 * mm, H - 28 * mm - img_h, img_w, img_h)
notas(c, 172 * mm, H - 34 * mm, [
    "## Medidas generales",
    "Ø aro (eje varillas): %s mm" % f1(dat["diametro_aro_eje"]),
    "Ø exterior total: %s mm" % f1(dat["diametro_exterior_total"]),
    "Altura del domo (eje): %s mm" % f1(dat["altura_domo_eje"]),
    "El domo es un casquete esférico de",
    "radio %s mm." % f1(dat["radio_esfera_domo"]),
    "",
    "## Secuencia sugerida",
    "1. Rolar el aro y soldar el empate.",
    "2. Marcar en el aro los %d puntos de V" % N,
    "   (cada %s°) y, si lleva, los %d de" % (f1(PASO), N),
    "   meridianos (corridos %s°)." % f1(geo["mer_offset_deg"]),
    "3. Fijar el disco central a %s mm de" % f1(dat["altura_domo_eje"]),
    "   altura, centrado (soporte provisional).",
    "4. Si lleva meridianos, soldarlos primero:",
    "   dan la forma del domo y sirven de guía.",
    "5. Soldar las %d curvas A (todas giran" % N,
    "   igual), luego las %d curvas B (volteadas)." % N,
    "6. Puntear todos los cruces entre varillas.",
    "7. Pulir soldaduras y pintar (polvo).",
], fs=8.6)
c.showPage()


# ---- Páginas 5+: plantillas 1:1 en hojas carta ----
def plantilla_tiles(c, R, A_deg, titulo, pag0):
    A = math.radians(A_deg)
    cuerda = 2 * R * math.sin(A / 2)
    flecha = R * (1 - math.cos(A / 2))
    margin = 8 * mm
    usable = W - 2 * margin
    total = cuerda + ROD + 20                      # mm
    n = max(1, math.ceil((total * mm - 20 * mm) / (usable - 20 * mm)))
    # ancho de cada tramo en mm de pieza, con 10 mm de traslape
    x_start = -total / 2
    step = (total - 10) / n
    for i in range(n):
        x_a = x_start + i * step
        x_b = x_a + step + 10
        cabecera(c, "%s – PLANTILLA 1:1 (hoja %d de %d)" % (titulo, i + 1, n),
                 "Imprimir al 100 %% (sin \"ajustar a página\"). Verifique que la barra mida 100 mm. "
                 "Unir las hojas haciendo coincidir las cruces de traslape.", "%d" % (pag0 + i))
        ox = margin - x_a * mm
        oy = 50 * mm
        c.saveState()
        p = c.beginPath()
        p.rect(margin, 18 * mm, usable, H - 44 * mm)
        c.clipPath(p, stroke=0, fill=0)
        dibujar_pieza(c, R, A_deg, ox, oy, mm, etiquetas=False, centro=False)
        # marcas de radio en los extremos (dirección al centro)
        yc = -R * math.cos(A / 2)
        c.setStrokeColor(ROJO)
        c.setLineWidth(0.4)
        for sgn in (-1, 1):
            ex, ey = sgn * cuerda / 2, 0.0
            dx, dy = (0 - ex), (yc - ey)
            L = math.hypot(dx, dy)
            c.line(ox + ex * mm, oy + ey * mm, ox + (ex + dx / L * 25) * mm, oy + (ey + dy / L * 25) * mm)
        # cruces de traslape
        c.setStrokeColor(NEGRO)
        c.setLineWidth(0.5)
        for xm in [x_start + j * step + 5 for j in range(1, n)]:
            for ym in (-14, flecha + 10):
                X, Y = ox + xm * mm, oy + ym * mm
                c.line(X - 4 * mm, Y, X + 4 * mm, Y)
                c.line(X, Y - 4 * mm, X, Y + 4 * mm)
            c.setDash(2, 2)
            c.line(ox + xm * mm, oy - 14 * mm, ox + xm * mm, oy + (flecha + 10) * mm)
            c.setDash()
        c.restoreState()
        c.setFont("Helvetica", 9)
        c.setFillColor(NEGRO)
        c.drawCentredString(W / 2, oy - 8 * mm, "%s · hoja %d/%d · cuerda %s mm · R %s mm al eje · %s° · varilla Ø%s" % (
            titulo, i + 1, n, f1(cuerda), f1(R), f1(A_deg), f1(ROD)))
        # barra de 100 mm
        bx, by = margin, 22 * mm
        c.setStrokeColor(NEGRO)
        c.setLineWidth(0.8)
        c.line(bx, by, bx + 100 * mm, by)
        for t in range(0, 101, 10):
            c.line(bx + t * mm, by, bx + t * mm, by + (3 if t % 50 else 5) * mm)
        c.setFont("Helvetica", 7.5)
        c.drawString(bx + 102 * mm, by, "100 mm")
        c.showPage()
    return pag0 + n


pag = plantilla_tiles(c, cu["radio_doblez_eje"], cu["angulo_arco_deg"], "Curva (pieza única)", 5)
if me["incluido"]:
    pag = plantilla_tiles(c, me["radio_doblez_eje"], me["angulo_arco_deg"], "Meridiano", pag)
c.save()

# ---------------------------------------------------------------------------
# Plantilla para plotter (una sola hoja)
# ---------------------------------------------------------------------------
PW = (cu["cuerda"] + 80) * mm
alto_c = cu["flecha"] + 45
alto_m = (me["flecha"] + 45) if me["incluido"] else 0
PH = (alto_c + alto_m + 40) * mm
cp = canvas.Canvas(os.path.join(D, "plantilla_1a1_plotter.pdf"), pagesize=(PW, PH))
cp.setTitle("Plantillas 1:1 – lámpara roseta")
cp.setFont("Helvetica-Bold", 11)
cp.drawString(10 * mm, PH - 10 * mm, "PLANTILLAS ESCALA 1:1 – imprimir al 100 %  ·  medidas en mm")
oy = PH - (18 + cu["flecha"] + 10) * mm
dibujar_pieza(cp, cu["radio_doblez_eje"], cu["angulo_arco_deg"], PW / 2, oy, mm, etiquetas=False, centro=False)
cp.setFont("Helvetica", 9)
cp.drawCentredString(PW / 2, oy - 7 * mm, "CURVA – hacer %d · R %s al eje · %s° · cuerda %s · largo %s · varilla Ø%s" % (
    NC, f1(cu["radio_doblez_eje"]), f1(cu["angulo_arco_deg"]), f1(cu["cuerda"]), f1(cu["largo_desarrollado_eje"]), f1(ROD)))
if me["incluido"]:
    oy2 = oy - (25 + me["flecha"]) * mm
    dibujar_pieza(cp, me["radio_doblez_eje"], me["angulo_arco_deg"], PW / 2, oy2, mm, etiquetas=False, centro=False)
    cp.drawCentredString(PW / 2, oy2 - 7 * mm, "MERIDIANO (opcional) – hacer %d · R %s al eje · %s° · cuerda %s · largo %s" % (
        N, f1(me["radio_doblez_eje"]), f1(me["angulo_arco_deg"]), f1(me["cuerda"]), f1(me["largo_desarrollado_eje"])))
bx, by = 10 * mm, 8 * mm
cp.setLineWidth(0.8)
cp.line(bx, by, bx + 100 * mm, by)
for t in range(0, 101, 10):
    cp.line(bx + t * mm, by, bx + t * mm, by + (3 if t % 50 else 5) * mm)
cp.drawString(bx + 102 * mm, by, "100 mm (verificar)")
cp.save()


# ---------------------------------------------------------------------------
# DXF (R12, mm)
# ---------------------------------------------------------------------------
class DXF:
    def __init__(self):
        self.e = []

    def _g(self, *kv):
        for k, v in zip(kv[::2], kv[1::2]):
            self.e.append("%d\n%s\n" % (k, ("%.4f" % v) if isinstance(v, float) else v))

    def line(self, p, q, layer="0"):
        self._g(0, "LINE", 8, layer, 10, float(p[0]), 20, float(p[1]), 30, 0.0, 11, float(q[0]), 21, float(q[1]), 31, 0.0)

    def circle(self, c, r, layer="0"):
        self._g(0, "CIRCLE", 8, layer, 10, float(c[0]), 20, float(c[1]), 30, 0.0, 40, float(r))

    def arc(self, c, r, a0, a1, layer="0"):
        self._g(0, "ARC", 8, layer, 10, float(c[0]), 20, float(c[1]), 30, 0.0, 40, float(r), 50, float(a0), 51, float(a1))

    def text(self, p, h, s, layer="TEXTO"):
        self._g(0, "TEXT", 8, layer, 10, float(p[0]), 20, float(p[1]), 30, 0.0, 40, float(h), 1, s)

    def polyline(self, pts, layer="0"):
        self._g(0, "POLYLINE", 8, layer, 66, 1, 70, 0)
        for x, y in pts:
            self._g(0, "VERTEX", 8, layer, 10, float(x), 20, float(y), 30, 0.0)
        self._g(0, "SEQEND", 8, layer)

    def save(self, path):
        with open(path, "w", encoding="ascii", errors="replace") as f:
            f.write("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n")
            f.write("0\nSECTION\n2\nENTITIES\n")
            f.write("".join(self.e))
            f.write("0\nENDSEC\n0\nEOF\n")


def dxf_pieza(path, R, A_deg, nombre, cant):
    d = DXF()
    A = A_deg
    a0, a1 = 90 - A / 2, 90 + A / 2
    yc = -R * math.cos(math.radians(A / 2))
    r = ROD / 2
    d.arc((0, yc), R, a0, a1, "EJE")
    d.arc((0, yc), R + r, a0, a1, "CONTORNO")
    d.arc((0, yc), R - r, a0, a1, "CONTORNO")
    for ang in (a0, a1):
        t = math.radians(ang)
        d.line((((R + r) * math.cos(t)), yc + (R + r) * math.sin(t)),
               (((R - r) * math.cos(t)), yc + (R - r) * math.sin(t)), "CONTORNO")
    cuerda = 2 * R * math.sin(math.radians(A / 2))
    d.line((-cuerda / 2, 0), (cuerda / 2, 0), "REFERENCIA")
    d.circle((0, yc), 2.0, "REFERENCIA")
    d.text((-cuerda / 2, -25), 8, "%s - cantidad %d - varilla D%s mm" % (nombre, cant, f1(ROD)))
    d.text((-cuerda / 2, -38), 6, "R eje %.2f mm  angulo %.2f deg  cuerda %.2f mm  largo %.2f mm" % (
        R, A, cuerda, R * math.radians(A)))
    d.save(path)


dxf_pieza(os.path.join(D, "curva_unica.dxf"), cu["radio_doblez_eje"], cu["angulo_arco_deg"], "CURVA", NC)
if me["incluido"]:
    dxf_pieza(os.path.join(D, "meridiano.dxf"), me["radio_doblez_eje"], me["angulo_arco_deg"], "MERIDIANO", N)

d = DXF()
d.circle((0, 0), ar["diam_exterior"] / 2, "ARO")
d.circle((0, 0), ar["diam_interior"] / 2, "ARO")
d.circle((0, 0), a, "ARO_EJE")
d.circle((0, 0), dat["disco"]["diametro"] / 2, "DISCO")
for k in range(N):
    for lado in "AB":
        d.polyline(arco_k(k, lado), "CURVAS")
    t = math.radians(k * PASO)
    d.text(((a + 30) * math.cos(t), (a + 30) * math.sin(t)), 8, "%d" % round(k * PASO))
    if me["incluido"]:
        t = math.radians(geo["mer_offset_deg"] + k * PASO)
        r0 = geo["radio_fin_centro"]
        d.line((r0 * math.cos(t), r0 * math.sin(t)), (a * math.cos(t), a * math.sin(t)), "MERIDIANOS")
d.save(os.path.join(D, "planta_armado.dxf"))

print("PDF y DXF listos en", D, "- páginas:", pag - 1)
