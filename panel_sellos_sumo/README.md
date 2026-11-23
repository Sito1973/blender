# Paneles con los sellos de Sumo en relieve — corte láser

14 sellos, cada uno convertido en un panel de 400 × 400 × 18 mm: la línea del sello
(Ø 350 mm) se corta en una capa y se encola sobre una base cuadrada lisa.

| Capa | Qué es | Medida (mm) | Por panel |
|------|--------|-------------|-----------|
| 1 · Base | Cuadrado liso, con el contorno del sello marcado como guía | 400 × 400 × 9 | 1 |
| 2 · Relieve | La línea del sello | Ø 350 × 9 | 1 juego |

## Los sellos

| N.º | Sello | Piezas | N.º | Sello | Piezas |
|-----|-------|--------|-----|-------|--------|
| 01 | Vetas del salmón | 1 + 1 | 09 | Costillas | 1 + 1 |
| 02 | Espiral que se vuelve ola | 1 | 10 | Vapor sobre el cuenco | 1 + 2 |
| 03 | Pliegues de la gyoza | 1 + 4 | 11 | Espiral y ojo | 1 + 1 |
| 05 | Ojo de pez con grecas | 1 + 5 | 12 | Ola | 1 + 2 |
| 06 | Greca andina y ola | 1 | 13 | Grecas y escamas *(nuevo)* | 1 + 4 |
| 07 | Palillos y arroz | 1 + 15 | 14 | Terrazas y luna *(nuevo)* | 1 + 1 |
| 08 | Rollo de sushi | 1 + 7 | 15 | Tejido andino y olas *(nuevo)* | 1 + 2 |

«1 + n» = la pieza principal (aro con sus líneas) más *n* piezas pequeñas que se pegan aparte.

- **01 a 12** son los de los fuelles de la bolsa de Sumo. El 04 (Rodaja de limón) se retiró.
- **13 a 15** son nuevos, en la línea de «Greca andina y ola» (motivo andino de escalones +
  motivo japonés de curvas). No están en la bolsa.

## Propuestas (carpeta `propuestas/`)

| Archivo | Qué es |
|---------|--------|
| `candidatos_sellos.png` | Los 12 sellos nuevos que se generaron (A a L); E, F y J son los 13, 14 y 15 |
| `candidatos_sellos.json` | Esos 12 en vector, para cambiar uno por otro sin volver a generarlos |
| `distribucion_A.png` | Ubicación en pared: mural en cuadrícula 4 × 3 |
| `distribucion_B.png` | Ubicación en pared: friso de 7 en una fila |

Para cambiar un sello por otro candidato, copiar su `d` de `candidatos_sellos.json` a
`sellos_sumo.json` con el número que se quiera y volver a ejecutar el script.

## Archivos

| Archivo | Para qué sirve |
|---------|----------------|
| `corte/sellos_sumo_todos.dxf` / `.pdf` / `.svg` | **Todo en un solo dibujo**, escala 1:1 en mm: arriba los relieves y abajo las bases, cada pieza rotulada |
| `corte/sello_NN_relieve.dxf` / `.svg` | La línea de un sello, por separado |
| `corte/sello_NN_base.dxf` / `.svg` | Cuadrado de la base + marca guía |
| `planos/plano_sellos.pdf` / `.png` / `.svg` | Todos los sellos, medidas, sección y lista de piezas |
| `panel_sellos_sumo.blend` | Modelo de Blender: curvas editables + vista 3D. Lleva dentro el script y el arte, así que funciona solo |
| `panel_sellos_sumo.py` | Script que genera todo lo anterior |
| `sellos_sumo.json` | Arte de los sellos en vector |
| `renders/` | Vistas previas |

Colores: **rojo = cortar**. **Azul** (solo en los archivos de base) **= marcar suave, sin
cortar**: dibuja sobre la base dónde va cada pieza, para pegarlas en su sitio. **Verde** (solo en
`sellos_sumo_todos`) **= rótulos**, no se cortan.

## Notas

- El arte de los sellos 01–12 sale de los fuelles publicados en `bolsas.cocinandosonrisas.co`
  (`descargas/Sumo_fuelle_cara2.svg` y `Sumo_fuelle_cara4.svg`); 01–06 son los de la cara 2
  y 07–12 los de la cara 4, de arriba abajo.
- Los sellos nuevos tienen la línea algo más gruesa y zonas macizas más grandes que los de
  la bolsa.
- Se descartan 4 motas minúsculas que no se podrían pegar (1 en el sello 03 y 3 en el 08).
  El umbral es `PIEZA_MIN_PCT`, en % del área del sello.
- A este tamaño la línea más fina mide unos 5,5 mm y la mayoría entre 8 y 16 mm.

## Cambiar el diseño

Los parámetros están al principio de `panel_sellos_sumo.py` (medidas en mm): `LADO`,
`DIAMETRO`, espesores, `SELLOS` (cuáles generar), etc.

```
blender --background --python panel_sellos_sumo.py
```

También se puede ejecutar dentro de Blender (pestaña *Scripting* → *Run Script*). Si se
retocan las curvas a mano, poner `MODO = "EXPORTAR"` y ejecutar de nuevo: reescribe los
archivos de corte a partir de las curvas de la escena, en la carpeta del `.blend`.

`plano_sellos.pdf`/`.png` y `sellos_sumo_todos.pdf` son conversiones de los `.svg` que escribe el script.
