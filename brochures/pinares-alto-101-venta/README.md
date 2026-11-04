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
   python3 fuente/build.py <carpeta-con-los-paquetes-npm> <carpeta-donde-esta-segno>
   ```
   Para un cambio rápido de texto también sirve editar directamente `fuente/index.html`.
3. Genera el PDF con Playwright (Chromium):
   ```bash
   node fuente/render.js fuente Brochure_Venta_Pinares_Alto_Apto_101.pdf
   ```

`fuente/herramientas/` guarda los scripts que prepararon las fotos (`photos.py`) y el mapa (`osm_map.py`); ya están generados en `fuente/assets/`.

## Créditos

- Tipografías: Instrument Serif y Geist (SIL Open Font License 1.1).
- Íconos: Lucide (ISC). Ícono de WhatsApp: Simple Icons (CC0).
- Mapa: © colaboradores de OpenStreetMap (ODbL).
