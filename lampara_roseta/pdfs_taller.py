"""
Documentos para los dos proveedores de la lámpara roseta, para N lámparas.

  1. corte_laser_{N}_lamparas.pdf   Metal Cortes: aros y discos en lámina de acero de 5 mm,
                                    con los DXF 1:1 en la carpeta corte_laser/
  2. curvas_{N}_lamparas.pdf        curvas (diagonales) y meridianos (LED) en varilla lisa Ø6,
                                    con las plantillas 1:1 al final

Lee las medidas de datos_pieza.json (las genera generar_lampara.py).
Uso:  python3 pdfs_taller.py [N]          (por defecto 9)
"""

import io
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
D, H, ROD, PET = dat["diametro_aro_eje"], dat["altura_domo_eje"], dat["diam_varilla"], dat["n_petalos"]
PASO = 360 / PET
MER_OFF = me.get("angulo_primer_meridiano_deg", PASO / 2)
R_FIN = cu["extremo_centro_r_ang_z"][0]          # radio donde terminan las curvas sobre el disco
me.setdefault("flecha", me["radio_doblez_eje"] * (1 - math.cos(math.radians(me["angulo_arco_deg"]) / 2)))

# ---------------- cálculos de taller ----------------
BARRA, KERF, RHO = 6000.0, 3.0, 7.85e-6
HOLE = 10.5                     # perforación del disco: niple roscado M10 de lámpara
NOTCH_W, NOTCH_D = 2.0, 1.5     # muescas de ubicación (ancho, profundidad)


def corte(largo):
    return math.ceil((largo + 30) / 10) * 10


