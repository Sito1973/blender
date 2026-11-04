"""Arma index.html a partir de template.html: íconos Lucide en línea, QR de WhatsApp y mapa."""
import io, json, re, sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
VENDOR = Path(sys.argv[1])              # carpeta con lucide-static y simple-icons desempacados
sys.path.insert(0, sys.argv[2])         # carpeta donde está instalado segno
import segno

CFG = {
    "PRICE_FULL": "$1.260.000.000",
    "PRICE_SHORT": "$1.260",
    "AVALUO_FECHA": "mayo 2026",
    "PHONE": "310 830 0277",
    "PHONE_DIGITS": "3108300277",
}
WA_TEXT = "Hola, me interesa el apartamento 101 de Pinares Alto que está en venta."
CFG["WA_URL"] = f"https://wa.me/57{CFG['PHONE_DIGITS']}?text={quote(WA_TEXT)}"

MAP_CARD_PX = 420  # ancho de .mapcard en template.html
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

def map_overlay(meta, W, H):
    pct = lambda x, y: f"left:{x / W * 100:.2f}%;top:{y / H * 100:.2f}%"
    o = []
    def poi(key, text, side="r", dy=0):
        x, y = meta[key] if isinstance(meta[key], list) else meta[key]
        o.append(f'<div class="mk" style="{pct(x, y)}"><div class="d"></div></div>')
        tx = f"calc({x / W * 100:.2f}% + 9px)" if side == "r" else f"calc({x / W * 100:.2f}% - 9px)"
        tr = "translate(0,-50%)" if side == "r" else "translate(-100%,-50%)"
        o.append(f'<span class="lbl" style="left:{tx};top:calc({y / H * 100:.2f}% + {dy}px);transform:{tr}">{text}</span>')
    st = {n: (x, y) for n, x, y in meta["stations"]}
    meta["st_utp"] = list(st["UTP"])
    poi("pinares_medica", "Pinares Médica", "r")
    poi("st_utp", "Estación UTP", "l", -1)
    poi("utp", "Universidad Tecnológica", "r")
    x, y = meta["prop"]
    o.append(f'<div class="mk home" style="{pct(x, y)}"><span class="halo"></span><div class="d"></div></div>')
    o.append(f'<span class="lbl home" style="left:calc({x / W * 100:.2f}% + 16px);top:calc({y / H * 100:.2f}% + 14px)">Pinares Alto · Apto 101</span>')
    # rótulo del Megacable a lo largo de la línea
    import math
    cab = [p for p in meta["cable"] if 0 <= p[0] <= W and 0 <= p[1] <= H]
    (x0, y0), (x1, y1) = cab[0], cab[-1]
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    t = (W * 0.26 - x0) / (x1 - x0)
    lx, ly = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
    o.append(f'<span class="lbl cable" style="left:{lx / W * 100:.2f}%;top:{ly / H * 100:.2f}%;'
             f'transform:translate(-50%,-50%) rotate({ang:.1f}deg) translateY(-8px)">Megacable</span>')
    bar = 0.2 * meta["px_per_km"] / W * MAP_CARD_PX   # 200 m en px de la tarjeta (420 px de ancho)
    o.append(f'<div class="scale"><span>N ↑</span><div><i style="width:{bar:.1f}px"></i></div><span>200 m</span></div>')
    o.append('<span class="osm">© OpenStreetMap</span>')
    return "".join(o)

html = (HERE / "template.html").read_text()
for k, v in CFG.items():
    html = html.replace("{{" + k + "}}", v)
html = re.sub(r"\{\{i:([a-z0-9-]+)\}\}", lambda m: icon(m.group(1)), html)
html = html.replace("{{wa}}", whatsapp()).replace("{{qr}}", qr_svg(CFG["WA_URL"]))
svg = (HERE / "assets/map.svg").read_text()
W, H = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
html = html.replace("{{map}}", svg).replace("{{map_overlay}}", map_overlay(json.loads((HERE / "assets/map.json").read_text()), W, H))
left = re.findall(r"\{\{[^}]+\}\}", html)
assert not left, left
(HERE / "index.html").write_text(html)
print("index.html", len(html), "bytes ·", CFG["WA_URL"])
