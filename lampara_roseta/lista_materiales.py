"""
Lista de piezas y de material para varias lámparas roseta (PDF).

Lee las medidas de datos_pieza.json (las que genera generar_lampara.py) y
calcula, para N lámparas, cuántas piezas hacen falta y cuántas barras comprar.

Uso:  python3 lista_materiales.py [N_LAMPARAS]      (por defecto 9)
"""

import json
import math
import os
import sys
import tempfile

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

AQUI = os.path.dirname(os.path.abspath(__file__))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 9
dat = json.load(open(os.path.join(AQUI, "datos_pieza.json"), encoding="utf-8"))
cu, me, aro, disco = dat["curva"], dat["meridiano"], dat["aro"], dat["disco"]
D, H, ROD = dat["diametro_aro_eje"], dat["altura_domo_eje"], dat["diam_varilla"]
PET = dat["n_petalos"]

# ---------------- cálculos de taller ----------------
BARRA = 6000.0      # barras de 6 m
DISCO_CORTE = 3.0   # pérdida por corte (disco de corte)
RHO = 7.85e-6       # acero, kg/mm3


def corte(largo):
    return math.ceil((largo + 30) / 10) * 10      # sobrante para recortar las puntas


def por_barra(c):
    return int(BARRA // (c + DISCO_CORTE))


def horma(R):
    k = 3.395 * 250 / (200000 * ROD)              # retorno elástico, acero 1020/A36
    return 1 / (1 / R + k) - ROD / 2


q_cur = N * dat["n_curvas"]
q_mer = N * PET if me["incluido"] else 0
c_cur, c_mer = corte(cu["largo_desarrollado_eje"]), corte(me["largo_desarrollado_eje"])
pb_cur, pb_mer = por_barra(c_cur), por_barra(c_mer)
def barras(q, pb):
    """Barras necesarias dejando al menos un 1 % de piezas de repuesto (pruebas y errores)."""
    if not q:
        return 0
    b = math.ceil(q / pb)
    if b * pb - q < max(1, math.ceil(q * 0.01)):
        b += 1
    return b


b_cur = barras(q_cur, pb_cur)
b_mer = barras(q_mer, pb_mer)
rep_cur = b_cur * pb_cur - q_cur
largo_aro = aro["largo_desarrollado_eje"]
aros_por_barra = int(BARRA // (largo_aro + 50))
b_aro = math.ceil(N / aros_por_barra)
kg_m_rod = math.pi * (ROD / 2) ** 2 * RHO * 1000
kg_m_ple = aro["ancho"] * aro["espesor"] * RHO * 1000
kg_lamp = ((dat["n_curvas"] * cu["largo_desarrollado_eje"] + (PET * me["largo_desarrollado_eje"] if me["incluido"] else 0)) * kg_m_rod / 1000
           + largo_aro * kg_m_ple / 1000 + math.pi * (disco["diametro"] / 2) ** 2 * disco["espesor"] * RHO)
kg_varilla = (b_cur + b_mer) * 6 * kg_m_rod
kg_pletina = b_aro * 6 * kg_m_ple

# ---------------- tipografía ----------------
F = {"disp": "Helvetica-Bold", "semi": "Helvetica-Bold", "body": "Helvetica", "bold": "Helvetica-Bold", "mono": "Courier", "monob": "Courier-Bold"}
try:
    from fontTools.ttLib import TTFont as FTFont
    src = os.path.join(AQUI, "video", "public", "fonts")
    tmp = tempfile.mkdtemp()
    for alias, fn in [("disp", "BarlowCondensed-700"), ("semi", "BarlowCondensed-600"), ("body", "Barlow-400"),
                      ("bold", "Barlow-600"), ("mono", "IBMPlexMono-400"), ("monob", "IBMPlexMono-500")]:
        t = FTFont(os.path.join(src, fn + ".woff2"))
        t.flavor = None
        out = os.path.join(tmp, fn + ".ttf")
        t.save(out)
        pdfmetrics.registerFont(TTFont(fn, out))
        F[alias] = fn
except Exception as e:  # sin fontTools/brotli: Helvetica
    print("Aviso: uso Helvetica (", e, ")")

INK = colors.HexColor("#15181c")
MUTED = colors.HexColor("#59626c")
LINE = colors.HexColor("#ccd2d8")
BRASS = colors.HexColor("#855818")
SOFT = colors.HexColor("#f3ede1")
ROD_C = colors.HexColor("#bf9455")
COTA = colors.HexColor("#b3332b")
EJE = colors.HexColor("#285fa3")


def n0(x):
    return f"{x:,.0f}".replace(",", ".")


def n1(x):
    s = f"{x:,.1f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


W, Hp = letter
M = 16 * mm
OUT = os.path.join(AQUI, f"lista_materiales_{N}_lamparas.pdf")
c = canvas.Canvas(OUT, pagesize=letter)
c.setTitle(f"Lámpara roseta · lista de materiales para {N} lámparas")


def text(x, y, s, font="body", size=10, color=INK, align="left"):
    c.setFont(F[font], size)
    c.setFillColor(color)
    if align == "right":
        c.drawRightString(x, y, s)
    elif align == "center":
        c.drawCentredString(x, y, s)
    else:
        c.drawString(x, y, s)


def wrap(x, y, s, width, font="body", size=10, color=INK, lead=1.35):
    words, line, lines = s.split(), "", []
    for w in words:
        t = (line + " " + w).strip()
        if pdfmetrics.stringWidth(t, F[font], size) <= width:
            line = t
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    for i, ln in enumerate(lines):
        text(x, y - i * size * lead, ln, font, size, color)
    return y - len(lines) * size * lead


def table(x, y, cols, rows, widths, size=9.2, row_h=7.4 * mm, head=True):
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    for i, r in enumerate([cols] + rows if head else rows):
        yy = y - i * row_h
        is_head = head and i == 0
        if is_head:
            c.setFillColor(SOFT)
            c.rect(x, yy - row_h + 2.2 * mm, sum(widths), row_h, stroke=0, fill=1)
        xx = x
        for j, (cell, w) in enumerate(zip(r, widths)):
            bold = is_head or (j == 0)
            font = "monob" if is_head else ("bold" if bold else "body")
            sz = size - 1.6 if is_head else size
            col = MUTED if is_head else INK
            if isinstance(cell, tuple):  # (texto, alineación)
                s, al = cell
            else:
                s, al = cell, "left"
            if al == "right":
                text(xx + w - 2 * mm, yy - row_h + 4.4 * mm, s, font, sz, col, "right")
            else:
                text(xx + 2 * mm, yy - row_h + 4.4 * mm, s, font, sz, col)
            xx += w
        c.line(x, yy - row_h + 2.2 * mm, x + sum(widths), yy - row_h + 2.2 * mm)
    return y - (len(rows) + (1 if head else 0)) * row_h


def footer(pag):
    c.setStrokeColor(LINE)
    c.line(M, 13 * mm, W - M, 13 * mm)
    text(M, 8.5 * mm, f"Lámpara roseta · {N} lámparas · aro Ø{n0(D)} al eje · domo {n0(H)} · medidas en mm", "body", 7.5, MUTED)
    text(W - M, 8.5 * mm, str(pag), "body", 7.5, MUTED, "right")


# ================= Página 1 · resumen y compra =================
y = Hp - M
text(M, y - 4 * mm, "LÁMPARA ROSETA · ESTRUCTURA EN VARILLA", "monob", 8, BRASS)
text(M, y - 17 * mm, f"{N} LÁMPARAS · Ø{n0(D / 10)} CM", "disp", 34, INK)
y = wrap(M, y - 25 * mm, f"Lista de piezas y de material. Aro de Ø{n0(D)} mm medido al centro de la pletina, donde se apoyan las varillas "
         f"(Ø{n0(aro['diam_exterior'])} por fuera). Domo de {n0(H)} mm de alto. Varilla lisa de Ø{n0(ROD)} mm.",
         W - 2 * M - 62 * mm, "body", 10.5, MUTED)
img = os.path.join(AQUI, "render_desde_abajo.png")
if os.path.exists(img):
    c.drawImage(img, W - M - 56 * mm, Hp - M - 42 * mm, 56 * mm, 42 * mm, preserveAspectRatio=True, anchor="c")

# cifras grandes
y = Hp - M - 54 * mm
tiles = [(n0(q_cur), "curvas", "las diagonales"), (n0(q_mer), "meridianos", "soporte de las tiras LED"),
         (n0(N), "aros", "el aro de abajo"), (n0(N), "discos", "el disco del centro")]
tw = (W - 2 * M - 3 * 4 * mm) / 4
for i, (num, lab, sub) in enumerate(tiles):
    x = M + i * (tw + 4 * mm)
    c.setFillColor(SOFT)
    c.roundRect(x, y - 27 * mm, tw, 27 * mm, 2.5 * mm, stroke=0, fill=1)
    text(x + 4 * mm, y - 13 * mm, num, "disp", 30, BRASS if i < 2 else INK)
    text(x + 4 * mm, y - 19 * mm, lab.upper(), "semi", 11.5, INK)
    text(x + 4 * mm, y - 23.6 * mm, sub, "body", 8, MUTED)

# piezas
y -= 36 * mm
text(M, y, "PIEZAS", "semi", 13, INK)
rows = [
    ["Curva (diagonal)", (str(dat["n_curvas"]), "right"), (n0(q_cur), "right"), f"Varilla Ø{n0(ROD)}",
     f"Arco plano R {n1(cu['radio_doblez_eje'])} · {n1(cu['angulo_arco_deg'])}° · largo {n1(cu['largo_desarrollado_eje'])}"],
]
if me["incluido"]:
    rows.append(["Meridiano (LED)", (str(PET), "right"), (n0(q_mer), "right"), f"Varilla Ø{n0(ROD)}",
                 f"Arco plano R {n1(me['radio_doblez_eje'])} · {n1(me['angulo_arco_deg'])}° · largo {n1(me['largo_desarrollado_eje'])}"])
rows += [
    ["Aro de abajo", ("1", "right"), (n0(N), "right"), f"Pletina {n0(aro['ancho'])}×{n0(aro['espesor'])}",
     f"Ø{n0(D)} al eje (int {n0(aro['diam_interior'])} / ext {n0(aro['diam_exterior'])}) · largo {n0(largo_aro)}"],
    ["Disco del centro", ("1", "right"), (n0(N), "right"), f"Lámina {n0(disco['espesor'])} mm",
     f"Ø{n0(disco['diametro'])} con perforación al centro para el cable"],
]
y = table(M, y - 3 * mm, ["PIEZA", ("POR LÁMPARA", "right"), (f"PARA {N}", "right"), "MATERIAL", "MEDIDAS (AL EJE DE LA VARILLA)"],
          rows, [33 * mm, 24 * mm, 20 * mm, 26 * mm, W - 2 * M - 103 * mm])

# compra
y -= 9 * mm
text(M, y, "LISTA DE COMPRA", "semi", 13, INK)
rows = [
    [f"Varilla lisa Ø{n0(ROD)} mm · 6 m", (f"{b_cur} barras", "right"),
     f"{n0(q_cur)} curvas: tramos de {n0(c_cur)}, {pb_cur} por barra, +{b_cur * pb_cur - q_cur} de repuesto"],
]
if q_mer:
    rows.append([f"Varilla lisa Ø{n0(ROD)} mm · 6 m", (f"{b_mer} barras", "right"),
                 f"{n0(q_mer)} meridianos: tramos de {n0(c_mer)}, {pb_mer} por barra, +{b_mer * pb_mer - q_mer} de repuesto"])
rows += [
    [f"Pletina {n0(aro['ancho'])} × {n0(aro['espesor'])} mm · 6 m", (f"{b_aro} barras", "right"),
     f"{N} aros de {n0(largo_aro)} mm, {aros_por_barra} por barra, +{b_aro * aros_por_barra - N} de repuesto"],
    [f"Lámina de acero {n0(disco['espesor'])} mm", ("60 × 60 cm", "right"), f"{N} discos de Ø{n0(disco['diametro'])} (o pedirlos cortados en láser)"],
]
y = table(M, y - 3 * mm, ["MATERIAL", ("CANTIDAD", "right"), "RINDE"], rows, [52 * mm, 28 * mm, W - 2 * M - 80 * mm])
y -= 4 * mm
text(M, y, f"Total: {b_cur + b_mer} barras de varilla Ø{n0(ROD)} ({n1(kg_varilla)} kg) y {b_aro} de pletina ({n1(kg_pletina)} kg). "
     f"Cada lámpara terminada pesa unos {n1(kg_lamp)} kg de acero; las {N}, {n0(kg_lamp * N)} kg.", "bold", 9.5, INK)

# notas
y -= 11 * mm
c.setFillColor(SOFT)
c.roundRect(M, y - 37 * mm, W - 2 * M, 39 * mm, 2.5 * mm, stroke=0, fill=1)
text(M + 5 * mm, y - 4 * mm, "PARA TENER EN CUENTA", "monob", 8, BRASS)
notas = [
    f"Las {n0(q_cur)} curvas son la misma pieza: un arco plano. En cada lámpara la mitad ({PET}) se monta volteada.",
    f"Varilla de Ø6 mm o de 1/4\" (6,35 mm): las dos sirven, porque el radio se mide al eje de la varilla.",
    f"Material más ajustado: cortando las curvas a {n0(c_cur - 5)} mm salen {por_barra(c_cur - 5)} por barra y bastan "
    f"{math.ceil((q_cur + rep_cur) / por_barra(c_cur - 5))} barras, pero queda menos sobrante para recortar las puntas.",
    "Si no hay roladora para la pletina de canto, el aro se puede cortar en láser de lámina de 5 mm; del centro sobrante salen los discos.",
]
yy = y - 10 * mm
for s in notas:
    text(M + 5 * mm, yy, "•", "bold", 9.5, BRASS)
    yy = wrap(M + 9 * mm, yy, s, W - 2 * M - 14 * mm, "body", 9.2, INK, 1.3) - 1.2 * mm
footer(1)
c.showPage()

# ================= Página 2 · las piezas y el corte =================
text(M, Hp - M - 4 * mm, "LAS 4 PIEZAS", "monob", 8, BRASS)
text(M, Hp - M - 15 * mm, "CÓMO ES CADA PIEZA", "disp", 26, INK)


def arc_drawing(x0, y0, w, h, R, ang_deg, d_rod):
    """Arco plano acostado: cuerda horizontal abajo, panza arriba, con cuerda y flecha."""
    half = math.radians(ang_deg) / 2
    chord, sag = 2 * R * math.sin(half), R * (1 - math.cos(half))
    s = min(w / (chord * 1.1), (h - 10 * mm) / sag)
    cx, base_y = x0 + w / 2, y0 + 7 * mm
    yc = base_y - R * math.cos(half) * s            # centro del doblez (fuera del dibujo)
    pts = [(cx + R * s * math.cos(t), yc + R * s * math.sin(t)) for t in [math.pi / 2 - half + 2 * half * i / 120 for i in range(121)]]
    c.setStrokeColor(ROD_C)
    c.setLineWidth(max(1.8, d_rod * s * 2.5))
    p = c.beginPath()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    c.drawPath(p, stroke=1, fill=0)
    c.setLineWidth(0.6)
    c.setStrokeColor(COTA)
    c.line(pts[0][0], base_y, pts[-1][0], base_y)
    c.line(cx, base_y, cx, base_y + sag * s)
    text(cx, base_y - 4.2 * mm, f"cuerda {n1(chord)}  ·  R {n1(R)}  ·  {n1(ang_deg)}°", "monob", 7.4, COTA, "center")
    text(cx + 1.5 * mm, base_y + sag * s * 0.4, f"flecha {n1(sag)}", "monob", 7.4, COTA)


def ring_drawing(x0, y0, w, h, d_ext, d_int, hole=False, label=None):
    r = min(w, h) / 2 * 0.86
    cx, cy = x0 + w / 2, y0 + h / 2
    c.setStrokeColor(ROD_C)
    c.setFillColor(ROD_C)
    if hole:
        c.circle(cx, cy, r, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.circle(cx, cy, r * 0.12, stroke=0, fill=1)
    else:
        c.setLineWidth(max(1.5, r * (d_ext - d_int) / d_ext))
        c.circle(cx, cy, r * (d_ext + d_int) / (2 * d_ext), stroke=1, fill=0)
    c.setStrokeColor(COTA)
    c.setLineWidth(0.6)
    c.line(cx - r, cy, cx + r, cy)
    text(cx, cy + 2 * mm, label or f"Ø{n0(d_ext)}", "monob", 8, COTA, "center")


cells = [
    ("CURVA · DIAGONAL", f"Hacer {n0(q_cur)}", lambda x, y, w, h: arc_drawing(x, y, w, h, cu["radio_doblez_eje"], cu["angulo_arco_deg"], ROD),
     [f"Varilla lisa Ø{n0(ROD)} · arco plano", f"Radio al eje {n1(cu['radio_doblez_eje'])} · {n1(cu['angulo_arco_deg'])}°",
      f"Largo {n1(cu['largo_desarrollado_eje'])} · corte {n0(c_cur)}", f"Cuerda {n1(cu['cuerda'])} · flecha {n1(cu['flecha'])}",
      f"Horma aprox. R {n0(horma(cu['radio_doblez_eje']))}"]),
]
if me["incluido"]:
    cells.append(("MERIDIANO · LED", f"Hacer {n0(q_mer)}", lambda x, y, w, h: arc_drawing(x, y, w, h, me["radio_doblez_eje"], me["angulo_arco_deg"], ROD),
                  [f"Varilla lisa Ø{n0(ROD)} · arco plano", f"Radio al eje {n1(me['radio_doblez_eje'])} · {n1(me['angulo_arco_deg'])}°",
                   f"Largo {n1(me['largo_desarrollado_eje'])} · corte {n0(c_mer)}", f"Cuerda {n1(me['cuerda'])} · flecha {n1(me['flecha'] if 'flecha' in me else me['radio_doblez_eje'] * (1 - math.cos(math.radians(me['angulo_arco_deg']) / 2)))}",
                   f"Horma aprox. R {n0(horma(me['radio_doblez_eje']))}"]))
cells += [
    ("ARO DE ABAJO", f"Hacer {n0(N)}", lambda x, y, w, h: ring_drawing(x, y, w, h, aro["diam_exterior"], aro["diam_interior"], label=f"Ø{n0(D)} al eje"),
     [f"Pletina {n0(aro['ancho'])} × {n0(aro['espesor'])} acostada", f"Ø{n0(D)} al eje de las varillas", f"Interior {n0(aro['diam_interior'])} · exterior {n0(aro['diam_exterior'])}",
      f"Largo al eje {n0(largo_aro)} · empate soldado", f"{PET} puntos de V cada {n1(360 / PET)}°"]),
    ("DISCO DEL CENTRO", f"Hacer {n0(N)}", lambda x, y, w, h: ring_drawing(x, y, w, h, disco["diametro"], 0, hole=True),
     [f"Lámina de {n0(disco['espesor'])} mm", f"Ø{n0(disco['diametro'])}", "Perforación al centro para el cable", "Las curvas terminan a r 70 mm,", "apoyadas y soldadas encima"]),
]
gx, gy, gw, gh = M, Hp - M - 24 * mm, (W - 2 * M - 6 * mm) / 2, 70 * mm
for i, (title, qty, draw, lines) in enumerate(cells):
    x = gx + (i % 2) * (gw + 6 * mm)
    ytop = gy - (i // 2) * (gh + 6 * mm)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.8)
    c.roundRect(x, ytop - gh, gw, gh, 2.5 * mm, stroke=1, fill=0)
    text(x + 4 * mm, ytop - 7 * mm, title, "semi", 12, INK)
    text(x + gw - 4 * mm, ytop - 7 * mm, qty, "disp", 14, BRASS, "right")
    draw(x + 3 * mm, ytop - gh + 25 * mm, gw - 6 * mm, gh - 36 * mm)
    yy = ytop - gh + 21 * mm
    for ln in lines:
        text(x + 4 * mm, yy, ln, "body", 8.4, INK)
        yy -= 3.9 * mm

# plan de corte
y = gy - 2 * (gh + 6 * mm) - 4 * mm
text(M, y, "PLAN DE CORTE POR BARRA DE 6 m", "semi", 13, INK)
y -= 6 * mm
bars = [(f"Curvas: {pb_cur} tramos de {n0(c_cur)}", c_cur, pb_cur, BRASS)]
if q_mer:
    bars.append((f"Meridianos: {pb_mer} tramos de {n0(c_mer)}", c_mer, pb_mer, ROD_C))
bars.append((f"Aros: {aros_por_barra} de {n0(largo_aro)}", largo_aro, aros_por_barra, colors.HexColor("#8a8f96")))
bw = W - 2 * M
for label, L, k, col in bars:
    text(M, y, label, "bold", 9, INK)
    sobra = BARRA - k * (L + DISCO_CORTE)
    text(M + bw, y, f"sobran {n0(sobra)} mm", "body", 8.5, MUTED, "right")
    yb = y - 6 * mm
    sc = bw / BARRA
    for j in range(k):
        x0 = M + j * (L + DISCO_CORTE) * sc
        c.setFillColor(col)
        c.rect(x0, yb, max(0.5, L * sc - 1.4), 3.2 * mm, stroke=0, fill=1)
    c.setFillColor(LINE)
    c.rect(M + k * (L + DISCO_CORTE) * sc, yb, max(0.5, sobra * sc), 3.2 * mm, stroke=0, fill=1)
    y -= 13 * mm
footer(2)
c.save()
print("PDF:", OUT)
print(f"curvas {q_cur} ({b_cur} barras) · meridianos {q_mer} ({b_mer} barras) · aros {N} ({b_aro} barras pletina) · discos {N}")
print(f"kg por lámpara {kg_lamp:.2f} · total {kg_lamp * N:.1f} · varilla comprada {kg_varilla:.1f} kg · pletina {kg_pletina:.1f} kg")
