# Elenco v3 · los retratos

Los doce animales de Loica dibujados de cuerpo entero, en la misma línea que
los compañeros del Libro Digital de Aldeas Infantiles: proporción chibi,
contorno de tinta grueso, ojos grandes con brillo, mejillas, ropa protagonista
y partes que se mueven solas.

Conviven con las caritas de `web/loica.js` (viewBox 24), que siguen siendo las
de los chips, los pines del mapa y todo lo que mide menos de 50 px: a 22 px un
retrato no se lee. Desde 50 px para arriba, `cuerpo()` y `mascota()` dibujan
el retrato.

## Cómo se edita

1. Se dibuja o corrige `svg/<clave>.svg` (solo el contenido interior del `<svg>`).
2. `python3 arte/elenco/construir.py` valida los doce, los comprime y los
   escribe en `web/loica.js` entre los marcadores `RETRATOS:INICIO` y
   `RETRATOS:FIN`. Ese bloque no se edita a mano.
3. Se revisa en `arte/elenco/hoja.html` (abrirla con el servidor del sitio
   corriendo desde `pipeline/`: `python3 -m http.server` y entrar a
   `/arte/elenco/hoja.html`). `--png` en `construir.py` además deja una
   captura en `arte/elenco/hoja.png` con Chrome sin ventana.
4. Si cambió `loica.js`, subir el `?v=` de todas las páginas.

## Reglas de dibujo (las mismas para los doce)

| Regla | Valor |
|---|---|
| Lienzo | `viewBox="0 0 200 240"`. Los pies apoyan en y≈226; nada pasa de y=236 ni sale de x 4–196 (las colas pueden llegar a 196) |
| Proporción | Cabeza ≈ 45 % del alto: centro cerca de (100, 86), unos 106 × 94. Cuerpo de y≈128 a y≈212 |
| Contorno | Lo pone el `<svg>` de afuera: `stroke="#1E2A4A" stroke-width="4.5"`, uniones y puntas redondas, `fill="none"`. Detalles internos a 2,5–3,5. Los rellenos sin borde llevan `stroke="none"` |
| Tinta | `#1E2A4A` (la misma de las caritas). Nunca negro puro |
| Ojos | Elipse de tinta ~rx 9 × ry 11, con un brillo blanco grande (r≈3,6) arriba a un lado y uno chico (r≈1,8) abajo al otro. Separados ~46 px |
| Mejillas | Elipse `#F2778C` a opacidad .55, bajo cada ojo |
| Ropa | La prenda protagonista va en el color de su categoría (columna `color` de `fichas.json`). Un accesorio que diga el oficio sin leer nada |
| Colores | Rellenos planos. Una sombra interna como mucho por pieza (un tono más oscuro, sin borde). Sin degradados, sin filtros, sin opacidades salvo mejillas y reflejos |
| Seguridad | Sin `<style>`, `<script>`, `<image>`, `href`, ni texto (`<text>`). Si hace falta un `id`, empieza con `<clave>-` |

### Partes que se mueven (clases obligatorias)

El CSS (`web/loica.css`, bloque «RETRATOS») anima por clase. Cada pieza gira
desde su base gracias a `transform-box: fill-box`.

| Clase | Qué es | Obligatoria |
|---|---|---|
| `an-cuerpo` | El grupo que envuelve TODO el dibujo (respira) | Sí |
| `an-parpado` | Dos grupos, uno por ojo, con `transform="scale(1 0)"`: una elipse del color de la cara que tapa el ojo + la curva del ojo cerrado. El CSS los cierra al parpadear y al dormir | Sí, dos |
| `an-brazo` | El brazo/ala del lado derecho de la imagen, el que saluda. Pivota en su hombro (arriba a la izquierda de la pieza) | Sí |
| `an-oreja-i` / `an-oreja-d` | Orejas, alas quietas o mechones | Si las tiene |
| `an-cola` | La cola. Pivota en su base (abajo a la izquierda) | Si la tiene |
| `an-extra` | Un accesorio que se mece (borla, pañuelo, etiqueta, pompón) | Opcional, una |
| `an-o-t` `an-o-b` `an-o-l` `an-o-r` `an-o-tl` `an-o-tr` `an-o-bl` `an-o-br` | Cambian el punto de giro de la pieza a arriba, abajo, izquierda… | Opcional |

Orden de capas recomendado (de atrás hacia adelante): cola → patas → cuerpo →
brazo quieto → ropa → brazo que saluda → orejas → cabeza → cara → accesorio de cabeza.

## Los doce

Ver `fichas.json`: clave, especie, categoría, color, vestuario y la frase que
describe el dibujo para lectores de pantalla.
