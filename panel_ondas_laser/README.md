# Panel de ondas en relieve para corte láser

Panel decorativo de 400 × 400 × 18 mm formado por **2 capas** de MDF/madera encoladas:

| Capa | Qué es | Medida (mm) | Por panel | Para 6 paneles |
|------|--------|-------------|-----------|----------------|
| 1 · Base | Cuadrado liso | 400 × 400 × 9 | 1 | 6 |
| 2 · Relieve | Marco + ondas (5 huecos calados) | 400 × 400 × 9 | 1 | 6 |

Los 6 paneles son iguales; se combinan girándolos 180° y las ondas casan entre sí.

## Archivos

| Archivo | Para qué sirve |
|---------|----------------|
| `corte/capa2_relieve.dxf` / `.svg` | **Lo que corta el láser.** Escala 1:1, en mm |
| `corte/capa1_base.dxf` / `.svg` | Cuadrado de la base (también se puede cortar con sierra) |
| `planos/plano_general.pdf` / `.png` / `.svg` | Plano con medidas, sección y lista de piezas |
| `panel_ondas.blend` | Modelo de Blender: curvas editables + vista 3D |
| `panel_ondas_laser.py` | Script que genera todo lo anterior |
| `renders/` | Vistas previas |

Colores en los archivos de corte: **rojo = cortar**, **azul = grabar línea** (opcional; son
las líneas finas decorativas, se pueden borrar).

## Cambiar el diseño

Los parámetros están al principio de `panel_ondas_laser.py` (medidas en mm): tamaño, marco,
espesores, número de bandas, `SEMILLA` (cambia el dibujo de las ondas), etc.

```
blender --background --python panel_ondas_laser.py
```

También se puede ejecutar dentro de Blender (pestaña *Scripting* → *Run Script*). Si se
retocan las curvas a mano, poner `MODO = "EXPORTAR"` y ejecutar de nuevo: reescribe los
archivos de corte a partir de las curvas de la escena.

`plano_general.pdf` y `.png` son conversiones del `.svg` que escribe el script.