def por_barra(c):
    return int(BARRA // (c + KERF))


def barras(q, pb):
    if not q:
        return 0
    b = math.ceil(q / pb)
    if b * pb - q < max(1, math.ceil(q * 0.01)):      # al menos 1 % de repuesto
        b += 1
    return b


def horma(R):
    k = 3.395 * 250 / (200000 * ROD)                  # retorno elástico, acero 1020/A36
    return 1 / (1 / R + k) - ROD / 2


q_cur, q_mer = N * dat["n_curvas"], (N * PET if me["incluido"] else 0)
c_cur, c_mer = corte(cu["largo_desarrollado_eje"]), corte(me["largo_desarrollado_eje"])
pb_cur, pb_mer = por_barra(c_cur), por_barra(c_mer)
b_cur, b_mer = barras(q_cur, pb_cur), barras(q_mer, pb_mer)
kg_m_rod = math.pi * (ROD / 2) ** 2 * RHO * 1000
R_EXT, R_INT, T = aro["diam_exterior"] / 2, aro["diam_interior"] / 2, aro["espesor"]
kg_aro = math.pi * (R_EXT ** 2 - R_INT ** 2) * T * RHO
kg_disco = math.pi * ((disco["diametro"] / 2) ** 2 - (HOLE / 2) ** 2) * disco["espesor"] * RHO
SHEETS = [(1220, 2440), (1500, 3000)]
GAP = 10.0


def aros_por_lamina(w, h):
    cell = 2 * R_EXT + GAP
    return int((max(w, h) - GAP) // cell) * int((min(w, h) - GAP) // cell)


# ---------------- tipografía y estilo ----------------
F = {"disp": "Helvetica-Bold", "semi": "Helvetica-Bold", "body": "Helvetica", "bold": "Helvetica-Bold", "mono": "Courier", "monob": "Courier-Bold"}
try:
    from fontTools.ttLib import TTFont as FTFont
    src, tmp = os.path.join(AQUI, "video", "public", "fonts"), tempfile.mkdtemp()
    for alias, fn in [("disp", "BarlowCondensed-700"), ("semi", "BarlowCondensed-600"), ("body", "Barlow-400"),
                      ("bold", "Barlow-600"), ("mono", "IBMPlexMono-400"), ("monob", "IBMPlexMono-500")]:
        t = FTFont(os.path.join(src, fn + ".woff2"))
        t.flavor = None
        t.save(os.path.join(tmp, fn + ".ttf"))
        pdfmetrics.registerFont(TTFont(fn, os.path.join(tmp, fn + ".ttf")))
        F[alias] = fn
except Exception as e:
    print("Aviso: uso Helvetica (", e, ")")

INK, MUTED, LINE = colors.HexColor("#15181c"), colors.HexColor("#59626c"), colors.HexColor("#ccd2d8")
BRASS, SOFT, ROD_C = colors.HexColor("#855818"), colors.HexColor("#f3ede1"), colors.HexColor("#bf9455")
COTA, EJE, PLATE = colors.HexColor("#b3332b"), colors.HexColor("#285fa3"), colors.HexColor("#8d949c")
W, Hp = letter
M = 16 * mm


def n0(x):
    return f"{x:,.0f}".replace(",", ".")


def n1(x):
    return f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


class Doc:
    def __init__(self, path, title, foot):
        self.c = canvas.Canvas(path, pagesize=letter)
        self.c.setTitle(title)
        self.foot, self.page, self.path = foot, 1, path

    def text(self, x, y, s, font="body", size=10, color=INK, align="left"):
        c = self.c
        c.setFont(F[font], size)
        c.setFillColor(color)
        {"right": c.drawRightString, "center": c.drawCentredString}.get(align, c.drawString)(x, y, s)

    def wrap(self, x, y, s, width, font="body", size=10, color=INK, lead=1.35):
        line, lines = "", []
        for w in s.split():
            t = (line + " " + w).strip()
            if pdfmetrics.stringWidth(t, F[font], size) <= width:
                line = t
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        for i, ln in enumerate(lines):
            self.text(x, y - i * size * lead, ln, font, size, color)
        return y - len(lines) * size * lead

    def table(self, x, y, cols, rows, widths, size=9.2, row_h=7.4 * mm):
        c = self.c
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        for i, r in enumerate([cols] + rows):
            yy, head = y - i * row_h, i == 0
            if head:
                c.setFillColor(SOFT)
                c.rect(x, yy - row_h + 2.2 * mm, sum(widths), row_h, stroke=0, fill=1)
            xx = x
            for j, (cell, w) in enumerate(zip(r, widths)):
                s, al = cell if isinstance(cell, tuple) else (cell, "left")
                font = "monob" if head else ("bold" if j == 0 else "body")
                sz, col = (size - 1.6, MUTED) if head else (size, INK)
                if al == "right":
                    self.text(xx + w - 2 * mm, yy - row_h + 4.4 * mm, s, font, sz, col, "right")
                else:
                    self.text(xx + 2 * mm, yy - row_h + 4.4 * mm, s, font, sz, col)
                xx += w
            c.line(x, yy - row_h + 2.2 * mm, x + sum(widths), yy - row_h + 2.2 * mm)
        return y - (len(rows) + 1) * row_h

    def tiles(self, y, items):
        tw = (W - 2 * M - (len(items) - 1) * 4 * mm) / len(items)
        for i, (num, lab, sub, accent) in enumerate(items):
            x = M + i * (tw + 4 * mm)
            self.c.setFillColor(SOFT)
            self.c.roundRect(x, y - 27 * mm, tw, 27 * mm, 2.5 * mm, stroke=0, fill=1)
            self.text(x + 4 * mm, y - 13 * mm, num, "disp", 28, BRASS if accent else INK)
            self.text(x + 4 * mm, y - 19 * mm, lab.upper(), "semi", 11, INK)
            self.text(x + 4 * mm, y - 23.6 * mm, sub, "body", 7.8, MUTED)
        return y - 27 * mm

    def header(self, eyebrow, title, sub=None, width=None):
        y = Hp - M
        self.text(M, y - 4 * mm, eyebrow, "monob", 8, BRASS)
        self.text(M, y - 16.5 * mm, title, "disp", 30, INK)
        if sub:
            return self.wrap(M, y - 24 * mm, sub, width or (W - 2 * M), "body", 10.2, MUTED)
        return y - 20 * mm

    def notes(self, y, title, items, h=None):
        c = self.c
        lines_h = sum(len(self._split(s, W - 2 * M - 14 * mm, 9.0)) * 9.0 * 1.3 + 3.4 for s in items)
        h = h or (lines_h + 12 * mm)
        c.setFillColor(SOFT)
        c.roundRect(M, y - h, W - 2 * M, h, 2.5 * mm, stroke=0, fill=1)
        self.text(M + 5 * mm, y - 6 * mm, title, "monob", 8, BRASS)
        yy = y - 12 * mm
        for s in items:
            self.text(M + 5 * mm, yy, "•", "bold", 9.5, BRASS)
            yy = self.wrap(M + 9 * mm, yy, s, W - 2 * M - 14 * mm, "body", 9.0, INK, 1.3) - 1.2 * mm
        return y - h

    def _split(self, s, width, size):
        line, lines = "", []
        for w in s.split():
            t = (line + " " + w).strip()
            if pdfmetrics.stringWidth(t, F["body"], size) <= width:
                line = t
            else:
                lines.append(line)
                line = w
        return lines + ([line] if line else [])

    def next_page(self):
        self.footer()
        self.c.showPage()
        self.page += 1

    def footer(self):
        self.c.setStrokeColor(LINE)
        self.c.line(M, 13 * mm, W - M, 13 * mm)
        self.text(M, 8.5 * mm, self.foot, "body", 7.5, MUTED)
        self.text(W - M, 8.5 * mm, str(self.page), "body", 7.5, MUTED, "right")

    def save(self):
        self.footer()
        self.c.save()


# ---------------- dibujos ----------------
def arc_drawing(d, x0, y0, w, h, R, ang_deg, show_center=False):
    """Arco plano acostado (cuerda abajo, panza arriba) con sus cotas."""
    c = d.c
    half = math.radians(ang_deg) / 2
    chord, sag = 2 * R * math.sin(half), R * (1 - math.cos(half))
    tall = R if show_center else sag
    s = min(w / (chord * 1.12), (h - 14 * mm) / tall)
    cx = x0 + w / 2
    base_y = y0 + 8 * mm + (R * math.cos(half) * s if show_center else 0)
    yc = base_y - R * math.cos(half) * s
    pts = [(cx + R * s * math.cos(t), yc + R * s * math.sin(t)) for t in [math.pi / 2 - half + 2 * half * i / 160 for i in range(161)]]
    if show_center:
        c.setDash(2, 2)
        c.setStrokeColor(MUTED)
        c.setLineWidth(0.6)
        c.line(cx, yc, pts[0][0], pts[0][1])
        c.line(cx, yc, pts[-1][0], pts[-1][1])
        c.setDash()
        c.circle(cx, yc, 0.9 * mm, stroke=1, fill=0)
        d.text(cx, yc - 4.5 * mm, "centro del doblez", "body", 7.5, MUTED, "center")
        d.text(cx + (pts[0][0] - cx) * 0.55 + 2 * mm, yc + (pts[0][1] - yc) * 0.55 - 3 * mm, f"R {n1(R)} al eje", "monob", 7.5, MUTED)
        d.text(cx, yc + 6 * mm, f"{n1(ang_deg)}°", "monob", 8, COTA, "center")
    c.setStrokeColor(ROD_C)
    c.setLineWidth(max(2.0, ROD * s * 2.4))
    p = c.beginPath()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    c.drawPath(p, stroke=1, fill=0)
    c.setStrokeColor(COTA)
    c.setLineWidth(0.6)
    c.line(pts[0][0], base_y, pts[-1][0], base_y)
    c.line(cx, base_y, cx, base_y + sag * s)
    d.text(cx, base_y - 4.4 * mm, f"cuerda {n1(chord)}", "monob", 8, COTA, "center")
    d.text(cx + 1.6 * mm, base_y + sag * s * 0.42, f"flecha {n1(sag)}", "monob", 8, COTA)
    if not show_center:
        d.text(cx, base_y + sag * s + 4 * mm, f"R {n1(R)} al eje · {n1(ang_deg)}°", "monob", 8, MUTED, "center")
    d.text(cx, base_y + sag * s + (9 if not show_center else 4) * mm, f"largo {n1(R * math.radians(ang_deg))} por el eje", "monob", 8, INK, "center")


def ring_drawing(d, cx, cy, r_draw, marks=True):
    """Aro visto desde arriba con cotas y, opcional, las muescas de ubicación."""
    c = d.c
    k = r_draw / R_EXT
    c.setFillColor(PLATE)
    p = c.beginPath()
    p.circle(cx, cy, R_EXT * k)
    p.circle(cx, cy, R_INT * k)
    c.drawPath(p, stroke=0, fill=1, fillMode=0)  # par-impar: deja el hueco
    if marks:
        c.setStrokeColor(colors.white)
        c.setLineWidth(1.0)
        for i in range(PET):
            a = math.radians(i * PASO)
            c.line(cx + R_INT * k * math.cos(a), cy + R_INT * k * math.sin(a), cx + (R_INT * k + 1.6 * mm) * math.cos(a), cy + (R_INT * k + 1.6 * mm) * math.sin(a))
            b = math.radians(MER_OFF + i * PASO)
            c.line(cx + R_EXT * k * math.cos(b), cy + R_EXT * k * math.sin(b), cx + (R_EXT * k - 1.6 * mm) * math.cos(b), cy + (R_EXT * k - 1.6 * mm) * math.sin(b))
    c.setStrokeColor(COTA)
    c.setLineWidth(0.6)
    c.line(cx - R_EXT * k, cy + R_EXT * k + 4 * mm, cx + R_EXT * k, cy + R_EXT * k + 4 * mm)
    d.text(cx, cy + R_EXT * k + 6 * mm, f"Ø exterior {n0(2 * R_EXT)}", "monob", 8, COTA, "center")
    c.line(cx - R_INT * k, cy, cx + R_INT * k, cy)
    d.text(cx, cy + 2 * mm, f"Ø interior {n0(2 * R_INT)}", "monob", 8, COTA, "center")
    d.text(cx, cy - 5 * mm, f"ancho {n0(R_EXT - R_INT)} · espesor {n0(T)}", "monob", 8, MUTED, "center")


def disc_drawing(d, cx, cy, r_draw, marks=True):
    c = d.c
    rd = disco["diametro"] / 2
    k = r_draw / rd
    c.setFillColor(PLATE)
    p = c.beginPath()
    p.circle(cx, cy, rd * k)
    p.circle(cx, cy, HOLE / 2 * k)
    c.drawPath(p, stroke=0, fill=1, fillMode=0)  # par-impar: deja el hueco
    if marks:
        c.setStrokeColor(colors.white)
        c.setLineWidth(1.0)
        for i in range(PET):
            b = math.radians(MER_OFF + i * PASO)
            c.line(cx + rd * k * math.cos(b), cy + rd * k * math.sin(b), cx + (rd * k - 1.8 * mm) * math.cos(b), cy + (rd * k - 1.8 * mm) * math.sin(b))
    c.setStrokeColor(COTA)
    c.setLineWidth(0.6)
    c.line(cx - rd * k, cy - rd * k - 4 * mm, cx + rd * k, cy - rd * k - 4 * mm)
    d.text(cx, cy - rd * k - 8.5 * mm, f"Ø {n0(disco['diametro'])} · espesor {n0(disco['espesor'])}", "monob", 8, COTA, "center")
    d.text(cx, cy - rd * k - 12.5 * mm, f"perforación central Ø{n1(HOLE)}", "monob", 8, COTA, "center")


# ---------------- DXF (R12, mm) ----------------
class DXF:
    def __init__(self):
        self.e = []

    def g(self, *kv):
        for k, v in zip(kv[::2], kv[1::2]):
            self.e.append(f"{k}\n{v:.10f}\n" if isinstance(v, float) else f"{k}\n{v}\n")

    def circle(self, x, y, r, layer="CORTE"):
        self.g(0, "CIRCLE", 8, layer, 10, float(x), 20, float(y), 30, 0.0, 40, float(r))

    def line(self, x1, y1, x2, y2, layer):
        self.g(0, "LINE", 8, layer, 10, float(x1), 20, float(y1), 30, 0.0, 11, float(x2), 21, float(y2), 31, 0.0)

    def polyline(self, verts, layer="CORTE"):
        """verts: [(x, y, bulge)], cerrada."""
        self.g(0, "POLYLINE", 8, layer, 66, "1", 70, "1")
        for x, y, b in verts:
            self.g(0, "VERTEX", 8, layer, 10, float(x), 20, float(y), 30, 0.0, 42, float(b))
        self.g(0, "SEQEND", 8, layer)

    def save(self, path):
        with open(path, "w", encoding="ascii") as f:
            f.write("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n")
            f.write("".join(self.e))
            f.write("0\nENDSEC\n0\nEOF\n")


def notched_circle(r, angles_deg, outward, cx=0.0, cy=0.0):
    """Círculo cerrado con muescas en V hacia el material (outward=True: hacia afuera del radio)."""
    half = math.degrees((NOTCH_W / 2) / r)
    depth = NOTCH_D if outward else -NOTCH_D
    pts = []
    angs = sorted(a % 360 for a in angles_deg)
    for i, a in enumerate(angs):
        nxt = angs[(i + 1) % len(angs)] + (360 if i + 1 == len(angs) else 0)
        a0, a1 = a - half, a + half
        span = (nxt - half) - a1                      # arco hasta la próxima muesca (CCW)
        pts.append((cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0)), 0.0))
        pts.append((cx + (r + depth) * math.cos(math.radians(a)), cy + (r + depth) * math.sin(math.radians(a)), 0.0))
        pts.append((cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1)), math.tan(math.radians(span) / 4)))
    return pts


