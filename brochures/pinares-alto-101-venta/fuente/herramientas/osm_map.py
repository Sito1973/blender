"""Render a minimal, brochure-style SVG map from OpenStreetMap extracts (ODbL, © OpenStreetMap contributors)."""
import sys, glob, math, json
import xml.etree.ElementTree as ET

src, out = sys.argv[1], sys.argv[2]
W, H = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (720, 480)
PROP = (4.799071, -75.683441)          # Calle 3 # 21-11 (coordenadas del avalúo)
C_LAT, C_LON = 4.79900, -75.68585     # view centre
WIDTH_KM = 1.60
K_LON = 111.32 * math.cos(math.radians(C_LAT))
K_LAT = 110.57
d_lon = WIDTH_KM / K_LON
d_lat = (WIDTH_KM * H / W) / K_LAT
LON0, LON1 = C_LON - d_lon / 2, C_LON + d_lon / 2
LAT0, LAT1 = C_LAT - d_lat / 2, C_LAT + d_lat / 2
PX_PER_KM = W / WIDTH_KM

def xy(lat, lon):
    return ((lon - LON0) / (LON1 - LON0) * W, (LAT1 - lat) / (LAT1 - LAT0) * H)

nodes, ways, rels = {}, {}, {}
for f in sorted(glob.glob(src + "/q*.osm")):
    for el in ET.parse(f).getroot():
        tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
        if el.tag == "node":
            nodes[el.get("id")] = (float(el.get("lat")), float(el.get("lon")))
        elif el.tag == "way":
            ways[el.get("id")] = ([n.get("ref") for n in el.findall("nd")], tags)
        elif el.tag == "relation":
            rels[el.get("id")] = ([(m.get("type"), m.get("ref"), m.get("role")) for m in el.findall("member")], tags)

def pts(refs):
    return [xy(*nodes[r]) for r in refs if r in nodes]

def simplify(p, tol=0.9):
    if len(p) < 3: return p
    o = [p[0]]
    for q in p[1:-1]:
        if math.dist(q, o[-1]) >= tol: o.append(q)
    o.append(p[-1]); return o

def d_attr(p, close=False):
    p = simplify(p)
    if len(p) < 2: return ""
    s = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in p)
    return s + ("Z" if close else "")

def rings(member_way_ids):
    """Stitch way segments into closed rings (good enough for small multipolygons)."""
    segs = [list(ways[w][0]) for w in member_way_ids if w in ways]
    out = []
    while segs:
        ring = segs.pop(0)
        changed = True
        while ring[0] != ring[-1] and changed:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == ring[-1]: ring += s[1:]
                elif s[-1] == ring[-1]: ring += s[::-1][1:]
                elif s[-1] == ring[0]: ring = s[:-1] + ring
                elif s[0] == ring[0]: ring = s[::-1][:-1] + ring
                else: continue
                segs.pop(i); changed = True; break
        out.append(ring)
    return out

def in_view(p, pad=60):
    return any(-pad <= x <= W + pad and -pad <= y <= H + pad for x, y in p)

GREEN_KEYS = {("natural", "wood"), ("natural", "scrub"), ("landuse", "forest"), ("landuse", "grass"),
              ("landuse", "greenery"), ("landuse", "meadow"), ("leisure", "park"), ("leisure", "garden"),
              ("leisure", "common")}
def is_green(t): return any((k, t.get(k)) in GREEN_KEYS for k in ("natural", "landuse", "leisure"))

green, campus, bldg, water, pitches = [], [], [], [], []
roads = {k: [] for k in ("minor", "service", "path", "tertiary", "secondary")}
cable, stations = [], []

for wid, (refs, t) in ways.items():
    p = pts(refs)
    if len(p) < 2 or not in_view(p): continue
    closed = refs[0] == refs[-1]
    hw = t.get("highway")
    if hw:
        if hw in ("secondary", "secondary_link", "primary", "trunk"): roads["secondary"].append(d_attr(p))
        elif hw in ("tertiary", "tertiary_link"): roads["tertiary"].append(d_attr(p))
        elif hw in ("residential", "unclassified", "living_street", "pedestrian"): roads["minor"].append(d_attr(p))
        elif hw == "service": roads["service"].append(d_attr(p))
        elif hw in ("footway", "path", "steps", "cycleway", "track"): roads["path"].append(d_attr(p))
    elif t.get("aerialway") == "station":
        cx = sum(x for x, _ in p) / len(p); cy = sum(y for _, y in p) / len(p)
        stations.append((t.get("name"), cx, cy))
        if closed: bldg.append(d_attr(p, True))
    elif t.get("aerialway") == "gondola": cable.append(p)
    elif "building" in t and closed: bldg.append(d_attr(p, True))
    elif t.get("waterway") in ("stream", "river", "canal"): water.append(d_attr(p))
    elif closed and is_green(t): green.append(d_attr(p, True))
    elif closed and t.get("leisure") == "pitch": pitches.append(d_attr(p, True))

