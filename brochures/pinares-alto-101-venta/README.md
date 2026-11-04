# Brochure de venta · Pinares Alto, Apartamento 101

**PDF final:** `Brochure_Venta_Pinares_Alto_Apto_101.pdf` (A4, 2 páginas, enlaces activos a WhatsApp y teléfono).

| Página | Contenido |
| --- | --- |
| 1 · Emoción | Portada con precio, cifras clave, "El apartamento" y galería con lo principal |
| 2 · Razones | Zonas comunes, mapa de ubicación, ficha técnica, respaldo del avalúo y contacto con QR |

Datos tomados del avalúo comercial (mayo 2026) y del brochure de arriendo.

## Cambiar precio, teléfono u otros datos

1. Edita `CFG` en `fuente/build.py` (`PRICE_FULL`, `PRICE_SHORT`, `AVALUO_FECHA`, `PHONE`, `PHONE_DIGITS`) o los textos en `fuente/template.html`.
2. Arma el HTML. Necesita `lucide-static@1.67.0` y `simple-icons@16.36.0` (vía `npm pack`, desempacados en una carpeta) y `segno` (`pip install segno`):
   ```bash
   python3 fuente/build.py <carpeta-con-los-paquetes-npm> <carpeta-donde-esta-segno> [fuente]
   ```
   `fuente` es la letra de los titulares: `manrope` (por defecto), `plus-jakarta-sans`, `urbanist` o `bricolage-grotesque`.
   Para un cambio rápido de texto también sirve editar directamente `fuente/index.html`.
3. Genera el PDF con Playwright (Chromium):
   ```bash
   node fuente/render.js fuente Brochure_Venta_Pinares_Alto_Apto_101.pdf
   ```

El mapa ilustrativo de la página 2 se arma en `fuente/build.py` (`POIS` y `CLUSTER`: lugar, ícono, tiempo y posición). En `fuente/herramientas/` están los lugares encontrados en Google Maps con sus tiempos (`lugares_google_maps.json`), el script que calcula los tiempos (`tiempos.py`) y el que preparó las fotos (`photos.py`).

## Créditos

- Tipografías: Manrope en titulares y Geist en textos; alternativas incluidas: Plus Jakarta Sans, Urbanist y Bricolage Grotesque (todas SIL Open Font License 1.1).
- Íconos: Lucide (ISC). Ícono de WhatsApp: Simple Icons (CC0).
- Mapa ilustrativo: lugares de Google Maps. Tiempos con OSRM sobre datos de © colaboradores de OpenStreetMap: a pie, tal cual; en carro, tiempo sin tráfico ×1,3 redondeado hacia arriba a 5 min.