def write_dxfs(folder):
    os.makedirs(folder, exist_ok=True)
    v_angles = [i * PASO for i in range(PET)]                 # puntos de V de las curvas
    m_angles = [MER_OFF + i * PASO for i in range(PET)]       # meridianos
    d = DXF(); d.circle(0, 0, R_EXT); d.circle(0, 0, R_INT); d.save(os.path.join(folder, "aro_laser.dxf"))
    d = DXF(); d.polyline(notched_circle(R_EXT, m_angles, outward=False)); d.polyline(notched_circle(R_INT, v_angles, outward=True))
    d.save(os.path.join(folder, "aro_laser_con_marcas.dxf"))
    rd = disco["diametro"] / 2
    d = DXF(); d.circle(0, 0, rd); d.circle(0, 0, HOLE / 2); d.save(os.path.join(folder, "disco_laser.dxf"))
    d = DXF(); d.polyline(notched_circle(rd, m_angles, outward=False)); d.circle(0, 0, HOLE / 2)
    d.save(os.path.join(folder, "disco_laser_con_marcas.dxf"))
    # acomodo sugerido en lámina de 1220 x 2440: 2 aros y los discos dentro de uno de ellos
    sw, sh = SHEETS[0][1], SHEETS[0][0]
    d = DXF()
    for (x1, y1, x2, y2) in [(0, 0, sw, 0), (sw, 0, sw, sh), (sw, sh, 0, sh), (0, sh, 0, 0)]:
        d.line(x1, y1, x2, y2, "LAMINA_REFERENCIA")
    centers = [(GAP + R_EXT, GAP + R_EXT), (2 * GAP + 3 * R_EXT, GAP + R_EXT)]
    for (x, y) in centers:
        d.circle(x, y, R_EXT); d.circle(x, y, R_INT)
    cell = disco["diametro"] + GAP
    for i in range(3):
        for j in range(3):
            x, y = centers[0][0] + (i - 1) * cell, centers[0][1] + (j - 1) * cell
            d.circle(x, y, rd); d.circle(x, y, HOLE / 2)
    d.save(os.path.join(folder, "lamina_1220x2440_acomodo_sugerido.dxf"))
    return ["aro_laser.dxf", "aro_laser_con_marcas.dxf", "disco_laser.dxf", "disco_laser_con_marcas.dxf", "lamina_1220x2440_acomodo_sugerido.dxf"]


