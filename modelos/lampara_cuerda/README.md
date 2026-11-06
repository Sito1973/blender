# Lámpara colgante de cuerda torcida

Modelo procedural para Blender de una lámpara colgante tipo platillo: dos conos
unidos en el centro por un doble aro. Va forrada con cuerda de algodón torcida
de 3 cabos color café/caramelo.

## Medidas

| Medida | Valor |
| --- | --- |
| Ancho (diámetro en el centro) | 80 cm |
| Alto total (de aro a aro) | 50 cm |
| Altura del centro | 25 cm (justo en la mitad: 25 cm arriba y 25 cm abajo) |
| Doble aro en el centro | 2 aros forrados de cuerda, separados 2 cm (a 24 y 26 cm de altura) |
| Bocas superior e inferior | Ø 25 cm, con banda metálica cobre de 1,5 cm |
| Cuerda | 6 mm, torcida de 3 cabos |
| Hebras | 288 por cono (arriba y abajo) |
| Cuerda necesaria (aprox.) | ≈ 235 m, sin contar amarres ni desperdicio |

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
| `ALTURA_ECUADOR_CM` | Dónde queda la parte más ancha (la mitad entre los dos aros del centro). Si es menor que la mitad del alto, el cono de abajo queda más bajito. |
| `SEPARACION_AROS_CENTRO_CM` | Distancia entre los dos aros del centro. Con 2 cm quedan casi pegados; con más se abre una franja entre ellos. |
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
- **Hebras**: las del cono de arriba bajan desde el aro superior hasta el aro
  de arriba del centro. Las del cono de abajo salen del aro de abajo del centro
  y llegan al aro inferior. Cerca de las bocas no caben todas lado a lado, así
  que se acomodan en tres capas. Hacia el centro se asientan en una sola capa y
  dejan pasar luz entre ellas.
- **Doble aro del centro**: son dos aros de alambre, uno encima del otro. Cada
  uno va forrado con cuerda enrollada en espiral, en sentidos opuestos. Así se
  forman los dos cordones horizontales de la parte más ancha, con una línea
  fina entre ellos.
- **Armazón**: cuatro aros de alambre (arriba, los dos del centro y abajo) y 8
  costillas, todos escondidos bajo la cuerda. Lleva además dos bandas de cobre visibles,
  una araña de 3 brazos, el portabombillo, un bombillo G95, el cable y el
  florón del techo.

Con los valores por defecto la escena tiene unos 2,5 millones de vértices de
cuerda. Si el visor de Blender va lento, sube `PASO_MUESTREO_MM` a 3 o baja
`PUNTOS_PERFIL` a 12.
