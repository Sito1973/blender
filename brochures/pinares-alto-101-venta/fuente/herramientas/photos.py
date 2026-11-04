"""Clean up and export the brochure photos (mild contrast/warmth, gentle sharpening)."""
import sys
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
src, dst = sys.argv[1], sys.argv[2]
# name -> (source file, min width for export)
PHOTOS = {
    "fachada":   ("src_rental/r-000.jpg", 0),
    "sala":      ("src_rental/r-001.jpg", 0),
    "cocina":    ("src_rental/r-002.jpg", 0),
    "alcoba":    ("src_rental/r-003.jpg", 0),
    "terraza":   ("src_rental/r-004.jpg", 0),
    # (la foto "PISCINA" del avalúo no es de Pinares Alto: no se usa)
    "salon":     ("src_rental/r-006.jpg", 0),
    "parque":    ("src_rental/r-007.jpg", 0),
    "comedor":   ("src_avaluo/a-025.jpg", 820),
    "balcon":    ("src_avaluo/a-037.jpg", 820),
    "balcon1":   ("src_avaluo/a-024.jpg", 820),
    "gimnasio":  ("src_avaluo/a-057.jpg", 820),
    "turco":     ("src_avaluo/a-069.jpg", 820),
    "vestier":   ("src_avaluo/a-055.jpg", 560),
    "bano":      ("src_avaluo/a-056.jpg", 560),
    "estar":     ("src_avaluo/a-047.jpg", 820),
    "porteria":  ("src_avaluo/a-013.jpg", 820),
}
for name, (rel, minw) in PHOTOS.items():
    im = Image.open(f"{src}/{rel}").convert("RGB")
    if minw and im.width < minw:
        h = round(im.height * minw / im.width)
        im = im.resize((minw, h), Image.LANCZOS)
    im = ImageOps.autocontrast(im, cutoff=0.4)
    im = ImageEnhance.Contrast(im).enhance(1.04)
    im = ImageEnhance.Color(im).enhance(1.06)
    # touch of warmth: lift red a hair, trim blue a hair
    r, g, b = im.split()
    r = r.point(lambda v: min(255, round(v * 1.015 + 1)))
    b = b.point(lambda v: round(v * 0.985))
    im = Image.merge("RGB", (r, g, b))
    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    im.save(f"{dst}/{name}.jpg", quality=88, optimize=True, progressive=True)
    print(name, im.size)
