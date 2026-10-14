# Elenco v2 — prototipo (22-08-2026)

**Integrado al sitio el mismo 22-08-2026** (paso 1 del plan): el bloque de mascotas de `web/loica.js` es este `v2.js`, el CSS de partes y tics está al final de `web/loica.css`, el logo va con `{acc:false}` y el desfile de la portada usa las entradas. Esta carpeta queda como referencia y banco de pruebas.

Los once animales guía de `web/loica.js`, con un accesorio por animal, partes
con clase para animarlas por CSS y una entrada por animal. La propuesta
completa (desfile, carnets, dónde actúan, reglas, plan) está publicada como
artefacto y en `propuesta.html` de esta carpeta.

| Archivo | Qué es |
|---|---|
| `v2.js` | El módulo nuevo. Misma API que `loica.js` (`carita`, `cuerpo`, `mascota`) más `{acc:false}` (sin accesorio: el logo) y `{anima:true}` (tics). Exporta `V2.CSS` con las animaciones. |
| `v1.js` | Copia literal del bloque de mascotas de `loica.js` (líneas 25-397 al 22-08-2026), para comparar. |
| `comparar.html` | Banco de pruebas: cada animal a 22/34/44/96 en v1 y v2, sobre pastel, como pin, en oscuro, y rasterizado a 22 px ×1 y ×2 como lo ve un teléfono. Abrir desde un servidor que sirva la raíz del repo (usa `../../web/loica.css`). |
| `propuesta.src.html` + `construir.py` | La propuesta; `python3 construir.py` inyecta `v1.js` y `v2.js` y deja `propuesta.html` autocontenida. |

## Para llevarlo al sitio (paso 1 del plan)

1. Reemplazar el bloque `/* ---------- MASCOTAS ---------- */` … `function mascota()` de
   `web/loica.js` por el contenido de `v2.js` sin el `const V2 = (() => {` / `return {...}; })()`
   (las funciones se llaman igual).
2. Pegar `V2.CSS` al final de `web/loica.css` (sección nueva "Partes y tics de las mascotas").
3. El logo (`pintarBarra`) llama con `{acc:false}`.
4. Subir `?v=22` a `23` en las nueve páginas y en `exportar_web.py`.

Los accesorios, por si hay que discutirlos uno a uno: Loica cintillo con
micrófono · Cóndor audífonos · Culpeo lentes de sol · Chinchilla boina ·
Chincol lápiz y bolsa de feria · Pudú pañuelo scout y mochila · Degú etiqueta
de precio con un cero · Guarén tarjeta dorada en los dientes · Chungungo
cintillo de toalla y dorsal · Pingüino birrete y libro · Quiltro servilleta.
