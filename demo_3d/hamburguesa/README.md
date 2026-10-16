# Hamburguesa 3D (Blender 5.2)

Hamburguesa armada en 3D a partir de las fotos de producto (carpeta de Google Drive con IMG_0281 a IMG_0345).
Cada ingrediente es un objeto independiente dentro de la colección `Hamburguesa`:

| Objeto | Ingrediente | Cómo se hizo |
|---|---|---|
| `Pan_Abajo` | Pan de abajo tostado | Texturas de IMG_0284 (cara tostada y costado) |
| `Salsa_Cremosa` | Salsa cremosa con pimienta | Forma procedural, color tomado de IMG_0340 |
| `Carne` | Carne de hamburguesa | Texturas de IMG_0340 (costado) e IMG_0291 (costra) |
| `Queso_Parmesano_Crocante` | Queso parmesano crocante | Recortado de IMG_0298, con su borde de encaje |
| `Queso_Crema` | Queso crema | Forma y material procedurales |
| `Tocineta` | Tocineta en trocitos | Forma y material procedurales |
| `Salsa_Frutos_Rojos` | Salsa de frutos rojos | Forma y material procedurales |
| `Lechuga` | Lechuga (8 hojas) | Textura de IMG_0309 (sin brillos), forma procedural |
| `Pan_Arriba` | Pan de arriba con amapola | Corteza de IMG_0340, cara tostada de IMG_0286, semillas en 3D |
| `Palillo` | Palillo de madera | Procedural |

La colección `Escenario` tiene la piedra, la hoja, el fondo, las luces y las cámaras
(`Camara_Armada`, `Camara_Detalle`, `Camara_Despiece`, `Camara_Animacion`).
Animación: del cuadro 1 (despiece) al 72 (armada).

## Regenerar

1. Bajar las fotos a `/home/user/drive_hamburguesa/orig/IMG_XXXX.jpg`.
2. `pip install scipy pillow numpy` y `python3 texturas.py` (crea `tex/`).
3. Bajar el HDRI `brown_photostudio_02` (2k, Poly Haven, CC0) a `hdri/`.
4. `HB_CALIDAD=final HB_VISTAS=armada,detalle,despiece blender -b --python hamburguesa.py`
5. Animación: `blender -b out/hamburguesa.blend --python animacion.py`
