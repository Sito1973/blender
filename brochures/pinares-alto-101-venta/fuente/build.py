"""Arma index.html a partir de template.html: tipografía, íconos Lucide en línea, QR de WhatsApp y mapa.

Uso: python3 build.py <carpeta-paquetes-npm> <carpeta-segno> [fuente] [salida.html]
     fuente = una de THEMES (por defecto: manrope)
"""
import io, math, re, sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
VENDOR = Path(sys.argv[1])              # carpeta con lucide-static y simple-icons desempacados
sys.path.insert(0, sys.argv[2])         # carpeta donde está instalado segno
import segno

CFG = {
    "PRICE_FULL": "$1.260.000.000",
    "PRICE_SHORT": "$1.260",
    "AVALUO_FECHA": "mayo\u00a02026",   # espacio duro: no partir la fecha
    "PHONE": "310 830 0277",
    "PHONE_DIGITS": "3108300277",
}
WA_TEXT = "Hola, me interesa el apartamento 101 de Pinares Alto que está en venta."
CFG["WA_URL"] = f"https://wa.me/57{CFG['PHONE_DIGITS']}?text={quote(WA_TEXT)}"

# Tipografía de titulares (todas SIL OFL 1.1, de Google Fonts vía Fontsource; archivos en assets/fonts).
# k escala los tamaños para que cada fuente ocupe más o menos lo mismo que Manrope.
THEMES = {
    "manrope":             {"family": "Manrope",             "k": 1.00},
    "plus-jakarta-sans":   {"family": "Plus Jakarta Sans",   "k": 0.98},
    "urbanist":            {"family": "Urbanist",            "k": 1.06},
    "bricolage-grotesque": {"family": "Bricolage Grotesque", "k": 0.98},
}
WEIGHTS = (300, 500, 700, 800)   # pesos que usa template.html con --display
FONT = sys.argv[3] if len(sys.argv) > 3 else "manrope"
OUT = sys.argv[4] if len(sys.argv) > 4 else "index.html"

def font_theme(slug):
    t = THEMES[slug]
    faces = "".join(
        f'@font-face{{font-family:"{t["family"]}";src:url(assets/fonts/{slug}-latin-{w}-normal.woff2) format("woff2");font-weight:{w}}}\n'
        for w in WEIGHTS)
    return faces, f'--display:"{t["family"]}", var(--sans); --k:{t["k"]};'

LUCIDE = VENDOR / "lucide-static-1.67.0/package/icons"
def icon(name):
    svg = (LUCIDE / f"{name}.svg").read_text()
    body = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
    body = re.sub(r"\s+", " ", body).strip()
    return ('<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{body}</svg>')

def whatsapp():
    svg = (VENDOR / "simple-icons-16.36.0/package/icons/whatsapp.svg").read_text()
    d = re.search(r'<path d="([^"]+)"', svg).group(1)
    return f'<svg class="ic" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="{d}"/></svg>'

def qr_svg(data):
    qr = segno.make(data, error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="svg", xmldecl=False, svgns=True, nl=False, omitsize=True, border=0, dark="#15201B")
    return buf.getvalue().decode()

# ---------------------------------------------------------------------------
# Mapa ilustrativo de cercanías (sin escala). Lugares: Google Maps (Places).
# Tiempos a pie: OSRM perfil peatón (routing.openstreetmap.de).
# Tiempos en carro: OSRM sin tráfico x1,3, redondeado hacia arriba a 5 min.
# Posiciones en px de la tarjeta (746 x 236); cada lugar respeta su rumbo real
# desde el apartamento (norte arriba), pero las distancias no están a escala.
# ---------------------------------------------------------------------------
IM_W, IM_H = 746, 236
HOME = (440, 132)                        # apartamento
WALK_ZONE = (128, 78)                    # radios de la elipse "10 min a pie"
CABLE = ((0, 38), (746, 238))            # Megacable: pasa por la estación y al sur del conjunto
CLUSTER = {"pin": (392, 84), "card": (190, 8), "rows": [   # zona comercial de Pinares, a pie
    ("utensils", "Gastronomía Sonoma", 6),
    ("heart-pulse", "Clínica Pinares Médica", 7),
    ("shopping-cart", "Carulla", 10),
]}
POIS = [  # (icono, nombre, modo, minutos, x, y, etiqueta: r=derecha, l=izquierda, lb=izquierda abajo)
    ("cable-car", "Estación Megacable", "pie", 10, 330, 126, "lb"),
    ("shopping-bag", "C.C. Parque Arboleda", "carro", 5, 450, 28, "r"),
    ("landmark", "Centro", "carro", 10, 150, 30, "l"),
    ("plane", "Aeropuerto Matecaña", "carro", 15, 28, 118, "r"),
    ("graduation-cap", "UTP", "carro", 10, 300, 206, "r"),
    ("school", "Colegio Franciscanas", "carro", 10, 420, 220, "r"),
]