# =====================================================================
# 1 · CORTE LÁSER (Metal Cortes)
# =====================================================================
dxfs = write_dxfs(os.path.join(AQUI, "corte_laser"))
foot = f"Lámpara roseta · corte láser · {N} lámparas · acero de {n0(T)} mm · medidas en mm"
d = Doc(os.path.join(AQUI, f"corte_laser_{N}_lamparas.pdf"), f"Corte láser · {N} lámparas roseta", foot)
y = d.header("CORTE LÁSER · METAL CORTES", f"LÁMINA DE ACERO {n0(T)} MM",
             f"Piezas planas para {N} lámparas roseta. Medidas en mm. Los archivos DXF van a escala 1:1, "
             f"con las medidas exactas de la pieza (sin compensar el corte).")
y = d.tiles(y - 6 * mm, [(n0(N), "aros", f"Ø{n0(2 * R_EXT)} × Ø{n0(2 * R_INT)}", True), (n0(N), "discos", f"Ø{n0(disco['diametro'])} con perforación", True),
                         (f"{n0(T)} mm", "espesor", "acero al carbono HR / A36", False), ("1:1", "DXF", "uno por pieza", False)])
y -= 10 * mm
d.text(M, y, "PIEZAS", "semi", 13, INK)
y = d.table(M, y - 3 * mm, ["PIEZA", ("CANT.", "right"), "MEDIDAS", "ARCHIVO DXF"], [
    ["Aro de abajo", (n0(N), "right"), f"Ø ext {n0(2 * R_EXT)} · Ø int {n0(2 * R_INT)} · ancho {n0(R_EXT - R_INT)}", "aro_laser.dxf"],
    ["Disco del centro", (n0(N), "right"), f"Ø {n0(disco['diametro'])} · perforación central Ø{n1(HOLE)}", "disco_laser.dxf"],
], [34 * mm, 16 * mm, 74 * mm, W - 2 * M - 124 * mm])
y -= 4 * mm
y = d.wrap(M, y, f"Opcional: las versiones \"con marcas\" (aro_laser_con_marcas.dxf y disco_laser_con_marcas.dxf) traen muescas de "
           f"{n1(NOTCH_W)} × {n1(NOTCH_D)} mm en el borde que marcan dónde va cada varilla. Ayudan mucho al soldar.", W - 2 * M, "body", 9.2, MUTED)

