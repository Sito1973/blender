"""Tiempos y distancias por vía (OSRM: carro en router.project-osrm.org, a pie en routing.openstreetmap.de)."""
import json, math, sys, time, urllib.request
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src)); o = d["origen"]; L = d["lugares"]
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "pinares-brochure/1.0 (one-off)"})
    with urllib.request.urlopen(req, timeout=40) as r: return json.load(r)
coords = ";".join(f"{p['lon']},{p['lat']}" for p in [o] + L)
car = get(f"https://router.project-osrm.org/table/v1/driving/{coords}?sources=0&annotations=duration,distance")
for i, p in enumerate(L, 1):
    p["car_min"] = round(car["durations"][0][i] / 60, 1); p["car_km"] = round(car["distances"][0][i] / 1000, 2)
    dy = (p["lat"] - o["lat"]) * 110.57; dx = (p["lon"] - o["lon"]) * 111.32 * math.cos(math.radians(o["lat"]))
    p["recta_km"] = round(math.hypot(dx, dy), 2); p["rumbo"] = round((math.degrees(math.atan2(dx, dy)) + 360) % 360)
time.sleep(1)
try:
    foot = get(f"https://routing.openstreetmap.de/routed-foot/table/v1/driving/{coords}?sources=0&annotations=duration,distance")
    for i, p in enumerate(L, 1):
        p["pie_min"] = round(foot["durations"][0][i] / 60, 1); p["pie_km"] = round(foot["distances"][0][i] / 1000, 2)
except Exception as e:
    print("a pie: no disponible ->", e)
json.dump(d, open(out, "w"), ensure_ascii=False, indent=1)
print(f"{'lugar':36} {'rumbo':>5} {'recta':>6} {'carro':>12} {'a pie':>12}")
for p in L:
    print(f"{p['name'][:36]:36} {p['rumbo']:>4}° {p['recta_km']:>5}k {p['car_min']:>5}m {p['car_km']:>5}k {p.get('pie_min','-'):>5}m {p.get('pie_km','-'):>5}k")