def mapa_ilustrado():
    hx, hy = HOME; rx, ry = WALK_ZONE
    (cx0, cy0), (cx1, cy1) = CABLE
    slope = (cy1 - cy0) / (cx1 - cx0)
    ang = math.degrees(math.atan(slope))
    mode_ic = {"pie": icon("footprints"), "carro": icon("car")}
    t = lambda mode, mins: f'<span class="im-t">{mode_ic[mode]}{mins} min</span>'
    px, py = CLUSTER["pin"]; kx, ky = CLUSTER["card"]
    o = [f'''<svg class="layer" viewBox="0 0 {IM_W} {IM_H}" aria-hidden="true">
<defs><radialGradient id="walk"><stop offset="0" stop-color="#B5643C" stop-opacity=".22"/><stop offset="1" stop-color="#B5643C" stop-opacity=".05"/></radialGradient></defs>
<g fill="#D3DDC6"><path d="M500 236C520 192 560 170 612 172C664 174 694 150 746 138L746 236Z"/>
<path d="M150 236C168 198 214 176 262 180C304 184 332 200 350 236Z"/><path d="M0 176C34 168 72 188 92 236L0 236Z"/></g>
<ellipse cx="{hx}" cy="{hy}" rx="{rx}" ry="{ry}" fill="url(#walk)" stroke="#B5643C" stroke-opacity=".5" stroke-width="1.2" stroke-dasharray="3 4"/>
<line x1="{cx0}" y1="{cy0}" x2="{cx1}" y2="{cy1}" stroke="#1C3A2F" stroke-opacity=".5" stroke-width="1.6" stroke-dasharray="6 4"/>
<line x1="{px - 10}" y1="{py - 6}" x2="{kx + 186}" y2="{ky + 52}" stroke="#1C3A2F" stroke-opacity=".35" stroke-width="1"/>
</svg>''']
    # zona caminable, etiquetas del entorno
    o.append(f'<span class="im-zone" style="left:{hx + 22}px;top:{hy + ry - 16}px">{icon("footprints")}10 min a pie</span>')
    mx = 560
    o.append(f'<span class="im-tag" style="left:{mx}px;top:{cy0 + slope * mx - 9}px;transform:translate(-50%,-50%) rotate({ang:.1f}deg)">Megacable</span>')
    o.append(f'<span class="im-tag" style="left:640px;top:190px">{icon("leaf")} Entorno natural</span>')
    # zona comercial (varios lugares a pie)
    o.append(f'<div class="im-pin" style="left:{px}px;top:{py}px">{icon("store")}</div>')
    rows = "".join(f'<div class="row"><span class="ico">{icon(ic)}</span>{name}{t("pie", m)}</div>' for ic, name, m in CLUSTER["rows"])
    o.append(f'<div class="im-card" style="left:{kx}px;top:{ky}px">{rows}</div>')
    # lugares
    for ic, name, mode, mins, x, y, side in POIS:
        o.append(f'<div class="im-pin" style="left:{x}px;top:{y}px">{icon(ic)}</div>')
        if side == "r":
            pos = f"left:{x + 16}px;top:{y}px;transform:translateY(-50%)"
        elif side == "l":
            pos = f"left:{x - 16}px;top:{y}px;transform:translate(-100%,-50%)"
        else:  # lb
            pos = f"left:{x - 12}px;top:{y + 17}px;transform:translate(-100%,-50%)"
        o.append(f'<span class="im-lbl" style="{pos}">{name}{t(mode, mins)}</span>')
    # apartamento
    o.append(f'<div class="im-home" style="left:{hx}px;top:{hy}px">{icon("house")}</div>')
    o.append(f'<span class="im-home-lbl" style="left:{hx + 26}px;top:{hy}px">Pinares Alto 101</span>')
    return "".join(o)

html = (HERE / "template.html").read_text()
faces, font_vars = font_theme(FONT)
html = html.replace("/*{{FONT_FACES}}*/", faces).replace("/*{{FONT_VARS}}*/", font_vars)
for k, v in CFG.items():
    html = html.replace("{{" + k + "}}", v)
html = re.sub(r"\{\{i:([a-z0-9-]+)\}\}", lambda m: icon(m.group(1)), html)
html = html.replace("{{wa}}", whatsapp()).replace("{{qr}}", qr_svg(CFG["WA_URL"]))
html = html.replace("{{mapa_ilustrado}}", mapa_ilustrado())
left = re.findall(r"\{\{[^}]+\}\}", html)
assert not left, left
(HERE / OUT).write_text(html)
print(OUT, f"({THEMES[FONT]['family']})", len(html), "bytes")