y -= 8 * mm
d.text(M, y, "LÁMINA", "semi", 13, INK)
n12, n15 = aros_por_lamina(*SHEETS[0]), aros_por_lamina(*SHEETS[1])
y = d.table(M, y - 3 * mm, ["LÁMINA", ("AROS POR LÁMINA", "right"), (f"LÁMINAS PARA {N}", "right"), "DISCOS"], [
    [f"{n0(SHEETS[0][0])} × {n0(SHEETS[0][1])} mm", (str(n12), "right"), (str(math.ceil(N / n12)), "right"), "los 9 caben dentro de un aro"],
    [f"{n0(SHEETS[1][0])} × {n0(SHEETS[1][1])} mm", (str(n15), "right"), (str(math.ceil(N / n15)), "right"), "los 9 caben dentro de un aro"],
], [40 * mm, 36 * mm, 36 * mm, W - 2 * M - 112 * mm])
y -= 6 * mm
y = d.notes(y, "PARA METAL CORTES", [
    f"Cantidad: {N} aros y {N} discos. Acero al carbono laminado en caliente (HR, A36 o similar) de {n0(T)} mm.",
    "Los DXF están en milímetros, escala 1:1. Las cotas son de la pieza terminada; tolerancia normal del láser (±0,3 mm).",
    f"Los {N} discos caben dentro del hueco de un aro, así que no necesitan lámina aparte (ver lamina_1220x2440_acomodo_sugerido.dxf).",
    "Entregar sin escoria ni rebaba, y planos (los aros no deben quedar alabeados).",
])
y -= 6 * mm
d.notes(y, "OJO CON EL MATERIAL DE LOS AROS", [
    f"Cada aro pesa {n1(kg_aro)} kg, pero el centro que sobra es un disco de Ø{n0(2 * R_INT)} de unos {n0(math.pi * R_INT ** 2 * T * RHO)} kg. "
    f"Pregunta si cobran la lámina completa o solo lo usado.",
    f"La alternativa es rolar los aros en pletina de {n0(R_EXT - R_INT)} × {n0(T)} (5 barras de 6 m para {N} aros, unos 23 kg). "
    f"Pide cotización de las dos opciones y escoge.",
])
d.next_page()