for rid, (mem, t) in rels.items():
    if t.get("type") != "multipolygon": continue
    outer = [ref for typ, ref, role in mem if typ == "way" and role in ("outer", "")]
    target = green if is_green(t) else campus if t.get("amenity") in ("university",) else None
    if target is None: continue
    for r in rings(outer):
        p = pts(r)
        if len(p) > 2 and in_view(p): target.append(d_attr(p, True))

# landmarks (centroids from the same OSM data)
def rel_centroid(name):
    for mem, t in rels.values():
        if t.get("name") == name:
            ps = [nodes[n] for typ, ref, role in mem if typ == "way" and ref in ways for n in ways[ref][0] if n in nodes]
            if ps: return (sum(a for a, _ in ps) / len(ps), sum(b for _, b in ps) / len(ps))
def way_centroid(name):
    for refs, t in ways.values():
        if t.get("name") == name:
            ps = [nodes[n] for n in refs if n in nodes]
            return (sum(a for a, _ in ps) / len(ps), sum(b for _, b in ps) / len(ps))

info = {
    "utp": rel_centroid("Universidad Tecnológica de Pereira"),
    "pinares_medica": way_centroid("Pinares Médica"),
    "san_rafael": (4.79869, -75.6894),
    "prop": PROP,
}
def km(a, b):
    return math.hypot((a[0] - b[0]) * K_LAT, (a[1] - b[1]) * K_LON)
for k, v in info.items():
    print(k, v, "->", None if v is None else round(km(PROP, v) * 1000), "m en línea recta", "px", None if v is None else tuple(round(c) for c in xy(*v)))
for n, x, y in stations: print("station", n, round(x), round(y))

def label_anchor(name):
    best = None
    for refs, t in ways.values():
        if t.get("name") != name: continue
        p = pts(refs)
        for a, b in zip(p, p[1:]):
            if not (40 < a[0] < W - 40 and 30 < a[1] < H - 30 and 40 < b[0] < W - 40 and 30 < b[1] < H - 30): continue
            L = math.dist(a, b)
            if best is None or L > best[0]:
                ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
                if ang > 90: ang -= 180
                if ang < -90: ang += 180
                best = (L, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, ang)
    return best
road_labels = {n: label_anchor(n) for n in ("Avenida Juan B. Gutiérrez", "Avenida Circunvalar", "Calle 14", "Carrera 17", "Avenida Belalcázar")}
print("road labels", road_labels)
cable_pts = [(round(x, 1), round(y, 1)) for p in cable for x, y in p]

# --- SVG ---
o = []
o.append(f'<svg class="map" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Mapa de ubicación de Pinares Alto, Pereira">')
o.append('<rect width="100%" height="100%" fill="var(--map-bg)"/>')
o.append('<g fill="var(--map-campus)" stroke="none">' + "".join(f'<path d="{d}"/>' for d in campus if d) + "</g>")
o.append('<g fill="var(--map-green)" stroke="none">' + "".join(f'<path d="{d}"/>' for d in green if d) + "</g>")
o.append('<g fill="var(--map-pitch)" stroke="none">' + "".join(f'<path d="{d}"/>' for d in pitches if d) + "</g>")
o.append('<g fill="none" stroke="var(--map-water)" stroke-width="1.4" stroke-linecap="round">' + "".join(f'<path d="{d}"/>' for d in water if d) + "</g>")
o.append('<g fill="var(--map-bldg)" stroke="none">' + "".join(f'<path d="{d}"/>' for d in bldg if d) + "</g>")
o.append('<g fill="none" stroke="var(--map-path)" stroke-width="0.7" stroke-dasharray="2 2" stroke-linecap="round">' + "".join(f'<path d="{d}"/>' for d in roads["path"] if d) + "</g>")
for cls, wdt in (("service", 1.4), ("minor", 2.6), ("tertiary", 4.2), ("secondary", 5.4)):
    col = "var(--map-road-major)" if cls in ("tertiary", "secondary") else "var(--map-road)"
    o.append(f'<g fill="none" stroke="{col}" stroke-width="{wdt}" stroke-linecap="round" stroke-linejoin="round">' + "".join(f'<path d="{d}"/>' for d in roads[cls] if d) + "</g>")
for p in cable:
    o.append(f'<path d="{d_attr(p)}" fill="none" stroke="var(--map-cable)" stroke-width="1.6" stroke-dasharray="5 3" stroke-linecap="round"/>')
o.append("</svg>")
open(out, "w").write("".join(o))
json.dump({k: (list(xy(*v)) if v else None) for k, v in info.items()} | {"stations": [(n, x, y) for n, x, y in stations], "px_per_km": PX_PER_KM, "road_labels": road_labels, "cable": cable_pts},
          open(out.replace(".svg", ".json"), "w"), indent=1)
print("svg bytes", len(open(out).read()))
