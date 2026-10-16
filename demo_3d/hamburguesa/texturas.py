"""Extrae texturas y colores de las fotos de la hamburguesa."""
import json
import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage as ndi

O = '/home/user/drive_hamburguesa/orig'
T = '/home/user/hb_work/tex'


def load(n):
    im = ImageOps.exif_transpose(Image.open(f'{O}/IMG_{n}.jpg')).convert('RGB')
    return np.asarray(im).astype(np.float32) / 255.0


def crop(a, box):
    H, W = a.shape[:2]
    return a[int(box[1]*H):int(box[3]*H), int(box[0]*W):int(box[2]*W)]


def to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def resize(a, w, h):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255.0


def delight(a, frac=0.25, keep=0.0):
    """Quita el sombreado de baja frecuencia (luz de la foto), conserva color y detalle."""
    lin = to_lin(a)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    sigma = frac * max(a.shape[:2])
    blur = ndi.gaussian_filter(lum, sigma)
    ratio = lum.mean() / np.maximum(blur, 1e-4)
    ratio = ratio ** (1.0 - keep)
    return to_srgb(lin * ratio[..., None])


def save(a, name, q=92):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    if name.endswith('.png'):
        im.save(f'{T}/{name}')
    else:
        im.save(f'{T}/{name}', quality=q)


def mean_srgb(a, box):
    c = crop(a, box).reshape(-1, 3)
    lin = to_lin(c).mean(0)
    return [round(float(v), 4) for v in lin]  # lineal, listo para Blender


colores = {}

# --- 0340: macro frontal de las capas ---
a = load('0340')
save(resize(delight(crop(a, (0.0, 0.0, 1.0, 0.27)), 0.3), 2048, 830), 'pan_arriba_corteza.jpg')
save(resize(delight(crop(a, (0.0, 0.538, 0.72, 0.700)), 0.3), 2048, 690), 'carne_costado.jpg')
colores['salsa_cremosa'] = mean_srgb(a, (0.15, 0.73, 0.55, 0.79))
colores['queso_crema'] = mean_srgb(a, (0.83, 0.36, 0.95, 0.44))
colores['frutos_rojos'] = mean_srgb(a, (0.50, 0.37, 0.55, 0.42))
colores['lechuga'] = mean_srgb(a, (0.02, 0.30, 0.25, 0.35))
colores['pan_arriba'] = mean_srgb(a, (0.1, 0.05, 0.9, 0.25))
colores['carne'] = mean_srgb(a, (0.05, 0.55, 0.65, 0.68))
colores['queso_crocante_lado'] = mean_srgb(a, (0.30, 0.47, 0.45, 0.50))

# --- 0284: pan de abajo, cara tostada y costado ---
a = load('0284')
cara = crop(a, (0.0, 0.235, 1.0, 0.585))
save(resize(delight(cara, 0.35, keep=0.3), 2048, 2048), 'pan_abajo_cara.jpg')
# costado: desdoblar la franja curva (borde inferior de la elipse)
H, W = a.shape[:2]
cx, cy, ea, eb = 0.5 * W, 0.405 * H, 0.52 * W, 0.17 * H
band_h = int(0.115 * H)
cols = np.linspace(0.10 * W, 0.90 * W, 2048)
out = np.zeros((band_h, len(cols), 3), np.float32)
for i, x in enumerate(cols):
    t = (x - cx) / ea
    ytop = cy + eb * np.sqrt(max(0.0, 1 - t * t))
    ys = (ytop + np.arange(band_h)).astype(int).clip(0, H - 1)
    out[:, i] = a[ys, int(x)]
save(resize(delight(out, 0.4, keep=0.2), 2048, 512), 'pan_abajo_costado.jpg')
colores['pan_abajo_costado'] = [round(float(v), 4) for v in to_lin(out.reshape(-1, 3)).mean(0)]

# --- 0286: cara tostada (plancha) del pan de arriba ---
a = load('0286')
save(resize(delight(crop(a, (0.085, 0.255, 0.795, 0.695)), 0.4, keep=0.4), 2048, 2048), 'pan_arriba_cara.jpg')

# --- 0291: costra de la carne (cara de arriba, se estira para corregir la perspectiva) ---
a = load('0291')
save(resize(delight(crop(a, (0.14, 0.415, 0.94, 0.575)), 0.3), 2048, 1400), 'carne_arriba.jpg')