# página 2: dibujos
y = d.header("CORTE LÁSER · DIBUJOS", "LAS DOS PIEZAS")
ring_drawing(d, W / 2, Hp - M - 82 * mm, 52 * mm)
d.text(M, Hp - M - 26 * mm, f"AROS · HACER {N}", "semi", 13, INK)
y = Hp - M - 148 * mm
d.text(M, y, f"DISCOS · HACER {N}", "semi", 13, INK)
disc_drawing(d, M + 40 * mm, y - 38 * mm, 26 * mm)
d.wrap(M + 84 * mm, y - 12 * mm, f"Las muescas blancas son las marcas opcionales. En el aro, las de adentro marcan los {PET} puntos donde se "
       f"juntan dos curvas formando una V (cada {n1(PASO)}°, empezando en 0°) y las de afuera los {PET} meridianos (corridos {n1(MER_OFF)}°). "
       f"En el disco marcan las {PET} posiciones donde llegan las varillas, alineadas con los meridianos del aro.",
       W - 2 * M - 84 * mm, "body", 9.2, INK)
d.wrap(M + 84 * mm, y - 56 * mm, f"Peso por pieza: aro {n1(kg_aro)} kg, disco {n1(kg_disco)} kg. Para {N} lámparas: {n1(N * (kg_aro + kg_disco))} kg de piezas terminadas.",
       W - 2 * M - 84 * mm, "body", 9.2, MUTED)
d.save()
laser_pdf = d.path

# =====================================================================
# 2 · CURVAS EN VARILLA
# =====================================================================
foot = f"Lámpara roseta · curvas en varilla Ø{n0(ROD)} · {N} lámparas · aro Ø{n0(D)} al eje · medidas en mm"
d = Doc(os.path.join(AQUI, f"curvas_{N}_lamparas.pdf"), f"Curvas en varilla · {N} lámparas roseta", foot)
y = d.header("CURVAS EN VARILLA · LÁMPARA ROSETA", f"{N} LÁMPARAS · Ø{n0(D / 10)} CM",
             f"Las dos piezas dobladas de la estructura, en varilla lisa de Ø{n0(ROD)} mm (sirve también la de 1/4\"). "
             f"Todas son arcos planos de radio fijo. El aro y el disco van aparte, en corte láser.", W - 2 * M - 60 * mm)
