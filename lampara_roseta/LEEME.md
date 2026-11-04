# Lámpara roseta: estructura metálica

Réplica de la estructura de la lámpara de las fotos, para mandarla a fabricar en metal.
Todas las medidas están en **milímetros**.

## La pieza que se repite

Las 48 curvas son **la misma pieza**: un arco plano de radio fijo, hecho en varilla lisa de Ø6 mm.
Las 24 que giran hacia el otro lado son esa misma pieza montada al revés.

| Dato | Valor |
|---|---|
| Radio de doblez (al eje de la varilla) | 286.2 mm |
| Ángulo del arco | 114.1° |
| Largo desarrollado | 569.8 mm |
| Cuerda (de extremo a extremo) | 480.2 mm |
| Flecha (altura del arco) | 130.5 mm |
| Cantidad | 48 |

## Archivos

| Archivo | Qué es |
|---|---|
| `lampara_roseta.blend` | Archivo de Blender 4.5 o posterior. La colección `1_PIEZA_UNICA` tiene la curva suelta con sus medidas y `2_LAMPARA_COMPLETA` tiene la lámpara armada. Las 48 curvas son copias enlazadas de la misma pieza, así que si se edita una cambian todas. |
| `planos_lampara_roseta.pdf` | Planos para el taller: ficha técnica, plano de la pieza, plano de armado y plantillas 1:1 en hojas carta. |
| `plantilla_1a1_plotter.pdf` | Plantillas 1:1 de la curva y del meridiano en una sola hoja, para imprimir en plotter. |
| `curva_unica.dxf` / `meridiano.dxf` | Las piezas en 2D a escala 1:1 (arco exacto), para CAD, corte láser o una plantilla de doblez. |
| `planta_armado.dxf` | Vista en planta 1:1 con la posición de todas las varillas. Sirve para armar la plantilla de montaje. |
| `curva_unica.stl` | La pieza sola en 3D. |
| `lampara_completa.stl` / `.obj` | La lámpara completa en 3D. |
| `render_*.png` | Vistas renderizadas. |
| `generar_lampara.py` | Script de Blender que genera todo. Las medidas se cambian al inicio del script. |
| `generar_planos.py` | Genera los PDF y DXF a partir de lo que produce el script anterior. |
| `corte_laser_9_lamparas_D90.pdf` | Para el taller de corte láser (Metal Cortes): 9 aros y 9 discos en lámina de acero de 5 mm. |
| `corte_laser/*.dxf` | Los DXF 1:1 para el láser: aro y disco, cada uno con y sin muescas de ubicación, más un acomodo sugerido en lámina de 1220 × 2440. |
| `curvas_9_lamparas_D90.pdf` | Las 432 curvas y los 216 meridianos en varilla Ø6: compra de barras, plan de corte, dibujos, tablas de trazado y plantillas 1:1. |
| `d80/` | Todo lo mismo para la lámpara de Ø80 cm (aro de 800 al eje, domo de 220): modelo de Blender, planos, plantillas, DXF y los dos PDF de taller. |
| `pdfs_taller.py` | Genera esos dos PDF y los DXF para cualquier cantidad de lámparas: `python3 pdfs_taller.py 9` (Ø90) o `python3 pdfs_taller.py 9 d80` (Ø80). |

## Cambiar el tamaño

Edite los parámetros al inicio de `generar_lampara.py` (`DIAMETRO_ARO`, `ALTURA_DOMO`, `DIAM_VARILLA`, etc.) y ejecute:

```
blender --factory-startup -b -P generar_lampara.py -- .
python3 generar_planos.py .
```

Para otro tamaño en su propia carpeta (por ejemplo Ø80 cm con domo de 220 mm):

```
blender --factory-startup -b -P generar_lampara.py -- d80 --D 800 --H 220
python3 generar_planos.py d80
python3 pdfs_taller.py 9 d80
```

Las medidas por defecto (aro de Ø900 mm y domo de 250 mm de alto) se calcularon a partir de las fotos. Confirme el tamaño real antes de mandar a fabricar.
