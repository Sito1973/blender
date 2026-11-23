# Paneles con los sellos de Sumo en relieve — corte láser

Los 12 sellos de los fuelles de la bolsa de Sumo, cada uno convertido en un panel de
600 × 600 × 18 mm: la línea del sello (Ø 520 mm) se corta en una capa y se encola sobre
una base cuadrada lisa.

| Capa | Qué es | Medida (mm) | Por panel |
|------|--------|-------------|-----------|
| 1 · Base | Cuadrado liso, con el contorno del sello marcado como guía | 600 × 600 × 9 | 1 |
| 2 · Relieve | La línea del sello | Ø 520 × 9 | 1 juego |

## Los sellos

| N.º | Sello | Piezas | N.º | Sello | Piezas |
|-----|-------|--------|-----|-------|--------|
| 01 | Vetas del salmón | 1 + 1 | 07 | Palillos y arroz | 1 + 15 |
| 02 | Espiral que se vuelve ola | 1 | 08 | Rollo de sushi | 1 + 7 |
| 03 | Pliegues de la gyoza | 1 + 4 | 09 | Costillas | 1 + 1 |
| 04 | Rodaja de limón | 1 + 7 | 10 | Vapor sobre el cuenco | 1 + 2 |
| 05 | Ojo de pez con grecas | 1 + 5 | 11 | Espiral y ojo | 1 + 1 |
| 06 | Greca andina y ola | 1 | 12 | Ola | 1 + 2 |

«1 + n» = la pieza principal (aro con sus líneas) más *n* piezas pequeñas que se pegan aparte.

## Archivos

| Archivo | Para qué sirve |
|---------|----------------|
| `corte/sello_NN_relieve.dxf` / `.svg` | **Lo que corta el láser.** Escala 1:1, en mm |
| `corte/sello_NN_base.dxf` / `.svg` | Cuadrado de la base + marca guía |
| `planos/plano_sellos.pdf` / `.png` / `.svg` | Los 12 sellos, medidas, sección y lista de piezas |
| `panel_sellos_sumo.blend` | Modelo de Blender: curvas editables + vista 3D |
| `panel_sellos_sumo.py` | Script que genera todo lo anterior |
| `sellos_sumo.json` | Arte de los 12 sellos en vector |
| `renders/` | Vistas previas |

Colores: **rojo = cortar**. **Azul** (solo en los archivos de base) **= marcar suave, sin
cortar**: dibuja sobre la base dónde va cada pieza, para pegarlas en su sitio.

## Notas

- El arte sale de los fuelles publicados en `bolsas.cocinandosonrisas.co`
  (`descargas/Sumo_fuelle_cara2.svg` y `Sumo_fuelle_cara4.svg`); los sellos 01–06 son los
  de la cara 2 y 07–12 los de la cara 4, de arriba abajo.
- Se descartan 4 motas de menos de 120 mm² que no se podrían pegar (1 en el sello 03 y 3
  en el 08). El umbral es `PIEZA_MIN_MM2`.
- A este tamaño la línea mide entre 9 y 24 mm de ancho.

## Cambiar el diseño

Los parámetros están al principio de `panel_sellos_sumo.py` (medidas en mm): `LADO`,
`DIAMETRO`, espesores, `SELLOS` (cuáles generar), etc.

```
blender --background --python panel_sellos_sumo.py
```

Usa funciones de `../panel_ondas_laser/panel_ondas_laser.py`, así que las dos carpetas
deben ir juntas. `plano_sellos.pdf` y `.png` son conversiones del `.svg` que escribe el script.