img = os.path.join(AQUI, "render_desde_abajo.png")
if os.path.exists(img):
    d.c.drawImage(img, W - M - 54 * mm, Hp - M - 40 * mm, 54 * mm, 40 * mm, preserveAspectRatio=True, anchor="c")
y = d.tiles(Hp - M - 52 * mm, [(n0(q_cur), "curvas", "las diagonales", True), (n0(q_mer), "meridianos", "soporte de las tiras LED", True),
                               (n0(b_cur + b_mer), "barras", f"varilla Ø{n0(ROD)} de 6 m", False), (f"{n1((q_cur * cu['largo_desarrollado_eje'] + q_mer * me['largo_desarrollado_eje']) / 1000)} m", "de varilla", "sin contar sobrantes", False)])
y -= 10 * mm
d.text(M, y, "PIEZAS", "semi", 13, INK)
y = d.table(M, y - 3 * mm, ["PIEZA", ("POR LÁMPARA", "right"), (f"PARA {N}", "right"), "MEDIDAS (AL EJE DE LA VARILLA)"], [
    ["Curva (diagonal)", (str(dat["n_curvas"]), "right"), (n0(q_cur), "right"),
     f"R {n1(cu['radio_doblez_eje'])} · {n1(cu['angulo_arco_deg'])}° · largo {n1(cu['largo_desarrollado_eje'])} · cuerda {n1(cu['cuerda'])}"],
    ["Meridiano (LED)", (str(PET), "right"), (n0(q_mer), "right"),
     f"R {n1(me['radio_doblez_eje'])} · {n1(me['angulo_arco_deg'])}° · largo {n1(me['largo_desarrollado_eje'])} · cuerda {n1(me['cuerda'])}"],
], [34 * mm, 24 * mm, 20 * mm, W - 2 * M - 78 * mm])
y -= 8 * mm
d.text(M, y, "LISTA DE COMPRA Y CORTE", "semi", 13, INK)
y = d.table(M, y - 3 * mm, ["PARA", ("BARRAS DE 6 m", "right"), ("TRAMO", "right"), ("POR BARRA", "right"), ("REPUESTO", "right"), ("SOBRA POR BARRA", "right")], [
    ["Curvas", (str(b_cur), "right"), (n0(c_cur), "right"), (str(pb_cur), "right"), (f"+{b_cur * pb_cur - q_cur}", "right"), (n0(BARRA - pb_cur * (c_cur + KERF)), "right")],
    ["Meridianos", (str(b_mer), "right"), (n0(c_mer), "right"), (str(pb_mer), "right"), (f"+{b_mer * pb_mer - q_mer}", "right"), (n0(BARRA - pb_mer * (c_mer + KERF)), "right")],
], [34 * mm, 28 * mm, 22 * mm, 24 * mm, 24 * mm, W - 2 * M - 132 * mm])
y -= 3 * mm
d.text(M, y, f"Total: {b_cur + b_mer} barras de varilla lisa Ø{n0(ROD)} mm de 6 m ({n1((b_cur + b_mer) * 6 * kg_m_rod)} kg).", "bold", 9.5, INK)
# plan de corte
y -= 9 * mm
for label, L, k, col in [(f"Curvas: {pb_cur} tramos de {n0(c_cur)}", c_cur, pb_cur, BRASS), (f"Meridianos: {pb_mer} tramos de {n0(c_mer)}", c_mer, pb_mer, ROD_C)]:
    d.text(M, y, label, "bold", 9, INK)
    sob = BARRA - k * (L + KERF)
    d.text(W - M, y, f"sobran {n0(sob)} mm", "body", 8.5, MUTED, "right")
    sc = (W - 2 * M) / BARRA
    for j in range(k):
        d.c.setFillColor(col)
        d.c.rect(M + j * (L + KERF) * sc, y - 6 * mm, L * sc - 1.4, 3.2 * mm, stroke=0, fill=1)
    d.c.setFillColor(LINE)
    d.c.rect(M + k * (L + KERF) * sc, y - 6 * mm, sob * sc, 3.2 * mm, stroke=0, fill=1)
    y -= 13 * mm