# --- 0298: queso parmesano crocante con transparencia ---
a = load('0298')
c = crop(a, (0.02, 0.33, 0.92, 0.76))
c = resize(c, c.shape[1] // 2, c.shape[0] // 2)
mx, mn = c.max(-1), c.min(-1)
S = (mx - mn) / (mx + 1e-6)
r, g, b = c[..., 0], c[..., 1], c[..., 2]
hue = (np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) + 360) % 360
mask = (S > 0.30) & (mx > 0.38) & (hue > 22) & (hue < 68)
mask = ndi.binary_opening(mask, iterations=1)
core = ndi.binary_opening(mask, iterations=4)
lab, n = ndi.label(core)
sizes = ndi.sum(core, lab, range(1, n + 1))
core = lab == (np.argmax(sizes) + 1)
# conserva el encaje cerca del cuerpo del queso, elimina hilos sueltos lejanos
cyx = np.argwhere(core).astype(np.float64)
mu = cyx.mean(0)
ev, evec = np.linalg.eigh(np.cov((cyx - mu).T))
yy, xx = np.mgrid[0:mask.shape[0], 0:mask.shape[1]]
d = np.stack([yy - mu[0], xx - mu[1]], -1) @ evec
rad = np.sqrt((d[..., 0] / (2 * np.sqrt(ev[0]))) ** 2 + (d[..., 1] / (2 * np.sqrt(ev[1]))) ** 2)
mask = mask & (rad < 1.10)
lab, n = ndi.label(mask)
sizes = ndi.sum(mask, lab, range(1, n + 1))
mask = lab == (np.argmax(sizes) + 1)
# rellenar huequitos de ruido pero dejar los agujeros reales del encaje
hl, hn = ndi.label(~mask)
hs = ndi.sum(~mask, hl, range(1, hn + 1))
for i, s in enumerate(hs):
    if s < 40:
        mask[hl == i + 1] = True
ys, xs = np.nonzero(mask)
y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
c, mask = c[y0:y1 + 1, x0:x1 + 1], mask[y0:y1 + 1, x0:x1 + 1]
# extender el color del queso hacia afuera para que los bordes no se vean oscuros
interior = ndi.binary_erosion(mask, iterations=3)
_, (iy, ix) = ndi.distance_transform_edt(~interior, return_indices=True)
c = c[iy, ix]
c = delight(c, 0.4, keep=0.3)
side = max(c.shape[:2])
c = resize(c, side, side)  # corrige la perspectiva (elipse -> circulo)
m = resize(np.repeat(mask[..., None].astype(np.float32), 3, -1), side, side)[..., 0]
pad = int(side * 0.04)
canvas = np.zeros((side + 2 * pad, side + 2 * pad, 4), np.float32)
_, (iy, ix) = ndi.distance_transform_edt(np.ones((side + 2*pad, side + 2*pad)) - np.pad(np.ones((side, side)), pad), return_indices=True)
cp = np.pad(c, ((pad, pad), (pad, pad), (0, 0)))
canvas[..., :3] = cp[iy, ix]
canvas[pad:pad + side, pad:pad + side, 3] = m
canvas = np.asarray(Image.fromarray((canvas * 255).astype(np.uint8), 'RGBA').resize((2048, 2048), Image.LANCZOS)).astype(np.float32) / 255
save(canvas, 'queso_crocante.png')
small = np.asarray(Image.fromarray((canvas[..., 3] * 255).astype(np.uint8)).resize((800, 800), Image.LANCZOS)) / 255.0
np.save(f'{T}/queso_crocante_mascara.npy', small.astype(np.float32))
colores['queso_crocante'] = [round(float(v), 4) for v in to_lin(c[m > 0.5]).mean(0)]


# --- 0309: lechuga (hoja de la derecha), sin los brillos especulares de la foto ---
a = load('0309')
c = crop(a, (0.56, 0.425, 0.815, 0.515))
mx, mn = c.max(-1), c.min(-1)
S = (mx - mn) / (mx + 1e-6)
brillo = ndi.binary_dilation((mx > 0.62) & (S < 0.58), iterations=6)
w = (~brillo).astype(np.float32)
num = ndi.gaussian_filter(c * w[..., None], sigma=(22, 22, 0))
den = ndi.gaussian_filter(w, sigma=22)[..., None]
relleno = num / np.maximum(den, 1e-4)
suave = ndi.gaussian_filter(brillo.astype(np.float32), 5)[..., None]
c = c * (1 - suave) + relleno * suave
save(resize(delight(c, 0.3, keep=0.25), 2048, 724), 'lechuga.jpg')
colores['lechuga_foto'] = [round(float(v), 4) for v in to_lin(c.reshape(-1, 3)).mean(0)]

json.dump(colores, open(f'{T}/colores.json', 'w'), indent=1)
print(json.dumps(colores, indent=1))
