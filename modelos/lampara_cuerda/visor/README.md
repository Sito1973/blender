# Visor 3D de la lámpara de cuerda

Página web para mostrar la lámpara: se gira, se acerca y se mueve con el mouse
o con los dedos, y se actualiza al cambiar las medidas.

- **Dirección**: https://lampara.cocinandosonrisas.co
- **Dirección de respaldo de Easypanel**: https://cocson-lampara.jjb7jj.easypanel.host

## Qué se puede hacer

- Cambiar las tres medidas principales: **diámetro de arriba**, **diámetro del
  ecuador** (el ancho) y **altura**.
- En *Más ajustes*: diámetro de abajo, altura del ecuador, separación del
  doble aro, grosor de la cuerda, número de hebras y abombado.
- Ver las cotas sobre el modelo, encender la luz de noche, cambiar el color de
  la cuerda y el metal de los aros.
- Vistas rápidas: 3/4, frente, arriba, abajo y un acercamiento al doble aro.
- **Copiar enlace**: la dirección guarda las medidas (por ejemplo
  `?ds=30&de=90&h=45`), así el arquitecto abre exactamente la misma lámpara.
- **Descargar imagen**: un PNG con el modelo, las cotas y una franja con las
  medidas.

El resumen calcula las hebras por cono, la separación entre hebras en el
ecuador, el diámetro de los aros del centro y los metros de cuerda aproximados.

## Archivos

| Archivo | Qué es |
| --- | --- |
| `index.html` | Todo el visor en un solo archivo (Three.js 0.170 desde jsDelivr) |
| `nginx.conf` | Configuración del servidor web |
| `desplegar.py` | Publica o actualiza el visor en Easypanel |

## Publicar cambios

El servicio `lampara` del proyecto `cocson` en Easypanel es un `nginx:1.27-alpine`
con `index.html` y `nginx.conf` montados como archivos. Después de editar el
visor:

```bash
EASYPANEL_TOKEN=<token de Easypanel> python3 desplegar.py
```

El script actualiza los dos archivos, revisa que el dominio exista y vuelve a
desplegar el servicio.

## Dominio

El subdominio necesita un registro DNS en Cloudflare, igual que `roseta`:

| Tipo | Nombre | Contenido | Proxy |
| --- | --- | --- | --- |
| A | `lampara` | `135.181.136.149` | Solo DNS (nube gris) |

Easypanel saca el certificado HTTPS solo cuando el nombre ya apunta al servidor.