y -= 2 * mm
d.notes(y, "PARA TENER EN CUENTA", [
    f"Las {n0(q_cur)} curvas son la misma pieza; en cada lámpara la mitad ({PET}) se monta volteada. Los {n0(q_mer)} meridianos también son todos iguales.",
    f"Se corta con sobrante y se recorta después de doblar, sobre la plantilla. Si cortas las curvas a {n0(c_cur - 5)} mm salen "
    f"{por_barra(c_cur - 5)} por barra ({barras(q_cur, por_barra(c_cur - 5))} barras), pero queda menos para recortar.",
    f"Horma para doblar a mano: radio {n0(horma(cu['radio_doblez_eje']))} para las curvas y {n0(horma(me['radio_doblez_eje']))} para los meridianos "
    f"(más cerrada que la pieza porque el acero se abre al soltarlo; ajústala con 2 piezas de prueba).",
    "Cada pieza tiene que quedar plana (apoyada en la mesa no cojea) y coincidir con la plantilla 1:1 de las últimas hojas.",
])
d.next_page()

# página 2: dibujos y tablas de trazado
y = d.header("CURVAS EN VARILLA · DIBUJOS", "LAS DOS PIEZAS")
box_w = W - 2 * M
d.text(M, Hp - M - 26 * mm, f"CURVA · DIAGONAL · HACER {n0(q_cur)}", "semi", 13, INK)
arc_drawing(d, M, Hp - M - 128 * mm, box_w * 0.6, 98 * mm, cu["radio_doblez_eje"], cu["angulo_arco_deg"], show_center=True)
d.text(M, Hp - M - 140 * mm, f"MERIDIANO · LED · HACER {n0(q_mer)}", "semi", 13, INK)
arc_drawing(d, M, Hp - M - 196 * mm, box_w * 0.6, 54 * mm, me["radio_doblez_eje"], me["angulo_arco_deg"], show_center=False)


def trazado(R, ang):
    half = math.radians(ang) / 2
    chord, yc = 2 * R * math.sin(half), -R * math.cos(half)
    step = 50 if chord > 260 else 25
    rows, x = [], 0.0
    while x < chord / 2 - 1:
        rows.append((x, math.sqrt(R * R - x * x) + yc))
        x += step
    rows.append((chord / 2, 0.0))
    return rows


tx = M + box_w * 0.64
for (title, R, ang, ytop) in [("Trazado de la curva", cu["radio_doblez_eje"], cu["angulo_arco_deg"], Hp - M - 34 * mm),
                              ("Trazado del meridiano", me["radio_doblez_eje"], me["angulo_arco_deg"], Hp - M - 140 * mm)]:
    d.text(tx, ytop, title.upper(), "monob", 8, BRASS)
    d.wrap(tx, ytop - 5 * mm, "Sobre la cuerda, a cada lado del centro: altura del eje.", box_w * 0.36, "body", 8, MUTED)
    rows = [[(("± " if i else "") + n0(xv), "right"), (n1(yv), "right")] for i, (xv, yv) in enumerate(trazado(R, ang))]
    d.table(tx, ytop - 11 * mm, [("DESDE EL CENTRO", "right"), ("ALTURA", "right")], rows, [box_w * 0.19, box_w * 0.17], size=8.6, row_h=6.2 * mm)
d.text(M, 22 * mm, "Las hojas siguientes son las plantillas a tamaño real: imprímelas al 100 % (sin \"ajustar a la página\") y únelas por las cruces.", "body", 8.6, MUTED)
d.save()
curvas_pdf = d.path

# plantillas 1:1 al final del PDF de curvas (de planos_lampara_roseta.pdf, páginas 5 a 8)
try:
    from pypdf import PdfReader, PdfWriter
    planos = os.path.join(AQUI, "planos_lampara_roseta.pdf")
    if os.path.exists(planos):
        w = PdfWriter()
        for p in PdfReader(curvas_pdf).pages:
            w.add_page(p)
        src = PdfReader(planos)
        for i in range(4, len(src.pages)):
            w.add_page(src.pages[i])
        w.add_metadata({"/Title": f"Curvas en varilla · {N} lámparas roseta"})
        buf = io.BytesIO()
        w.write(buf)
        open(curvas_pdf, "wb").write(buf.getvalue())
except Exception as e:
    print("Aviso: no se agregaron las plantillas 1:1 (", e, ")")

print("PDF láser :", laser_pdf)
print("PDF curvas:", curvas_pdf)
print("DXF       :", ", ".join(dxfs))
print(f"aros {N} · discos {N} · curvas {q_cur} ({b_cur} barras) · meridianos {q_mer} ({b_mer} barras)")
