# Lámpara colgante de cuerda torcida

Modelo procedural para Blender de una lámpara colgante tipo platillo (dos conos
unidos por el ecuador), forrada con cuerda de algodón torcida de 3 cabos color
café/caramelo.

## Medidas

| Medida | Valor |
| --- | --- |
| Ancho (diámetro en el ecuador) | 80 cm |
| Alto total (de aro a aro) | 50 cm |
| Altura del ecuador | 25 cm (justo en la mitad: 25 cm arriba y 25 cm abajo) |
| Bocas superior e inferior | Ø 25 cm, con banda metálica cobre de 1,5 cm |
| Cuerda | 6 mm, torcida de 3 cabos |
| Hebras | 288 por cono (arriba y abajo) |
| Cuerda necesaria (aprox.) | ≈ 225 m, sin contar amarres ni desperdicio |

El script mide la lámpara terminada e imprime las medidas reales en la consola,
junto con los metros de cuerda que usa el modelo.

## Cómo usarlo

**Dentro de Blender (4.2 o superior)**

1. Abre la pestaña **Scripting**.
2. **Open** → `lampara_cuerda.py` → **Run Script** (Alt+P).
3. Se crean dos colecciones:
   - `Lampara_Cuerda`: la lámpara.
   - `Lampara_Escena`: pared, luces y cámaras. Usa `Camara_Lampara` para la vista
     principal y `Camara_Frente` para una vista de frente ortográfica.
4. Renderiza con **F12**. El render usa Cycles.

**Desde la terminal**

```bash
# Guardar el .blend
blender -b -P lampara_cuerda.py -- --guardar lampara_cuerda.blend

# Render de producto (1600 px, 128 muestras)
blender -b -P lampara_cuerda.py -- --render render.png --res 1600 --muestras 128

# Vista de frente con fondo claro
blender -b -P lampara_cuerda.py -- --render frente.png --vista frente
```

## Cambiar la lámpara

Todo se ajusta en la sección `PARÁMETROS` al inicio del script. Ejecutarlo otra
vez borra la lámpara anterior y la vuelve a crear.

| Parámetro | Para qué sirve |
| --- | --- |
| `ANCHO_CM`, `ALTO_CM` | Medidas exteriores |
| `ALTURA_ECUADOR_CM` | Dónde queda la parte más ancha. Si es menor que la mitad del alto, el cono de abajo queda más bajito. |
| `DIAM_BOCA_SUP_CM`, `DIAM_BOCA_INF_CM` | Diámetro de los aros de arriba y abajo |
| `ABOMBADO_CM` | 0 deja los conos rectos; un valor mayor los abomba hacia afuera |
| `DIAM_CUERDA_MM`, `PASO_TORSION_MM` | Grosor de la cuerda y qué tan apretada es su torsión |
| `NUM_HEBRAS` | Densidad del tejido: más hebras tapan más la luz |
| `COLOR_CUERDA` | Color en hexadecimal; el actual se tomó de la foto del rollo |
| `GIRO_HEBRAS_GRADOS` | Un valor mayor que 0 hace que las hebras bajen en espiral |
| `POTENCIA_BOMBILLO_W` | Intensidad de la luz interior |
| `PASO_MUESTREO_MM`, `PUNTOS_PERFIL` | Calidad de la malla (cuanto menor el paso, más fino) |
| `CREAR_ESCENA` | `False` crea solo la lámpara, sin pared, luces ni cámaras |

## Cómo está construido el modelo

- **Cuerda**: cada hebra es una curva. La sección es la unión de tres cabos
  circulares, y esa sección gira a lo largo de la hebra (tilt), así que la
  torsión es geometría real y no una textura.
- **Hebras**: bajan desde el aro superior hasta el ecuador, y otras salen del
  ecuador hasta el aro inferior. Cerca de las bocas no caben todas lado a lado,
  así que se acomodan en tres capas. Hacia el ecuador se asientan en una sola
  capa y dejan pasar luz entre ellas.
- **Ecuador**: un tramo de cuerda enrollado en espiral sobre el aro de alambre
  forma el cordón horizontal de la parte más ancha.
- **Armazón**: tres aros de alambre (arriba, ecuador y abajo) y 8 costillas,
  todos escondidos bajo la cuerda. Lleva además dos bandas de cobre visibles,
  una araña de 3 brazos, el portabombillo, un bombillo G95, el cable y el
  florón del techo.

Con los valores por defecto la escena tiene unos 2,3 millones de vértices de
cuerda. Si el visor de Blender va lento, sube `PASO_MUESTREO_MM` a 3 o baja
`PUNTOS_PERFIL` a 12.
