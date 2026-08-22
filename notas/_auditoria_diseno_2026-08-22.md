# Auditoría de diseño — Loica web, 22 de agosto de 2026

**Alcance:** las nueve páginas de `web/` más una ficha de `web/e/`, en 390×844 (táctil, dpr 2), 768×1024 y 1440×900, tema claro y oscuro, Chromium y WebKit, contra el contrato de `web/_direccion_visual.md` y las críticas del 9-ago (`notas/_critica_diseno.md`, `notas/_critica_navegacion.md`).
**Método:** Playwright con mediciones por `page.evaluate` (contraste WCAG real, áreas táctiles con `pointer:coarse`, overflow, fuentes < 12 px, animales por tamaño, elementos bajo la barra inferior) y capturas que se miraron una por una. Todas las cifras están medidas. Las capturas, los JSON y los scripts viven en `informes/auditoria-diseno-2026-08-22/` (fuera de git, ~140 MB); las referencias de abajo (`A-*.png`, `B-*.png`, `_s-*.png`) son rutas dentro de esa carpeta.
**Lente:** la skill `frontend-design` (tesis, tipografía con personalidad, estructura que codifica algo verdadero, movimiento con motivo, nada de plantilla) y la lista de verificación de `ui-ux-pro-max` (contraste 4,5:1, 44 px, foco, reduced-motion, sin emoji como ícono, 375/768/1024/1440).
**Veredicto:** el sistema de diseño está bien construido por debajo (tokens, contorno y repisa, oscuro cuidado, foco doble, cero overflow) y las dos páginas con más carácter son Habla y Dónde comer. Lo que falla es lo mismo en todas partes: **la señalética animal no se ve donde se usa** (pines de 15 px, caritas de 11, animales en gris al 50 %), **el texto sobre color se decide página por página** (~40 pares bajo 4,5:1 con tokens que ya existen para evitarlo) y **tres cosas están rotas en celular**.

## Lo que bloquea en celular

1. **Calendario:** a 390×844 y 360×780 la rejilla mide 195 px y seis filas de `minmax(44px)` necesitan 289; los días 24-31 quedan pintados bajo la agenda con `html,body{overflow:hidden}`. La última semana del mes no se puede tocar. (A-calendario §1)
2. **Descuentos:** el botón "Mapa" (x=494) y el contador (x=586) viven en un riel de 713 px que no avisa que se desplaza. El mapa de descuentos no existe para quien no descubre el scroll horizontal. (B-descuentos §1)
3. **Descuentos:** `.ficha` y `.panel-mapa` son absolutos dentro de un `main` cuyo `padding-bottom` no les aplica: "Ver en la página del banco" queda bajo la barra inferior (y=771-820, barra desde 786) y la ficha no scrollea. Arreglo de una línea: `bottom:var(--hueco-nav)`, como ya hace talleres. (B-descuentos §2)

## Lo importante, ordenado por impacto

4. **La señalética no se ve en el mapa.** Pines de 15×19 px con carita de 11 (`icon-size` .4-.55 sobre 34×42); el contrato pide 28. Talleres usa círculos pelados de 12 px sin animal y descuentos 256 discos de 34 px con 175 solapados y teselas claras de noche. Tres lenguajes de pin para un solo sitio. (A-mapa §1, B-talleres §4, B-descuentos §4)
5. **La portada pierde su tesis en celular:** los 11 animales del hero se dibujan en y≈800-839 y la barra inferior arranca en 786; además miden 35 px (mínimo 40 para un cuerpo). Primera pantalla: pájaro, título, botones. (A-index §1-2)
6. **Banda sin teselas de ~60 px sobre el mapa en toda carga móvil** (mapa y talleres; 4 de 5 cargas): el header crece 78→108→150 px después de crear el mapa y el último repintado queda con la cobertura vieja. Parece un segundo header roto. (A-mapa §2, B-talleres §3)
7. **Texto sobre color decidido página por página: ~40 pares bajo 4,5:1.** Badge "HOY" blanco sobre rojo-500 3,96 (2,76 de noche) en cuatro páginas; tarjeta "Talleres" 2,55; pastillas de rol en nosotros hasta 1,65 de noche; chips activos de talleres 2,83-3,49; nombre del banco hasta 2,47; hora del blog 1,97; nav activa 4,31. Los tokens `-solido` y `-tinta` existen y no se usan ahí. (A §5, B §5)
8. **Vacíos sin salida y con el animal enfermo:** mapa, talleres, descuentos y calendario pintan al animal dormido en gris con `opacity:.5` y sin botón; "✕ Limpiar" queda al final de un riel de 1.100 px. En el mapa a 390 el vacío se recorta: se ve la cabeza de la Loica y ningún texto. (A-mapa §5, B §6)
9. **Habla en celular arranca con el hero fuera de pantalla** (`bajar()` salta 359 px al cargar: la Loica llega volando donde nadie la ve) y, conversando, el cambiador de guía son nueve animales de 27×30 px. (A-habla §1-2)
10. **Los animales guía no tienen rol.** El Chungungo se repite idéntico en los seis chips de talleres; el Chincol mide 18 px y queda fuera de pantalla; el Guarén nunca pasa de 44; el Quiltro sale 30 veces por pantalla en comer; el calendario tiene 168 caritas y ninguna con rol; la barra inferior —lo que se ve en todas las páginas— lleva nueve íconos genéricos de línea con etiquetas de 9,5 px. Solo Habla les da voz. **Esto es lo que resuelve la propuesta de elenco v2** (`notas/elenco-v2/`). (A §7 y §10, B §7)
11. **Dos elencos, cuatro chips, cuatro gestos.** El elenco se presenta en index (11 tarjetas + ficha, 3.416 px a 390) y en nosotros (11 tarjetas con otra biografía, sin ficha). Hay cuatro chips distintos (loica.css 42 px, cabeceras 38→36, comer sin repisa, agrega 40 px con animales de 18). La misma `tarjetaEvento` abre ficha en el mapa, pestaña externa en calendario, `e/<id>` en habla y `mapa.html#/e/` en index. (A transversal, B transversal)
12. **Blog frágil:** 4 de 9 y 10 de 10 recomendaciones son cajas "ya no está en la base de datos"; botones de 33 px, "← Volver" de 20 px, leyenda de formatos con contorno y repisa que no se toca. (B-blog)
13. **Agrega sigue siendo un formulario genérico:** cinco obligatorios sin marcar, sin `aria-invalid`/`aria-describedby`, `#precio` sin label, formulario a 817 px de alto en celular, éxito "¡Gracias!" que no sabe si el correo salió; nada de lo pedido el 9-ago para esta página se hizo. (B-agrega)
14. **Lo prometido el 9-ago que sigue igual:** precio "—" (65 de 69 en talleres), "+153" en el calendario móvil, finde sin distinguir, hoy pierde el borde al elegirse, bloque 1-2-3 y grilla en nosotros, gradiente muerto, `lema` sin renderizar, sin esqueleto de carga, calendario sin `.catch`. (A §8, B-talleres §2)
15. **La Loica vuela a donde el pin estaba**, no a donde queda tras el `flyTo` con `offset:[0,-90]`: aterriza a ~130 px del pin, a veces fuera del viewport. (A-mapa §4)
16. **La ficha compartible** (`e/`) manda a `talleres.html#/e/<id>` y talleres no lee el hash; la foto es la única del sitio sin contorno ni repisa; la descripción llega cortada con "…" desde el pipeline. (B-ficha)
17. **`prefers-reduced-motion`** sigue siendo el martillazo global (`*{animation:none!important}`) que el contrato §8.5 pidió reemplazar: mata también el `transition` de alto del panel del mapa. (A/B transversal)

## Los cuatro cambios que más aire dan con menos trabajo

1. **Pines y badge al tamaño del contrato.** Una línea en `icon-size` (≈24-40 px) y diez de CSS para la pastilla "HOY" fuera de la miniatura con `--acento-solido`. La señalética aparece donde está el producto y desaparece el peor contraste del sitio. Con el elenco v2, además, cada pin se reconoce por el accesorio.
2. **Un animal grande por sección, caritas en la barra inferior y la cordillera del color de la página.** Chincol a 96 px junto a "69 talleres", Guarén en la franja de descuentos, el Quiltro ya está; cada destino de la nav tiene animal y color (~25 líneas en `pintarBarra`); `cordillera({tono})` en comer, blog y agrega, y remate en la ficha. Las secciones dejan de ser "la misma lista con otro color".
3. **Un solo chip y una sola regla de texto sobre color.** `.chip` de loica.css en comer y agrega; un token `--tono-tinta` por categoría y por banco (crema sobre oscuro, tinta sobre claro) en chips activos, `.banco-nombre`, `.reco-hora`, pastillas y badge. Cuatro componentes y ~40 contrastes de una sola vez.
4. **Una pantalla de portada y el hueco de la barra respetado.** Hero que termina sobre la barra (los 11 visibles), sin la sección elenco (−3.416 px), tres destinos en vez de siete; en descuentos conteo y "Mapa" en fila propia y `.ficha,.panel-mapa{bottom:var(--hueco-nav)}`; botón en los vacíos. Es más borrar que construir y destraba los tres *bloquea*.

## Lo que está bien y no hay que tocar

El hero de la portada a 1440 (la Loica llega, se posa y saluda sobre la cordillera con los once), la ficha del animal con pastel como segunda tinta, el relevo y el hilo de color de Habla, la tarjeta cuadrada y "El pero." de Dónde comer, el lomo por banco y el 50 % en Baloo de Descuentos, el panel de tres alturas y el CTA visible sin scroll del mapa, teselas CARTO con oscuro, foco doble visible, cero overflow horizontal, reduced-motion que de verdad apaga todo, ningún "Benjamín" ni "bicho" en texto visible.

## El mapa en celular (el reporte que motivó esto)

En el sitio publicado el mapa funciona en celular (Chromium y WebKit emulando iPhone 13, Pixel 5, apaisado, 360 px, dpr 3, oscuro: 9/9 teselas, ~880 pines, pan, pinza, pin→ficha, scroll de lista, tirador, buscador). Lo que se rompía era **probarlo desde el teléfono contra el servidor local por la IP de la red**: `upgrade-insecure-requests` en la CSP (desde el 13-08) subía `loica.js`, `loica.css` y `eventos.json` a un https inexistente y la página quedaba en blanco. Se sacó la directiva de las nueve páginas y de la plantilla de `exportar_web.py` (en Pages no hacía nada; `eventos.json` tiene 0 imágenes `http://`). Evidencia en `informes/mapa-movil-2026-08-22/`. Quedan dos cosas reales para el mapa móvil que sí son de diseño: la banda de teselas (punto 6) y los pines de 15 px (punto 4).

---

# Parte A — portada, mapa, habla, calendario, nosotros (informe completo)

**Fecha:** 22-08-2026 · **Contrato auditado:** `web/_direccion_visual.md` (§0, 1, 4–9) y `web/loica.css` · **Notas previas:** `notas/_critica_diseno.md`, `notas/_critica_navegacion.md` (9-ago).
**Método:** Playwright/Chromium contra `http://localhost:8777`. Viewports 390×844 (`is_mobile`, táctil, dpr 2), 768×1024 y 1440×900, tema claro y oscuro, `networkidle` + 800 ms (2,6 s en habla). Mediciones con `medir.js` (contraste WCAG con luminancia relativa sobre el primer fondo opaco, áreas táctiles con `::before/::after`, overflow, fuentes < 12 px, SVG de animales por tamaño, elementos bajo `.nav-inferior`), `targets_coarse.py` (emulación `pointer:coarse` por CDP) y tres sondas extra (`_sonda_mapa.py`, `_sonda_habla.py`, banda del mapa). Se reutilizaron las 111 capturas `A-*` del intento anterior y se agregaron 9 (`-5s`, `-vacio2`, `-vuelo`, `-tras-resize`, `-resultado2`, `_banda-*`) más 57 rebanadas `_s-*` de las capturas largas para poder leerlas.
**Ojo:** `index.html`, `mapa.html`, `nosotros.html` cambiaron de líneas durante la auditoría (otra sesión editando): los números de línea son de la última lectura y pueden correrse 2–10 líneas; los selectores no cambian.

---

## Los 10 que importan

1. **Calendario bloquea en celular:** a 390×844 y 360×780 la rejilla mide 195 px y necesita 289; los días 24–31 quedan pintados bajo la agenda y `html,body{overflow:hidden}` impide llegar a ellos. La última semana del mes no se puede tocar.
2. **Los pines del mapa miden 15×19 px con carita de 11 px** (`icon-size` .4–.55 sobre 34×42). La dirección pide carita de 28 px; a ese tamaño solo se lee el color y la señalética —la razón del sistema— no existe en la pantalla principal.
3. **La tesis de la portada queda bajo la barra inferior en celular:** los 11 animales del hero se dibujan en y≈800–839 y la `.nav-inferior` arranca en 786. Primera pantalla = pájaro + título + botones, sin elenco.
4. **Banda sin teselas de ~60 px arriba del mapa en toda carga móvil** (390, 360, 768; claro y oscuro; persiste a los 5,5 s y tras `resize()`; desaparece con `panBy([0,1])`). Parece un segundo header roto.
5. **Blanco sobre rojo-500/naranjo en cuatro páginas:** badge "HOY" 3,96:1 (2,76 en oscuro), tarjetas de destino "Talleres" 2,55:1, pastillas de rol en nosotros (Barrio 2,55, Gratis en oscuro 1,65), números 1-2-3 2,55. Los tokens `-solido` y `-tinta` existen y no se usan ahí.
6. **Habla en celular arranca con el hero fuera de pantalla** (`bajar()` salta 359 px al cargar) y, una vez conversando, el cambiador de guía son 9 animales de 27×30 px.
7. **El elenco se presenta dos veces** (index: 11 tarjetas + ficha, 3.416 px de scroll a 390; nosotros: 11 tarjetas con otro texto y sin ficha). Un solo gesto, cuatro destinos: la misma `tarjetaEvento` abre ficha en el mapa, pestaña externa en calendario, `e/<id>.html` en habla y `mapa.html#/e/` en index.
8. **Lo prometido el 9-ago que sigue igual:** precio "—", "+153" en el calendario móvil, fin de semana sin distinguir, `hoy` pierde su borde al estar elegido, bloque 1-2-3 y grilla de 11 tarjetas en nosotros, gradiente de la portada, `lema` sin renderizar, sin esqueleto de carga, calendario sin `.catch`.
9. **La Loica vuela a donde el pin estaba, no a donde queda** después del `flyTo` con `offset:[0,-90]`; en una tarjeta aterrizó 64 px fuera del viewport.
10. **La nav inferior son 9 íconos genéricos de línea con etiquetas de 9,5 px** ("Dctos", "Subir", "Quién") en un sistema cuya identidad son 11 caritas; y el enlace activo de la nav superior pierde el anillo de foco (la repisa pisa el `:focus-visible`).

---

## 1. `index.html` — portada

**Veredicto:** tiene tesis (cordillera, elenco parado encima, la Loica que llega y saluda) y es la página con más carácter; pero en celular la tesis queda debajo de la barra, y después del hero se convierte en tres grillas de tarjetas que repiten la navegación y la página Nosotros.

| # | Sev. | Hallazgo | Evidencia | Qué está mal | Arreglo |
|---|---|---|---|---|---|
| 1 | importante | Los 11 animales del hero quedan bajo la barra inferior en la primera pantalla a 390×844 | `A-index-390-claro-fold.png`, `A-index-390-oscuro-fold.png`: cordillera cortada por la nav, sin animales. Medido: `.paseo` 699–849, `.desfile{bottom:10px}` → animales en y≈800–839; `.nav-inferior` fija desde y=786 (`--alto-nav:58px`) | La primera pantalla pierde lo único que distingue a Loica de una landing cualquiera; solo se ve pájaro, título, dos botones y cuatro cifras | Que el hero termine sobre la barra: `.hero{min-height:calc(100dvh - var(--hueco-nav))}` con `.paseo` anclado abajo y las cifras fuera del hero (debajo del paseo), o `#loica-guia svg` a 96 px y `.cifras` en una fila de 4 en móvil |
| 2 | importante | Los 11 cuerpos del desfile se dibujan a 35 px | `index.html:116` `clamp(33px,9vw,74px)`; medidas `bichoHero svg` 35,1–36,0; `_s-index-390-claro-1.png` | `cuerpo()` está pensado para ≥ 40 px (§6.2); a 35 el Degú, el Pudú y el Quiltro son tres manchas verdes; son botones de 35×49 | En móvil, 5 animales a ≥ 48 px (los que tienen página propia) o dos filas; o `carita()` en discos de 44 como en nosotros |
| 3 | importante | `.destino`: blanco sobre naranjo #F08800 ("Talleres y clases") 2,55:1 en título (27 px/700, mín. 3), bajada (13 px) y flecha; "El mapa" bajada blanca sobre #DE3A1E 4,44:1 | `resumen-texto.txt` 1440-claro; `_s-index-390-claro-2.png`, `_s-index-1440-claro-2.png` | §7.6: los colores claros llevan tinta azul, no crema; `DESTINOS` (`index.html:443`) trae el flag `claro:true` para los siete | Talleres/otros con `color:var(--azul-900)` (`claro:false`); música con fondo `--c-musica-tinta` (#A82B12) o bajada a 15 px/600 sobre `--c-musica-tinta` |
| 4 | importante | "HOY" en la miniatura: blanco sobre `--acento` #E8442E 3,96:1 (2,76 en oscuro), 10 px Manrope, y la franja tapa el mentón de la carita de 44 px | `loica.css:400-405`; `_s-index-390-claro-1.png`, `A-mapa-390-claro.png` (la franja "19 AGO" corta al chinchilla) | §3.4 "nunca blanco sobre rojo-500"; §7.2 pide pastilla contorneada fuera de la esquina; la señalética de 44 px queda en 30 | `.miniatura{overflow:visible}` `.miniatura .dia{inset:auto -4px -4px auto;border-radius:var(--r-pill);border:2px solid var(--contorno);background:var(--tinta);font:800 10px/1 var(--fuente-marca);padding:3px 6px}` `.dia.pronto{background:var(--acento-solido);color:#fff}` (4,81:1; en oscuro `--acento-contraste` da 5,13:1) |
| 5 | importante | El precio sin dato sigue siendo "—" | `loica.js:1542` `${precio \|\| "—"}`; extras `sinDato:["—"]`; visible en `_s-index-1440-claro-2.png` | Pedido en A2 (9-ago); el manifiesto promete "dice el precio real, avisa si un dato no está"; hoy no hay `sinPrecio` en `TEXTOS` | `t("sinPrecio")` = "Precio en la fuente" / "Price at source" / "Preço na fonte", 12 px/600 en `.precio.sin-dato` |
| 6 | importante | "Hoy en Santiago" dice "315 eventos." y muestra 4; el botón "Ver más panoramas →" va a `mapa.html` sin el filtro de hoy | extras `tarjetas:4`, sub "315 eventos."; `index.html:709` `href="mapa.html"` | La cifra promete 315 y el botón entrega 1.825 sin filtro: el lector pierde "hoy" al tocar | `href="mapa.html#hoy"` + leer el hash en `mapa.html` (`cuando="hoy"`); copy "Ver los 315 de hoy →" |
| 7 | importante | El elenco de la portada: 11 tarjetas idénticas en una columna (3.416 px a 390, la sección más larga) que duplican "Los animales guía" de nosotros con textos distintos; la pista "Cómo llegó a esto →" vive en `opacity:0` hasta `:hover` | extras `.elenco` 3002→6418; `_s-index-390-claro-3/4/5.png`; `_s-index-1440-claro-3.png` (4+4+3 con hueco); `index.html:212` `.lupa{opacity:0}` | Con el dedo nada dice que la tarjeta se abre; y dos elencos con dos biografías por animal | Dejar el desfile como único elenco de la portada (ya abre la ficha) + una línea "Once animales te guían → conócelos" hacia nosotros. Si se conserva: `.lupa{opacity:1}` bajo `pointer:coarse`, grilla de 2 columnas (`minmax(150px,1fr)`, cuerpo 72) |
| 8 | importante | Siete "destinos" (1.106 px a 390) repiten la barra de navegación (9 enlaces arriba + 9 abajo); la mascota asoma como marca de agua al 30 % y se lee como fantasma | `_s-index-390-claro-2.png`, `_s-index-1440-claro-2.png` (4+3 con hueco) | Tres navegaciones en una página; la grilla "tarjeta de color + título + bajada + →" es el bloque más de plantilla | Tres destinos como acciones (Mapa, Habla, Agenda) y el resto en la nav; o una fila de pastillas con carita de 22 px |
| 9 | pulido | La mancha `.m3` (turquesa 220 px al 16 %) se lee como una luna pegada a los pies de la Loica a 1440 | `index.html:59`; `_s-index-1440-claro-1.png` | Un disco sin sentido cortando la cordillera | Subirla sobre la línea del cerro y pintarla `--c-otros` (sol), o quitarla (a 390 ya se oculta) |
| 10 | pulido | Cifra "66" en oscuro: `--c-cultura` #1B6FD1 sobre #1E2740 = 2,99:1 (texto grande, mín. 3) | `index.html:687`; resumen 390-oscuro-ficha-animal | Usa el relleno fuerte, no la versión tinta (que ya se invierte en oscuro) | `"var(--c-cultura-tinta)"` |
| 11 | pulido | Botón cerrar de la ficha del animal 38×38; movimiento perpetuo en la primera pantalla (11 animales `pasear` 3,2 s ∞ + Loica `loica-flota` 4,4 s ∞) | `index.html:252`, `108`, `127`; medidas `fichaAnimal.cerrar 38`; reduced-motion lo apaga ✓ (0 animaciones, 0 px cambiados) | §7.5 pide 44; el desfile no necesita marchar siempre | `.fb-cerrar{width:44px;height:44px}`; pasear 6 s y parar, o solo al hover/foco |
| 12 | pulido | Sin estado de carga: la caja "Hoy en Santiago" queda vacía hasta que llega `eventos.json`; el error sí existe (Loica dormida + botón) ✓ | `index.html` `pintarDatos` / `.catch` | B8 pedía esqueleto | Tres `.tarjeta.cargando` con `latir` mientras carga |

**Lo que está bien:** la composición del hero a 1440 (título a la izquierda, la Loica con globo a la derecha, cordillera con los 11 a 74 px) es la imagen del producto; el modo oscuro invierte el contorno a crema y se ve dibujado; la ficha del animal (pose celebrando, pastel como "segunda tinta", foco que vuelve a la tarjeta) es de las mejores piezas del sitio; cero overflow horizontal; nada queda tapado por la barra (body `padding-bottom:58px`).

---

## 2. `mapa.html` — mapa

**Veredicto:** es la pantalla mejor resuelta en estructura (riel de fechas segmentado, CTA visible sin scroll, arrastre real de tres alturas, Loica que vuela, teselas propias para oscuro), pero la señalética —la razón de todo el sistema— no se ve: pines de 15 px y caritas de 11.

| # | Sev. | Hallazgo | Evidencia | Qué está mal | Arreglo |
|---|---|---|---|---|---|
| 1 | importante (raya en bloquea) | Pines de 15,1×18,7 px con carita de 11,2 px en el zoom inicial 12,2; 18,7 px como máximo a zoom 15 | `mapa.html:652` `"icon-size":[...,11,.4,15,.55]` sobre SVG 34×42; extras `pin:{pinW:15.1,carita:11.2}`; `A-mapa-390-claro.png`, `A-mapa-1440-claro.png` (confeti), 901 pines en pantalla | §6.3: carita de 28 px dentro del pin; §1 del contrato abre con "las mascotas son invisibles a los tamaños en que se usan" y sigue siendo cierto aquí. Degú/Pudú/Quiltro son tres gotas verdes | `"icon-size":["interpolate",["linear"],["zoom"],11,.7,14,1,16,1.15]` (≈ 24–40 px); bajo zoom 13 agrupar o bajar `icon-allow-overlap`; `symbol-sort-key` por gratis ya está ✓ |
| 2 | importante | Banda sin teselas de ~60 px arriba del mapa en todas las cargas móviles (390/360 claro y oscuro, 768); persiste a los 5,5 s y tras `mapa.resize()`; desaparece con `panBy([0,1])`; no ocurre a 390 sin emulación móvil ni a 1440 | `A-mapa-390-claro-5s.png`, `A-mapa-390-claro-tras-resize.png`, `_banda-390-dpr2-mobile.png` vs `_banda-390-dpr2-mobile-pan.png`; sonda: header crece 78→108→150 px en 600 ms (barra, riel, chips tras `eventos.json`), canvas y transform terminan en 694 px, teselas en caché `loaded` | El último repintado queda con la cobertura anterior; con el zoom y la atribución encima parece un segundo header roto. Verificar en teléfono real | Reservar el alto de `#filtros` desde el HTML (`min-height:50px`) para que el header no crezca después del mapa; tras `pintarFiltros()` inicial: `requestAnimationFrame(()=>{mapa.resize();mapa.triggerRepaint()})` |
| 3 | importante | En reposo el mapa ocupa 368 de 844 px (44 %): cabecera 150 (barra 58 + riel 46 + chips 46) + panel 268 + nav 58 | extras `header.h 150`, `panel 518–786`; `A-mapa-390-claro.png` | La crítica de navegación pedía devolverle pantalla al mapa; la cabecera pasó de 120 a 150 px | Bajar la fila de chips al panel (C1) o plegarla tras un chip "Tipo ▾"; reposo del panel a `disponible*.34` con contador + afinar; ocultar el zoom de MapLibre en móvil (pellizco) |
| 4 | importante | La Loica vuela a donde el pin estaba: `volarLoica` usa `mapa.project()` antes del `flyTo` con `offset:[0,-90]` | `mapa.html:1106-1109`; sonda: trayectoria termina en (175,387) y el pin queda en (195,257); en otra tarjeta terminó en x=454 > 390 (`medidas-mapa-390-claro-ficha.json`, overflow `#loica-vuelo right:454`) | §6.6: "llega antes que la cámara al pin destino"; hoy llega a 130 px de donde el pin aparece | Destino = `{x:caja.width/2, y:caja.height/2 - 90}` (centro + offset), no la proyección previa |
| 5 | importante | Estado vacío recortado en celular: con "zzqxjw" la lista mide 133 px y el bloque `.vacio` 252: se ve la cabeza de la Loica dormida y ningún texto hasta arrastrar el panel; además va pintada en `var(--tinta-tenue)` con `.vacio svg{opacity:.5}` | `A-mapa-390-claro-vacio2.png`; sonda vacío `{lista.h:133, vacio.h:252}`; `mapa.html:1009`, `loica.css:549` | La pose ya dice "nada" (§6.4); el gris + opacidad la hace parecer enferma (B9 pidió sacar el opacity). El chip "✕ Limpiar filtros" sí aparece ✓ | Al quedar en 0, `fijar(1)` (panel medio) o poner el texto antes del dibujo; `cuerpo("loica","var(--acento)",72,{pose:"durmiendo"})` y `opacity:1` |
| 6 | importante | El enlace activo de la nav superior pierde el anillo de foco: `.nav a[aria-current="page"]` (0,2,1) con `box-shadow:var(--repisa-1)` pisa `:focus-visible` (0,1,0) | `log-mapa.txt` tab 1440: "Mapa" `boxShadow: rgb(30,42,74) 0px 3px 0px` (solo repisa); mismo en calendario | Quien navega con Tab no ve dónde está justo en la página activa | `.nav a[aria-current="page"]:focus-visible{box-shadow:var(--repisa-1),0 0 0 3px var(--foco),0 0 0 6px var(--contorno)}` |
| 7 | importante | Cuatro alturas de chip en la misma pantalla móvil: segmentado 34, chips 38→36, afinar 36; repisas de 2 px contra 3 del sistema; chips de 44 solo por `::before` invisible | `mapa.html:398,400`; targets 390: `#fechas button` 47×34, `.chip` 85×38, `.afinar .chip` 36 | §7.1: chip de 44 con una repisa; tres tamaños se leen como tres componentes | Un chip: `min-height:40px` en móvil + `::before` 44; repisa `--repisa-1` en todos |
| 8 | pulido | Tirador: 386×19,5 px de área con una rayita gris de 44×4,5 | `mapa.html:263-265`; targets-coarse `div#tirador 19.5` | §7.5 pide pastilla de tinta 52×7; 19,5 px es poco para agarrar con el pulgar | `.tirador{padding:12px var(--e-4) 10px}` `.barra-tirador{width:52px;height:7px;background:var(--tinta)}` |
| 9 | pulido | Zoom de MapLibre en blanco sin contorno, también sobre el mapa oscuro; atribución desplegada de 300 px arriba a la derecha | `A-mapa-390-oscuro.png` | Únicos controles fuera del sistema de tinta | `.maplibregl-ctrl-group{background:var(--fondo-elevado);border:2px solid var(--contorno);box-shadow:var(--repisa-1);border-radius:var(--r-md)}` + íconos propios; o quitarlos bajo 880 px |
| 10 | pulido | Caritas bajo el mínimo de 22 px: `.cuenta-rango` a 18, `.mascota-nombre` de la ficha a 20 | `mapa.html:749`, `:1072`; medidas `<22px: 1` (escritorio), `9–10` con ficha | §6.3 | 22 px en ambos |
| 11 | pulido | El `<input>` de búsqueda mide 22 px de alto dentro de una cápsula de 38: tocar el borde de la cápsula no enfoca | targets 1440 `input#buscar 289×22`; calendario 325×22 | Área táctil real de la mitad de la caja | `.campo-buscar input{height:100%}` y `onclick` en la cápsula → `input.focus()` |
| 12 | pulido | Sin estado de carga: "0 eventos" y mapa pelado 1–2 s antes de que llegue el JSON | `mapa.html` arranque | B8 | Contador "…" + tres tarjetas `cargando` |

**Lo que está bien:** CTA "Ver en la fuente original" visible sin scroll a 390 (y=330) y a 1440 (y=457) — B1 resuelto; panel con tres alturas y arrastre de verdad (C2); teselas CARTO claro/oscuro; error con botón "Reintentar"; aviso de mapa lento con la Loica; chips ordenados por volumen con conteos honestos; 0 overflow; foco doble visible en chips y botones.

---

## 3. `habla.html` — el elenco recomienda

**Veredicto:** la página con más personalidad del sitio —el relevo entre animales, el hilo de color, la hoja que cambia de filo, el único lugar donde los animales guía hablan— pero en celular arranca con el hero fuera de pantalla y el cambiador de guía se encoge a 27 px.

| # | Sev. | Hallazgo | Evidencia | Qué está mal | Arreglo |
|---|---|---|---|---|---|
| 1 | importante | Al cargar a 390 la página salta 359 px (`bajar()` → `scrollIntoView` del último turno): título, Loica que llega volando y globo quedan arriba del viewport; la primera opción está en y=803, bajo el pliegue útil (786) | `A-habla-390-claro-fold.png` vs `_s-habla-390-claro-1.png`; sonda `scroll0.scrollY 359`; `habla.html:1007-1009` | La entrada de la anfitriona —la coreografía de la página— ocurre fuera de pantalla; el usuario cae en medio de una conversación | En móvil arrancar con el hero ya compacto (`body.conversando` desde el inicio, ≈124 px) y que el saludo del globo sea la primera burbuja; no llamar `bajar()` en el primer turno |
| 2 | importante | En `body.conversando` los 9 atajos miden 26,6×29,6 px y son el único cambiador de guía; sin área extendida | `habla.html:225` `clamp(26px,5.2vw,40px)`; sonda final `bichos 26.6×29.6`; `A-habla-390-claro-resultado2.png` (arriba) | Bajo 44 y bajo los 40 px mínimos de `cuerpo()`: nueve manchas que además no dicen a dónde llevan (el rótulo es solo `:hover`) | En conversando usar `carita()` en discos de 40 px con `min-height:44px` (como el desfile de nosotros) o riel desplazable con 5 visibles y rótulo de 12 px |
| 3 | importante | "LOICA" se repite en cada burbuja que sigue a una respuesta tuya: `responde()` borra `ultimaVoz` | `habla.html:952-953`; `A-habla-1440-claro-resultado2.png`: LOICA ×5 seguidas sin que nadie más hablara | El nombre se vuelve ruido y el relevo real (la pastilla) pierde fuerza | Resetear `ultimaVoz` solo en `relevo()`; el avatar ya dice quién es |
| 4 | pulido | La hoja `.conversa` con `min-height:calc(100vh - 150px)` deja 300–380 px de papel hundido vacío a 1440/768 con dos burbujas y seis opciones | `habla.html:308-311`; `_s-habla-1440-claro-2.png` | Se lee como página sin terminar | `min-height:auto` + `padding-bottom:var(--e-12)` |
| 5 | pulido | Compactado, a 1440 el título queda a la izquierda y la Loica de 46 px en la esquina derecha (900 px entre ambos) | `_s-habla-1440-claro-turnos-1.png` | Dejan de ser una unidad; en móvil ya va en fila (`habla.html:254-259`) | Mismo `grid-template-columns:auto 1fr;justify-items:start` en escritorio |
| 6 | pulido | Los rótulos del desfile (11 px, solo `:hover/:focus`) no existen con el dedo | `habla.html:152-155`; medidas `rotuloOpacity "0"` ×9 | En celular los nueve atajos no dicen a dónde llevan hasta tocarlos (la pista de texto ayuda, pero es gris de 12 px) | Rótulo visible bajo `pointer:coarse` a 12 px, dos filas si no cabe |
| 7 | pulido | "Ver todo en el mapa" abre `mapa.html` sin lo conversado (hoy/solo/centro/gratis) | `habla.html` `pintarAcciones` `ir.href="mapa.html"` | El usuario pierde lo que acaba de decir | Pasar `cuando`/`soloGratis`/sector por hash y leerlo en el mapa |
| 8 | pulido | Llegar al resultado son 6 respuestas y ~9 s de esperas simuladas (`esperar` 320–900 ms + "escribiendo" 560–900 ms) | sonda: `turnos 16` al final | Con reduced-motion baja a 260 ✓; sin él, el teatro se nota | "Escribiendo" máx. 400 ms; sin pausa entre dos burbujas del mismo animal |
| 9 | pulido | Las tarjetas del resultado llevan a `e/<id>.html`; en mapa/calendario/index el mismo componente hace otra cosa | `habla.html` `pintarLote` | Ver transversal 3 | Unificar destino |

**Lo que está bien:** relevo con pastilla pastel (9–11:1) y cordillera/hoja que cambian de color con el guía; opciones de 60 px con conteo honesto y repisa del color del animal; error con la Loica en la burbuja; foco doble en las opciones; la conversación completa se ve en `A-habla-390-claro-resultado2.png` y funciona.

---

## 4. `calendario.html` — calendario

**Veredicto:** una grilla de Google Calendar con chips de Loica encima: sin un animal con rol, sin fin de semana, bordes de 1,5 px, y en celular la última semana del mes no se puede tocar.

| # | Sev. | Hallazgo | Evidencia | Qué está mal | Arreglo |
|---|---|---|---|---|---|
| 1 | **bloquea** | A 390×844 y 360×780 solo caben 4,4 filas: `.rejilla` mide 195 px (275→470) y seis filas de `minmax(44px,1fr)` + 5 gaps necesitan 289; las filas 5–6 (días 24–31) quedan pintadas bajo `.agenda` (fondo, desde y=482) y `html,body{overflow:hidden}` | `A-calendario-390-claro.png` (fila "24 25 26…" cortada), `A-calendario-360-claro-fold.png` (se corta en la fila del 17), extras `rejilla.h 195`; `calendario.html:31,177,174` | No hay forma de seleccionar del 24 al 31 de agosto en un teléfono | `.calendario{overflow-y:auto}` y `grid-auto-rows:minmax(34px,1fr)`; mejor: en móvil un riel de semana (7 celdas + flechas), que es lo que la crítica pedía (calendario como selector de fecha) |
| 2 | importante | "+N" miente en celular: con `.marca-ev{display:none}` la celda 22 dice "+153" para 156 eventos (resta las 3 marcas ocultas) | `calendario.html:176,470`; extras `masVisibles ["+153","+159",…]`, `marcasVisibles 0`; `A-calendario-390-claro.png` | Señalado el 9-ago (B7/C9) y sigue | Total real en móvil: `<span class="mas">${delDia.length}</span>` cuando las marcas están ocultas |
| 3 | importante | Sin estado de error: `cargarEventos().then(...)` sin `.catch` | `calendario.html:242-248` (index, mapa y habla sí lo tienen) | Si falla el JSON queda "Agosto 2026" con 42 celdas vacías, sin aviso | Copiar el `.catch` del mapa (Loica dormida + "Reintentar") |
| 4 | importante | Fin de semana indistinguible y el "hoy" pierde su borde al estar elegido: `lun…dom` los siete en `--tinta-tenue`; `.dia.elegido` (l.78) pisa el rojo de `.dia.hoy` (l.77) | extras `encabezado` rgb(100,93,81) ×7; `A-calendario-390-claro.png` (22 con borde azul) vs `-dia.png` (22 con borde rojo al elegir otro día) | En una app de panoramas el finde es la única distinción que se busca; al cargar, hoy no se ve como hoy (B6 y mención del 9-ago) | `.encabezado-dias span:nth-child(n+6){color:var(--acento-solido)}`; `.dia:nth-child(7n-1),.dia:nth-child(7n){background:var(--fondo)}`; `.dia.hoy.elegido{border-color:var(--acento)}` |
| 5 | importante | Bordes de 1–1,5 px fuera del contrato: `.dia{border:1.5px solid var(--borde)}` (arena-300, 1,3:1 contra el papel), `.mes-nav button{border:1.5px}`, `.agenda{border-left:1px}`, `.afinar{border-bottom:1px}` | `calendario.html:52,70,90`; `A-calendario-1440-claro.png` | §4.1: "nada de 1px… a partir de 2 se lee como dibujo"; la grilla se ve plana y gris, la única página sin repisa | Celdas con eventos: `border:2px solid var(--contorno-suave)`; vacías: sin caja, solo el número; flechas con contorno 2 px + repisa |
| 6 | importante | Tipografía mínima: `.marca-ev` 10,5 px/600 (71 visibles a 1440), `.mas` 10 px, y en `.dia.fuera` (`opacity:.4`) todo cae a 1,7–2,3:1 (p. ej. "Blood Simple…" 1,88:1; "+3" 1,84:1) | resumen 1440-claro/oscuro; `calendario.html:81,88,76` | Son botones con texto; 18 textos < 12 px en escritorio | 12 px mínimo; `.dia.fuera` atenúa solo el número (`--tinta-tenue`) y oculta las marcas |
| 7 | importante | Cero animales con rol: 12 caritas en chips y 156 en miniaturas, nada más | medidas `mascotas: 156 × .miniatura 44, 12 × .chip 22, 1 × logo`; §6.5 prometía "la mascota dominante del mes a 120 px, atrás al 12 %" | Es la página donde más se nota que el sistema es "chips de colores" | Cabecera del día con la carita dominante a 44 px y "156 eventos · 38 gratis"; mascota del mes como marca de agua (`mascota(...,120)`, `opacity:.12`, `position:absolute`) |
| 8 | pulido | A 390 el header apila barra 58 + chips 56 + mes 40 + búsqueda 50 = 204 px antes de la grilla; el `<input>` mide 22 px dentro de una cápsula de 38 | `calendario.html:140` (`order:3`), targets `input#buscar 325×22` | La búsqueda ya tiene una versión plegada en el mapa | Reusar la lupa plegada del mapa; `input{height:100%}` |
| 9 | pulido | "‹ ›" son glifos a 15 px en botones de 44; "Hoy" es botón sin verbo | `calendario.html:203-205`; extras `mesNav` | Únicos íconos del sitio que no son SVG | Flechas SVG (la `flecha()` de la ficha del mapa); "Ir a hoy" |
| 10 | pulido | La tarjeta del día abre la fuente externa en pestaña nueva, mientras en el mapa abre la ficha | `calendario.html:501` `window.open(e.url…)` | Ver transversal 3 | Abrir `mapa.html#/e/<id>` o `e/<id>.html` |
| 11 | pulido | Agenda del día a 390: visor de 221 px para 156 tarjetas (17.951 px de scroll) | extras `agendaLista {sh:17951, ch:221}` | Con el bloqueo del punto 1, el 46 % de la pantalla ya es de la agenda y sigue siendo poco | Con el riel de semana, la agenda recupera la pantalla |

**Lo que está bien:** el día vacío tiene carácter (Chincol durmiendo a 88 px) y distingue "día sin nada" de "lo vaciaron los filtros"; afinar por subcategoría con conteos que no mienten; flechas ← → del teclado; arranca en hoy; la grilla a 1440 con etiquetas es legible y el oscuro está cuidado.

---

## 5. `nosotros.html` — quién hace esto

**Veredicto:** el texto es lo más humano del sitio y los principios con su animal son la mejor sección; pero la página todavía se arma con dos bloques de plantilla (1-2-3 y una grilla de 11 tarjetas), repite el elenco de la portada y dice "avísame" sin decir cómo.

| # | Sev. | Hallazgo | Evidencia | Qué está mal | Arreglo |
|---|---|---|---|---|---|
| 1 | importante | Contraste en pastillas y números: `.guia .rol` blanco sobre #F08800 "Barrio" 2,55:1, sobre #E8442E "La anfitriona" 3,96, sobre #DE3A1E "Música" 4,44, sobre #0C8B9B "Deporte" 4,05 (12 px/800); en oscuro "Gratis" blanco sobre verde-300 #B4D0C1 = **1,65:1** (`--gratis` se invierte a claro y la pastilla sigue con blanco); `.paso .num` "1" blanco sobre #F08800 2,55 (17 px/800) | `nosotros.html:102-107,176-180`; resumen 1440-claro/oscuro; `_s-nosotros-1440-oscuro-4.png` ("Gratis" ilegible) | §7.6: los colores claros llevan tinta azul; index ya lo resuelve con `--tono-tinta` | Pastillas con `background:var(--suave);color:var(--azul-900)` (9–11:1 en los dos temas, mismo par que `.fb-historia`) o `background:var(--tono-tinta)`; el Degú con `--verde-700` fijo |
| 2 | importante | "avísame" ×3 y "se me pasó" sin ningún canal: no hay correo, formulario ni enlace de contacto en la página | `nosotros.html:274,292` y todo el archivo (sin `mailto:` ni enlace en `.pie`) | La honestidad de "Lo que todavía no funciona" queda sin puerta; además es primera persona singular ("fuera del horario de trabajo") mientras index dice "No cobramos" y la Loica habla en habla: tres voces | Enlace "Avisar un error" en el pie y en "Se cuelan errores" (`agrega.html#error` o `mailto:`); voz declarativa: "Si ves algo malo, se arregla: escribe a …" |
| 3 | importante | "Cómo se llena el mapa" = tres tarjetas con círculo numerado 1-2-3 | `nosotros.html:97-107`; `_s-nosotros-1440-claro-2.png`, `_s-nosotros-390-claro-2.png` | Es el bloque que B12 (9-ago) pidió desarmar y el más "generado" de la página; el número no aporta (son tres momentos del día, no pasos a seguir) | Línea de tiempo con hora en Baloo 2 grande ("06:00", "Después", "Siempre") y el Chincol cantando a las 7; sin caja ni círculo |
| 4 | importante | Elenco duplicado: 11 `.guia` repiten el elenco de index con otro texto y sin la ficha "Cómo llegó a esto"; grilla 3+3+3+2 con hueco a 1440; 3.250 px de columna a 390 | `_s-nosotros-1440-claro-4/5.png`; extras `elenco.h 3250`; §6.5: "Nosotros: las seis a 200 px, en fila, con su nombre y su función" | Dos casas para el mascotario, ninguna a 200 px | Esta es la casa: fila desplazable de 120–200 px con nombre, categoría y la historia al tocar (reusar `abrirBicho` de index); en index solo el desfile |
| 5 | pulido | Gradiente en `.portada` (crema → crema, invisible) | `nosotros.html:36`; §4.5 prohíbe degradados en superficies; señalado el 9-ago | Código muerto con contrato en contra | Quitar |
| 6 | pulido | La Loica de la portada (`.volando`) está posada y solo flota 9 px; a 390 la portada es el título + 10 líneas de 17 px antes de ver a los animales | `nosotros.html:41`; `A-nosotros-360-claro-fold.png`, `_s-nosotros-390-claro-1.png` | Primera pantalla = muro de texto | Pose `volando` de `cuerpo()` o sin animación; bajada de 3 líneas y el resto después del desfile |
| 7 | pulido | El desfile de 11 caritas (30 px en discos de 46, dos filas a 390) no es tocable (`aria-hidden`), mientras en index/habla el mismo desfile abre la ficha/la conversación | `nosotros.html:206` | En la página del elenco son los únicos animales que no se pueden tocar | Enlazar cada disco a su tarjeta (`href="#guia-<clave>"`) |
| 8 | pulido | Cierre "¿Organizas algo?" idéntico al de index (mismo fondo azul-900, mismos dos botones) con el CTA de publicar bajo otro nombre | `_s-nosotros-390-claro-6.png` vs `_s-index-390-claro-6.png` | Ver transversal 2 | Un solo nombre para publicar |
| 9 | pulido | `.falla h3` en Manrope 17/800: la única h3 del sitio fuera de Baloo 2; las tres "fallas" a 390 se ven como cajas grises de texto | `nosotros.html:128`; `_s-nosotros-390-claro-3.png` | La idea (sombra interior = "se hunde") es buena, pero sin tipografía de marca se lee como aviso | h3 en `--fuente-marca` |

**Lo que está bien:** principios alternados con el animal de cada uno en disco y pastel fijo legible en los dos temas; la Loica dormida junto a "Lo que todavía no funciona" (único elemento torcido, −2°, como permite §4.4); la lista honesta de fallas; un copy con autor ("Santiago está lleno de cosas que nadie avisa").

---

## 6. Transversal

### Inconsistencias entre páginas

1. **El elenco vive en dos páginas con dos biografías** (index "Los que te acompañan" + ficha; nosotros "Los animales guía" sin ficha). Elegir casa: nosotros.
2. **Un destino, tres o cuatro nombres:** publicar = "Agrega tu evento" (nav superior, cierre de index) / "Subir" (nav inferior) / "Subir un panorama" (nosotros); nosotros = "Quién hace esto" / "Quién" / "nosotros" (pie de index) / "Quién hace Loica" (`<title>`); calendario = "Calendario" (nav, tarjeta "El calendario") / "Agenda" (nav inferior).
3. **La misma `tarjetaEvento` hace cuatro cosas al tocarla:** mapa → ficha; calendario → fuente externa en pestaña nueva; habla → `e/<id>.html`; index → `mapa.html#/e/<id>`.
4. **Cuatro alturas de chip y dos repisas:** 42 (calendario/`loica.css`), 38→36 (mapa móvil), 36 (afinar), 34 (segmentado); repisa 3 vs 2 px. §7.1 pide 44 y una.
5. **Bordes finos fuera de contrato:** calendario (1–1,5 px en celdas, flechas, agenda), `.tarjeta{border-bottom:1px}`, `.hoy-pie` 1 px; y el "lomo" de color de la tarjeta (§7.2) no existe — solo el inset verde de gratis.
6. **Blanco sobre rojo-500/naranjo se repite** en HOY (4 páginas), `.destino` (index), `.rol`/`.num` (nosotros) y la nav activa a 1440 ("Mapa" crema sobre #DE3A1E 4,31:1; "Quién hace esto" sobre #0E8757 4,41:1; 15 px/700).
7. **Estados vacíos/error con la mascota en gris** (`var(--tinta-tenue)` + `opacity:.5`) en mapa, index y calendario; nosotros la pinta en rojo. §6.4 y B9.
8. **Íconos fuera del sistema:** nav inferior con 9 íconos genéricos de línea, etiquetas de 9,5 px y pastilla solo en el activo; tema con glifos "☾/☀" (U+2600 puede renderizar como emoji en Android; §9.11); calendario con "‹ ›".
9. **Foco:** anillo doble visible en todo ✓ salvo el enlace activo de la nav superior; `.cierre .boton.secundario` de index redefine `box-shadow` (`index.html:308`) con la misma especificidad que `.boton.secundario:focus-visible` y va después: revisar.
10. **`prefers-reduced-motion`:** respetado en las cinco páginas (0 animaciones corriendo, 0 px de diferencia entre dos cuadros), pero con el martillazo global (`loica.css:570-572`) que §8.5 pidió reemplazar: también mata el `transition:height` del panel del mapa.
11. **`lema` "Santiago está pasando"** sigue definido en tres idiomas y sin renderizarse en ninguna página (B10).

### Los 3 cambios que más aire dan con menos trabajo

1. **Pines y badge al tamaño del contrato.** Una línea en `icon-size` (≈ 24–40 px) y diez de CSS para la pastilla "HOY" fuera de la miniatura con `--acento-solido`: la señalética aparece donde está el producto y desaparece el peor contraste del sitio.
2. **Caritas en la nav inferior.** Cada destino ya tiene animal y color (Cóndor/mapa, Loica/habla, Chinchilla/agenda, Chincol/clases, Guarén/dctos, Quiltro/comer, Culpeo/blog, Pudú/quién; "+" para subir); ~25 líneas en `pintarBarra` + `CORTOS`. La barra que se ve en todas las páginas pasa a ser el mejor portador de la marca, y de paso se unifican "Agenda/Calendario" y "Subir/Agrega".
3. **Portada de una pantalla.** Hero que termina sobre la barra (los 11 animales visibles en el primer pantallazo), sin la sección elenco (−3.416 px) y con tres destinos en vez de siete. Es más borrar que construir.

### Lo prometido que no se cumplió (checklist corta)

| Promesa | Fuente | Estado |
|---|---|---|
| Carita de 28 px en el pin | §6.3 / §7.3 | 11 px |
| Lomo de color en la tarjeta | §7.2 | no existe |
| Badge de día como pastilla contorneada | §7.2 | franja roja 10 px |
| Tirador pastilla 52×7 de tinta | §7.5 | rayita gris 44×4,5 |
| `.nav a` 44 px; nav inferior 10,5 px / 24 px | §7.6 | 42 px; 9,5 px / 21 px |
| reduced-motion fino | §8.5 | martillazo |
| Mascota del mes en calendario; seis a 200 px en nosotros | §6.5 | no; 11 a 64 px |
| Nunca blanco sobre rojo-500 | §3.4 | HOY, destino, rol, num |
| Sin emoji/glifos como ícono | §9.11 | ☾/☀, ‹ › |
| Precio "—" → "Precio en la fuente" | A2 | sigue "—" |
| Finde distinto; hoy conserva borde | B6 | no |
| "+N" honesto en móvil | B7/C9 | sigue "+153" |
| Sin 1-2-3 ni grilla de elenco en nosotros | B12 | siguen |
| Gradiente de portada fuera | menciones 9-ago | sigue |
| Esqueleto de carga | B8 | no hay |
| `.catch` en todas las cargas | C10 | falta calendario |
| Lema en pantalla | B10 | código muerto |
| **Cumplido:** tokens y contrastes de `--tinta-tenue`, chips de 44 efectivos, CTA visible sin scroll (B1), nav inferior (B3), arrastre real (C2), teselas CARTO + oscuro (A3), salida del vacío con chip limpiar (B9 parcial), cerrar de ficha 44 (mapa), Baloo 2 en chips y botones (§5.1), poses (§6.4), la Loica que vuela (§6.6) | | |

---

## 7. Animales guía: dónde, tamaño, rol

| Página | Dónde | Tamaño (px) | Rol | Problema |
|---|---|---|---|---|
| todas | `.logo` carita | 30–34 | señalética | — |
| todas | `.nav-inferior` | — | — | 9 íconos genéricos; ningún animal donde más se vería |
| index | `#loica-guia` cuerpo (vuela → posada, globo) | 122 / 224 | actor: saluda una frase fija | bien; el globo es el único diálogo fuera de habla |
| index | `.desfile .bicho-hero` ×11 (botón → ficha) | 35 / 74 | señalética interactiva | bajo la nav a 390 y 35 px (mín. 40 para cuerpo) |
| index | `.cifra` caritas ×4 | 28 / 34 | señalética | "66" en oscuro 2,99:1 |
| index | `.miniatura` caritas ×4 | 44 | señalética | la franja HOY tapa el mentón |
| index | `.destino .asoma` cuerpos ×7 | 118 al 30 % | decoración (marca de agua) | fantasmas; no se distinguen |
| index | `.bicho` cuerpos ×11 + `.fb-cabeza` (celebrando) | 96 / 104–132 | actor: cuenta su historia en ficha | duplica nosotros; sin pista táctil |
| index | error de carga: Loica durmiendo | 88 | actor de estado | gris + opacity .5 |
| mapa | chips caritas ×14 | 22 | señalética | Degú/Pudú se confunden (mismo verde, misma cara; solo cambia el cuerno) |
| mapa | pines ×900 | 15 (carita 11) | señalética | ilegibles: solo color |
| mapa | `.miniatura` ×24 | 44 | señalética | franja de fecha |
| mapa | `.cuenta-rango` / `.mascota-nombre` | 18 / 20 | señalética | bajo 22 |
| mapa | `#loica-vuelo` (volando) | 56 | actor sin diálogo: guía el ojo | aterriza donde el pin estaba |
| mapa | `.aviso` carita | 22 | actor: avisa "el mapa va lento" | bien |
| mapa | vacío: Loica durmiendo | 92 | actor de estado | recortada y en gris |
| habla | `#loica-guia` + globo | 118 / 196 → 42 / 46 | actor: recibe | en móvil pasa fuera de pantalla |
| habla | `.bicho-hero` ×9 | 36 / 74 → 27 / 41 | botones de atajo y cambiador de guía | 27×30 conversando; rótulo solo hover |
| habla | `.avatar` caritas | 32 | **actor con diálogo** (voz propia por animal) | el mejor uso del sitio |
| habla | `.relevo` carita | 22 | señalética del relevo | bien |
| habla | `.opcion` caritas | 30 | señalética de la opción | bien |
| calendario | chips ×12, miniaturas ×156 | 22 / 44 | señalética | ningún animal con rol; sin mascota del mes |
| calendario | vacío: Chincol durmiendo | 88 | actor de estado | bien (en gris) |
| nosotros | `.volando` Loica | 96 | decoración (flota) | pose posada con nombre de vuelo |
| nosotros | `.desfile` caritas ×11 en discos | 30 (disco 46) | señalética | no tocables en la página del elenco |
| nosotros | `.principio-animal` ×3 | 58 / 44 | señalética del principio | bien |
| nosotros | `.dormida` Loica | 60 / 46 | actor de estado ("lo que no funciona") | bien; único torcido |
| nosotros | `.guia-cabeza` ×11 | 64 | presentación | sin ficha; duplica index; pastillas con contraste roto |

**Lectura:** a 74 px los 11 se distinguen (collar del Cóndor, cola del Culpeo, cuerno del Pudú, guata del Quiltro). A 22 px funcionan los de color único (Cóndor, Culpeo, Chinchilla, Chincol, Guarén, Pingüino); Degú/Pudú y Quiltro/Degú se confunden. Bajo 22 (pines, cuenta-rango) no se lee ninguno. Solo la Loica habla fuera de habla.html, y solo con una frase fija.

---

## 8. Métricas

### Áreas táctiles < 44 px a 390 (emulación `pointer:coarse`)

| Página | Interactivos | Caja < 44 | Efectivo < 44 (con `::before/::after`) | Qué queda chico de verdad |
|---|---|---|---|---|
| index | 53 | 26 | 25 | tema 33×26 (39×44 ef.), ES/EN/PT 33×29 (33 de ancho), 11 `.bicho-hero` 35×49, `p.pie a` 58×42; nav ×9 a 43,3 de ancho (al límite) |
| mapa | 62 | 35 | 14 | tema, idiomas, `#tirador` 386×19,5; `input#buscar` 22 de alto (escritorio 289×22) |
| habla | 29 | 23 | 22 | tema, idiomas, 9 `.bicho-hero` 42×49 (27×30 conversando) |
| calendario | 222 | 27 (63 a 360) | 14 | tema, idiomas, `input#buscar` 325×22; a 360 las 42 celdas 43,7×44 |
| nosotros | 16 | 14 | 13 | tema, idiomas; nav ×9 |

**Los 5 peores:** `div#tirador` 386×19,5 (mapa) · `input#buscar` 325×22 / 289×22 (calendario, mapa) · `.bicho-hero` conversando 26,6×29,6 ×9 (habla) · `.idiomas button` 33×29 ×3 en las cinco páginas (44 de alto por `::after`, 33 de ancho) · `button#btn-tema` 33×26 (39×44 ef.). Después: `.bicho-hero` de index 35×49 ×11.

### Contraste bajo el mínimo (4,5:1; 3:1 para ≥ 24 px o ≥ 18,66 px bold)

| Página | Par | Ratio | Dónde |
|---|---|---|---|
| index/mapa/calendario/habla | #FFF sobre #E8442E (oscuro #F47662) | 3,96 / 2,76 | `.miniatura .dia.pronto` "HOY" 10 px |
| index | #FFF sobre #F08800 | 2,55 | `.destino` Talleres: título 27 px, bajada 13 px, flecha |
| index | #FFF sobre #DE3A1E | 4,44 | `.destino` El mapa, bajada 13 px |
| index (oscuro) | #1B6FD1 sobre #1E2740 | 2,99 | `.cifra b` "66" (mín. 3) |
| mapa/calendario (1440) | #FFFBF5 sobre #DE3A1E | 4,31 | `.nav a[aria-current]` "Mapa" 15 px/700 |
| nosotros (1440) | #FFFBF5 sobre #0E8757 | 4,41 | `.nav a[aria-current]` "Quién hace esto" |
| nosotros | #FFF sobre #F08800 | 2,55 | `.paso .num` "1" 17 px; `.guia .rol` "Barrio" 12 px |
| nosotros | #FFF sobre #E8442E / #DE3A1E / #0C8B9B | 3,96 / 4,44 / 4,05 | `.rol` La anfitriona / Música / Deporte |
| nosotros (oscuro) | #FFF sobre #B4D0C1 | 1,65 | `.rol` "Gratis" |
| calendario | #2E7D5B sobre #E5F1EB | 4,31 | `.marca-ev.libre` 10,5 px |
| calendario | #E8442E sobre #EDE7DE | 3,23 | `.dia.hoy.elegido .dia-num` 13 px/700 |
| calendario | `.dia.fuera` (opacity .4): números 2,32, marcas 1,67–1,88, "+3" 1,84 (oscuro 2,0–3,4) | | botones con texto del mes vecino |
| mapa | #B2B4BB sobre crema | 2,01 | `#ev-prev` deshabilitado (exento por estar disabled) |

Exentos: `.bicho .lupa` y `.rotulo` (opacity 0 por diseño: son el problema de affordance, no de contraste); `#loica-globo` al 56 % durante el fade.

### Overflow horizontal

| Página | 390 | 360 |
|---|---|---|
| index / mapa / habla / calendario / nosotros | ninguno (`scrollWidth` = `innerWidth`) | ninguno |

Único fuera de caja: `#loica-vuelo` en el mapa termina en x=454 (dentro de `overflow:hidden`; es el hallazgo del vuelo, no un overflow de página).

### Fuentes < 12 px visibles

| Página | Textos |
|---|---|
| todas | `.nav-inferior a span` 9,5 px/700 ×9 (`loica.css:256`) |
| index | "HOY" 10 px; `.cifra span` 11 px en móvil |
| mapa | `.miniatura .dia` 10 px ("20 AGO"); "HOY" 10 px |
| habla | `.rotulo` 11 px (solo hover) |
| calendario | `.marca-ev` 10,5 px (71 visibles a 1440), `.mas` 10 px, "HOY" 10 px → 18 textos a 1440, 7 en móvil |
| nosotros | solo la nav |

### Otros

- **Elementos bajo `.nav-inferior`:** ninguno real. La heurística marcó 3–8 por página en mapa y calendario, pero todos están dentro de contenedores con scroll cuyo borde inferior coincide con el borde superior de la barra (`bottom:var(--hueco-nav)`); en index/habla/nosotros el `padding-bottom:58px` del body lo evita.
- **`prefers-reduced-motion`:** cinco páginas con 0 animaciones corriendo y 0 px de diferencia entre dos cuadros a 700 ms; habla respeta además la espera mínima de 260 ms para que las opciones no caigan bajo el dedo.
- **Foco (Tab ×5):** anillo doble amarillo+tinta visible en logo/tema/idiomas (móvil) y en la nav superior (escritorio); en habla el foco parte en las opciones (Chrome mueve el punto de partida tras el `scrollIntoView`). Excepción: el enlace activo de la nav superior muestra solo la repisa.
- **`cursor:pointer`:** correcto en todo lo clicable; `grab` en el tirador; `default` solo en `#ev-prev` deshabilitado.
- **Emoji como ícono:** ninguno; glifos de texto en tema (☾/☀), calendario (‹ ›) y "✕ Limpiar filtros".
- **Acción primaria por pantalla:** una en index (hero y cierre), mapa (ficha), habla (acciones), nosotros (cierre); el calendario no tiene (es de exploración, está bien). Botones con verbo salvo "Panoramas de hoy", "Quién hace esto" y "Hoy".

---

## 9. Capturas y archivos (en `auditoria/`)

- Reutilizadas del intento anterior: `A-<pagina>-<390|768|1440>-<claro|oscuro>.png` (+ `-fold` a 390 y 360, `-tab5` a 390/1440, `-reduced` a 390), `A-index-*-ficha-animal`, `A-mapa-*-chip`, `A-mapa-*-ficha`, `A-mapa-{768,1440}-*-vacio` (inválidas: la ficha quedó abierta), `A-habla-*-turnos`, `A-habla-*-resultado` (llega hasta la pregunta de plata), `A-calendario-*-dia`, `A-calendario-*-chip`.
- Nuevas: `A-mapa-390-claro-5s.png`, `A-mapa-390-claro-tras-resize.png`, `A-mapa-{390,1440}-claro-vacio2.png` (vacío real), `A-mapa-{390,1440}-claro-vuelo.png`, `A-habla-{390,1440}-claro-resultado2.png` (resultado completo), `_banda-390-dpr2-mobile{,-pan}.png`, `_banda-390-dpr1-desktop.png`, `_banda-1440-dpr2.png`; rebanadas legibles `_s-<captura>-<n>.png` (57).
- Datos: `medidas-*.json`, `resumen-*.json`, `resumen-texto.txt`, `targets-coarse-390.json`, `sonda-mapa.json`, `sonda-habla.json`; scripts `captura.py`, `medir.js`, `resumir.py`, `targets_coarse.py`, `_rebanar.py`, `_sonda_mapa.py`, `_sonda_habla.py`.


---

# Parte B — talleres, descuentos, comer, blog, agrega y una ficha (informe completo)

**Páginas:** `talleres.html`, `descuentos.html`, `comer.html`, `blog.html`, `agrega.html` y la ficha `e/002da2db71ee5e85.html` (Boxeo Mujeres, con `og:image` real).
**Contra qué se juzga:** `web/_direccion_visual.md` (§0, 1, 4-9), `loica.css`, `_ux_filtros.md` y las dos críticas previas (`notas/_critica_diseno.md`, `notas/_critica_navegacion.md`), para marcar qué de lo prometido no se cumplió.
**Método:** Playwright para Python, Chromium y WebKit. 390×844 (móvil, DPR 2, táctil), 768×1024 y 1440×900; claro y oscuro; `networkidle` + 0,9 s. Mediciones con `page.evaluate` (`B-medir.js`): áreas táctiles, contraste WCAG real (color y primer fondo opaco ascendente, con opacidad acumulada), overflow a 390 y 360, elementos bajo `.nav-inferior`, fuentes < 12 px, mascotas por página, formulario. Mediciones puntuales en `B-extra.py` (`B-extra.json`). Todo en esta carpeta; ninguna captura ni cifra de abajo es estimada.
**Severidad:** *bloquea* = impide una tarea principal en celular; *importante* = degrada la experiencia o incumple el contrato visual a la vista; *pulido* = detalle.

Dos notas de método que conviene saber antes de leer:

- **WebKit en local pintaba las páginas en blanco.** No es un bug del sitio: `upgrade-insecure-requests` en la CSP hace que Safari suba `http://localhost/loica.js` a `https://` (error TLS); Chrome exime localhost. Verificado con consola y red (`B-webkit-debug.py`). Se repitió la pasada quitando la directiva al vuelo (`B-wk-*.png`) y la paridad con Chromium es total (mismos conteos de blancos, contraste y fuentes). Durante la auditoría otra sesión quitó la directiva de los HTML del proyecto; es coherente con esto.
- **Las cifras de "elementos tapados por la nav"** en páginas que scrollean (comer, blog, agrega, ficha) son falsos positivos de carga: el contenido pasa por debajo de la barra al hacer scroll y las cuatro reservan el hueco (`body.con-nav-inferior`, 58 px). Solo cuentan los casos de descuentos y talleres, que son páginas de alto fijo.

---

## Resumen: los 10 hallazgos que más pesan

1. **Descuentos, 390: el botón "Mapa" y el contador no existen para el celular.** Viven en el riel del día, que mide 713 px en un viewport de 390 y no tiene barra ni degradado: `#ver-mapa` parte en x=494, `#cuenta` en x=586. *Bloquea.*
2. **Descuentos: la ficha y el mapa terminan debajo de la barra inferior.** `.ficha` y `.panel-mapa` son absolutos dentro de un `main` con `padding-bottom` para la nav, y el padding no les aplica: el botón "Ver en la página del banco" queda en y=771-820 con la nav en 786 y la ficha sin scroll (clientHeight = scrollHeight = 437). Se ven 15 px del botón. *Bloquea.*
3. **Talleres: 65 de 69 tarjetas dicen "—" de precio.** Era el criterio de PASS n.º 1 de la crítica de diseño y sigue igual; la ficha del mismo taller dice "Sin información". *Importante.*
4. **El mapa de descuentos es una mancha:** 256 pines de 34 px, 175 solapados (68 %) a zoom 11,4, sin clúster; y en modo oscuro sigue con teselas claras, al revés que talleres y mapa. *Importante.*
5. **~27 pares de texto bajo 4,5:1**, casi todos por la misma causa: cada página decide sola el color del texto sobre color. Tinta azul sobre teal/verde en los chips activos de talleres (3,49 / 2,83), nombre del banco en color de relleno (hasta 2,47 de noche), hora del blog en oscuro (1,97), badge "HOY" (3,96 claro / 2,76 oscuro), "El finde" (3,96). El contrato §7.6 ya tiene la regla. *Importante.*
6. **Estados vacíos sin salida** en talleres y descuentos: animal durmiendo al 50 % de opacidad, "Prueba sacando alguno" y ningún botón; "✕ Limpiar" está al final de un riel de 1.100 px. Pedido en B9/C10 y en `_ux_filtros` §5.1. *Importante.*
7. **Los animales guía no tienen rol en talleres ni presencia en descuentos:** el Chungungo se repite idéntico en los 6 chips de talleres (no distingue nada) y el Chincol mide 18 px y está fuera de pantalla a 390; el Guarén sí codifica el banco, pero nunca pasa de 44 px. En comer el Quiltro aparece 30 veces por pantalla (dos por tarjeta sin foto). *Importante.*
8. **Blog: tarjetas fantasma.** 4 de 9 recomendaciones del post "Gratis de verdad" y 10 de 10 del post vencido son cajas grises "Este panorama ya no está en la base de datos"; botones de 33 px, "← Volver" de 20 px y una leyenda de formatos con contorno y repisa que no se puede tocar. *Importante.*
9. **Agrega: nada marca los 5 campos obligatorios**, los errores no llevan `aria-invalid`/`aria-describedby`, `#precio` no tiene label, el formulario empieza a 817 px de alto en celular (la crítica C11 lo medía en 777 y pedía bajarlo) y el éxito sigue diciendo "¡Gracias!" sin saber si el correo salió. *Importante.*
10. **Ficha: "Ver en la página de talleres" lleva a un hash que `talleres.html` no lee** (0 referencias a `location.hash`), la foto es la única del sitio sin contorno ni repisa y la descripción llega cortada con "…" desde el pipeline. *Importante.*

Y un bonus de Chromium: en talleres, 4 de 5 cargas a 390 y 768 muestran una **banda beige de ~58 px sobre el mapa** (bajo los filtros) que persiste 3,5 s después de `networkidle` y desaparece al mover el mapa. No ocurre en WebKit.

---

## talleres.html

**Veredicto:** funciona como lista, pero no como sección con carácter: es el esqueleto de descuentos con otro naranjo, el Chincol no aparece, el mapa es de círculos sin casa y casi todas las tarjetas dicen "—".

| # | Sev. | Hallazgo | Evidencia | Qué está mal | Arreglo |
|---|---|---|---|---|---|
| 1 | importante | "Todos" y los 27 talleres que solo viven ahí son inalcanzables a 390 | `B-talleres-390-claro.png` (riel cortado en "do"); `B-extra.json` → `segm_todos.x=416`, `segm_dom.x=363`; riel 674 px en 390, `scrollbar-width:none` | El segmentado de 9 opciones más "Revisado el" miden 674 px; nada avisa que hay más. La nota dice "27 no declaran sus días y están en Todos" y "Todos" no se ve | A <480 px: "Hoy · Semana · Todos" + día en desplegable, o segmentado en dos filas; como mínimo, `mask-image` de borde y "Todos" fijo a la derecha |
| 2 | importante | 65 de 69 precios son "—" | `B-extra.json` → `precio_guion:65`; `tarjetaEvento()` en loica.js (`.precio.sin-dato`); criterio PASS 1 de `_critica_diseno` | El guion es un campo roto, no honestidad; la ficha del mismo taller dice "Sin información" | No pintar la celda sin dato, o "Precio en la fuente"; para talleres municipales exportar inscripción/arancel cuando exista |
| 3 | importante | Banda beige de ~58 px sobre el mapa al cargar (Chromium) | `B-talleres-390-claro.png`, `B-talleres-768-claro.png`, `B-talleres-390-claro-espera3s.png` (3,5 s), `B-talleres-390-banda-pan.png` (desaparece al mover); `B-banda.py` | El mapa nace con el header a medio pintar (riel y filtros se llenan tras el `fetch`), el `ResizeObserver` hace `resize()` y la fila superior de teselas no se repinta. Intermitente (4 de 5 cargas), no en WebKit | Crear el mapa después del primer `pintarTodo()`, o fijar `min-height` en `.riel-fecha`/`#filtros` para que el header no cambie de alto; y `mapa.resize()` + `triggerRepaint()` tras pintar filtros |
| 4 | importante | Pines de 8-18 px, sin animal, sin contorno de casa | `montarCapas()`: `circle-radius` 4→9 (z10→z14), a z11,4 ≈ 12 px de diámetro; `B-talleres-390-claro.png` vs `B-ref-mapa-390-claro.png` | Contrato §7.3 (gota + carita + casco + repisa). El popup se abre tocando un blanco de 12 px. Tres lenguajes de pin en el sitio | Capa `symbol` con la gota+carita como sprite (una por categoría), o `circle-radius` 11-14 con `circle-stroke-width:2.5` y `--contorno`; 24 px mínimos a z≥11 |
| 5 | importante | La misma carita 6 veces; el Chincol no aparece | Chips Gimnasia/Baile fitness/Natación/Fútbol/Por equipos/Deporte = Chungungo ×6 (`pintarFiltros`, `colorTipo`); Chincol 18 px en `#cuenta` con x=486 (fuera de pantalla) | La carita no distingue nada y el animal guía de la página no está. Contrato §6.5: uno grande por pantalla | Chips de subtipo sin animal (o glifo del subtipo); Chincol a 72-96 px en el panel junto a "69 talleres" (posada) y en el vacío (durmiendo, ya está) |
| 6 | importante | Estado vacío sin salida | `B-talleres-390-claro-vacio.png`; `.vacio svg{opacity:.5}` (loica.css); "✕ Limpiar filtros" en x>900 del riel | B9, C10 y `_ux_filtros` §5.1 pedían botón y decir cuál filtro sobra; la opacidad .5 hace que el Chincol parezca deshabilitado | Botón "Quitar filtros" en el vacío; opacidad 1 y color tenue real; pista con el filtro culpable |
| 7 | importante | Chips activos ilegibles | "Gimnasia" activo: #1E2A4A sobre #0C8B9B = **3,49:1**; "Gratis" activo: sobre #2E7D5B = **2,83:1** (12 px/700). `header .filtros .chip[aria-pressed=true]{background:var(--tono);color:var(--azul-900)}` | El comentario del CSS asume tono claro (naranjo); teal y verde son oscuros. Contrato §7.6: los oscuros llevan crema | `--tono-tinta` por categoría (crema sobre oscuro, tinta sobre claro), como ya hace `[data-pagina]` con `--nav-tinta` |
| 8 | importante | Badge "HOY" 10 px bajo contraste | blanco sobre #E8442E **3,96:1**; oscuro: sobre #F47662 **2,76:1**. `.miniatura .dia.pronto{background:var(--acento)}` (loica.css §5) | Mismo badge en mapa, calendario y descuentos | `--acento-solido` (#D13B27, 4,9:1) en claro; en oscuro tinta azul sobre el salmón; 11 px |
| 9 | pulido | El mismo dato tres veces | Títulos "Sala de Máquinas Plan Libre Lu a Vi 06:30 h. / Sa 09:00 h." + hora "06:30" + "↻ lunes, martes, miércoles, jueves, viernes y sábado" (2 líneas) | Horario embebido en el título de origen; cadencia larga | Pipeline: limpiar el horario del título cuando ya está en `dias_semana`; cadencia compacta ("lun a sáb") |
| 10 | pulido | Tirador, zoom y atribución | `.barra-tirador` 44×4,5 px gris #BEB6A9 (contrato §7.5: 52×7 tinta); zoom ± 29×29 arriba a la izquierda (C6 pedía quitarlos en celular); atribución OSM/CARTO bajo la nav (top 810 > 786) porque el mapa llena `main` hasta el borde | | Pastilla de tirador; zoom solo en ≥880; `#mapa-talleres{bottom:var(--hueco-nav)}` en móvil |
| 11 | pulido | Sin `<h1>` | `h1=[]` en la medición; igual en descuentos | La página no se nombra: solo `<title>` y la pastilla de la nav | `<h1>` visual-oculto o en el conteo ("Talleres y clases · 69 hoy") |
| 12 | pulido | Glifos como íconos | "↻", "✕", "▾" (`.chip-select::after`), "☾/☀" | Contrato §9.11 | SVG de 16 px con `currentColor` |

Lo que está bien y no hay que tocar: el segmentado con "Hoy" destacado, la tarjeta compartida con el mapa, la nota honesta de geo y de días, el popup con borde de tinta, teselas oscuras de noche, `overscroll-behavior` en la lista, el pie "los cupos los maneja cada organizador".

---

## descuentos.html

**Veredicto:** la sección con más carácter del grupo (Guarén teñido por banco, lomo de color, porcentaje grande en Baloo), pero en celular dos cosas están rotas: el botón Mapa y el contador no se ven, y el final de la ficha —con el botón al banco— queda bajo la barra inferior.

| # | Sev. | Hallazgo | Evidencia | Qué está mal | Arreglo |
|---|---|---|---|---|---|
| 1 | **bloquea** | Botón "Mapa" y contador fuera de pantalla a 390 y 360 | `B-descuentos-390-claro.png`; `B-extra.json` → `ver_mapa.x=494` (right 581), `cuenta.x=586`; `.riel-fecha` scrollWidth 713 (oculto 323 px; 353 a 360); `B-descuentos-390-claro-mapa.png` solo existe porque el script scrolleó el riel | El mapa de descuentos no existe para quien no descubre el scroll horizontal (sin barra, sin degradado). Tampoco se ve cuántos descuentos hay | Fila propia bajo el día: conteo a la izquierda, "Mapa" a la derecha; o "Mapa" como botón flotante sobre la lista (abajo a la derecha, zona del pulgar) y el conteo sobre la lista como en talleres |
| 2 | **bloquea** | La ficha y el mapa terminan debajo de la nav inferior | `.ficha{position:absolute;inset:auto 0 0 0}` (~l.195) y `.panel-mapa{inset:0}` (~l.160) dentro de `main{padding-bottom:var(--hueco-nav)}` (~l.253): el padding no aplica a hijos absolutos. Medido (Rappi): botón banco y=771-820, nav top=786, ficha bottom=844, `clientHeight=scrollHeight=437` (no scrollea); `#nota-mapa` top 764 / bottom 832. `B-wk-descuentos-390-claro-ficha.png`, `B-descuentos-390-claro-ficha.png`, `B-descuentos-390-claro-mapa.png` (nota cortada) | Se ven 15 px del CTA en fichas cortas; en fichas largas el último botón ("Ir al sitio del local") nunca sube por sobre la barra; la nota del mapa se lee a medias | `@media(max-width:879px){.ficha,.panel-mapa{bottom:var(--hueco-nav)}}` — exactamente lo que talleres hace con `.panel-lista` |
| 3 | importante | CTA de la ficha bajo el pliegue también a 1440 | `B-descuentos-1440-claro-ficha.png`: 50 %, días, dónde, rubro, hasta, 12 pastillas de tarjetas y el párrafo de condiciones antes del botón; no se ve en 900 px | B1/C3 de las críticas previas pedían CTA siempre visible | `.ficha-cta{position:sticky;bottom:0}`; tarjetas colapsadas ("12 tarjetas ▾"); condiciones después del botón |
| 4 | importante | Mapa: 256 pines, 175 solapados; claro de noche | `B-extra.json` → `mapa.solapados:175`, `pin0 34×34`; `B-descuentos-390-claro-mapa.png` (Providencia es una mancha); `TESELAS` = voyager único (l.635), `B-descuentos-390-oscuro-mapa.png` | Sin clúster es ilegible y no se puede tocar (34 px y encimados); talleres y mapa sí cambian teselas | `cluster:true` en la fuente + círculo con conteo; pines de 44 px; teselas dark como `estiloMapa()` de talleres |
| 5 | importante | El nombre del banco va en color de relleno, no en tinta | `.tarjeta .banco-nombre{color:var(--banco)}` (loica.css §5) aunque `BANCOS[x].tinta` existe (loica.js). Claro: Cencosud **3,93**, Falabella **4,41**; oscuro: Entel **2,47**, Santander **2,74**, Banco de Chile **2,99**, Falabella **3,26**, Cencosud **3,65**; `.ficha-banco` igual (2,99) | Contrato §9.4 y la nota de `CATEGORIAS`: "tinta es el único que puede tocar texto" | `--banco-tinta` desde `b.tinta` (las `--c-X-tinta` ya invierten en oscuro) |
| 6 | importante | Con "Hoy" puesto, las 80 cintas son rojas | `B-extra.json` → `diasPronto:80/80`; `cintaDia()`: `hoy` es siempre true bajo el filtro Hoy; blanco sobre #E8442E 3,96 (10 px) | El rojo deja de señalar y encima no contrasta | Rojo solo cuando el filtro no es Hoy; cinta en tinta y el día de hoy en rojo dentro de la ficha (ahí sí funciona) |
| 7 | importante | Estado vacío sin salida | `B-descuentos-390-claro-vacio.png`: Guarén durmiendo al 50 %, "Prueba sacando alguno", sin botón; "✕ Limpiar" en x>1.000 del riel | Igual que talleres | Botón en el vacío; opacidad 1 |
| 8 | importante | Ficha sin semántica de diálogo | `B-extra.json` → `hayFoco:"fuera"`, `role:null`, `ariaModal:null`, sin telón; solo cambia `aria-hidden`. Escape sí cierra | Teclado y lector de pantalla se quedan en la lista de atrás | `role="dialog"` + `aria-modal`, foco al `.cerrar` al abrir y de vuelta a la tarjeta al cerrar, `inert` en `#lista` mientras está abierta |
| 9 | pulido | Copy y datos | "Ver más panoramas →" (`t("verMas")`) en una lista de descuentos; "Av. Pedro de valdivia 1738, Providencia · Providencia" (comuna duplicada, 3 de 80); 27 de 80 con "Metropolitana"/"Todo Chile" como dirección; Entel y Ripley comparten el café por defecto, así que el lomo ya no identifica banco | | `t("dVerMas")`; quitar la comuna de la dirección si ya termina en ella; "Sin dirección" explícito; color propio para los bancos nuevos |
| 10 | pulido | Glifos y letras chicas | "◉" en `.boton-mapa::before`, "▾", "✕", "→"; pastillas 11,5 px, texto de pin 11 px | Contrato §9.11; fuentes <12 | SVG; 12 px |
| 11 | pulido | Pastel fijo de noche | `.aviso-banco` #F0D8BE con tinta azul fija: franja clara en oscuro (`B-descuentos-390-oscuro.png`) | Las `--c-X-suave` no tienen variante oscura (mismo problema en blog, comer y agrega) | Definir `--c-X-suave` en `[data-tema=oscuro]` (tono 800 de cada familia) |
| 12 | pulido | Sin `<h1>`; zoom ± 29 px; `.enlace-lugar` 194×18 | medición | | como talleres; `display:inline-block;padding:12px 0;margin:-12px 0` en el enlace |

Lo que está bien: lomo por banco + Guarén teñido (la única página donde el animal codifica un dato real), el 50 % en Baloo con contorno y repisa, la pastilla roja del día de hoy en la ficha, la dirección como link a Maps, "Eso es todo lo que hay con esos filtros", las condiciones en letra chica pero completas, Escape para cerrar.

---

## comer.html

**Veredicto:** la página más diseñada del grupo y la única que se siente escrita por una persona; lo que sobra es Quiltro (30 por pantalla) y lo que falta es que los chips y el velo sigan el contrato.

| # | Sev. | Hallazgo | Evidencia | Qué está mal | Arreglo |
|---|---|---|---|---|---|
| 1 | importante | El Quiltro 30 veces por pantalla, dos por tarjeta | Medición: cabecera 66 px ×1, medalla 24 px ×14, respaldo 97 px ×14 (visible en 5 sin foto); `B-comer-390-claro.png`, `B-comer-1440-claro.png` | En las 5 tarjetas sin foto el perro sale en la medalla y en el fondo, idéntico; cinco clones se leen como "sin foto", no como identidad | Esconder la medalla cuando el respaldo es el Quiltro; variar el respaldo (solo cabeza asomada por un borde, recorte distinto) o foto propia en `web/fotos/comer/` (hoy solo hay el LEEME) |
| 2 | importante | Chips de cocina fuera del sistema | `.filtros button`: 38 px, Manrope 800, borde `--borde-fuerte` gris, sin repisa ni animal; y `.filtros` hereda `background:var(--fondo-elevado);border-bottom:1px` de loica.css → rectángulo plano detrás de los chips (`B-comer-390-claro.png`) | Tercer chip distinto del sitio; contrato §7.1 | `.chip` de loica.css con `flex-wrap`; `background:none;border:0` en el contenedor |
| 3 | importante | Velo con degradado y sombras difusas | `.local-velo` `linear-gradient(to top, rgba(12,18,34,.92)…)`; `text-shadow:0 1px 3px` en `.local-texto h2`, `.local-donde`, `.local-tipo` | Contrato §4.2/§4.5: cero blur, cero degradados en superficie. Sobre foto es defendible; sobre el pastel de las tarjetas sin foto es un degradado sobre superficie plana | Banda sólida de tinta bajo el nombre (o casco crema con contorno, como la medalla); sin `text-shadow` |
| 4 | importante | Letras chicas sobre foto | `.local-donde` 10,5 px/800, `.estrella` 11 px, `.dato b` 11 px | Bajo el piso de 12 px; el medidor marca además 1:1 en `.local-donde`, pero es falso positivo (compara contra el pastel y no contra el velo) | 12 px; mantener el velo o la banda detrás |
| 5 | pulido | "Cuándo ir:" se parte en dos líneas | `B-comer-390-claro-local.png`, `B-comer-390-claro-local-sinfoto.png`: "Cuándo / ir:"; `.pedir .cuando` es flex y el `<b>` se encoge | | `.pedir .cuando b{flex:none;white-space:nowrap}` |
| 6 | pulido | "Cocina" queda huérfana | `.datos{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}`: a 390 son 2 + 1 | | 1 columna bajo 480 px, o 3 iguales con `minmax(0,1fr)` |
| 7 | pulido | Voz | "avísame y lo corrijo" (1.ª persona singular) en un sitio que dice "Revisamos", "Te mandamos", "quien hace esto" | Regla editorial: declarativo, sin persona | "avisa y lo corregimos" |
| 8 | pulido | El remate de cordillera es morado | `cordillera()` sin `tono` → `--c-fiesta` en comer, blog y agrega | No toma el color de la sección; la portada sí tiñe | `cordillera({tono:"var(--c-comer)"})` |
| 9 | pulido | Fotos hotlinkeadas | 9 de 14 desde dominios ajenos (`fotosLocales` en `B-extra.json`); 0 rotas hoy | Cualquier cambio de CDN cae al clon del punto 1 | Foto propia o `referrerpolicy`/caché local |
| 10 | pulido | Estados | Carga, error, "no encontramos ese local" y "nada de esa cocina" existen y usan el Quiltro (`B-comer-390-claro-noencontrado.png`) | Bien; solo la opacidad: `var(--tinta-tenue)` gris en todos | Color real o pose |

Lo que está bien: la tarjeta cuadrada con el nombre encima, la medalla y "Imperdible", "El pero." rotado −2° (uno de los dos ángulos permitidos por pantalla, bien usado), los datos duros arriba, "Qué hay que pedir" en pastel con contorno, la declaración de no-canje, los tres botones con verbo ("Cómo llegar", "Su sitio", "@cuenta"), compartir a 44 px.

---

## blog.html

**Veredicto:** el índice tiene carácter (tarjetas flotantes con repisa, tres animales con formato), pero el post es frágil: recomendaciones fantasma, botones de 33 px, hora invisible de noche y un "volver" de 20 px.

| # | Sev. | Hallazgo | Evidencia | Qué está mal | Arreglo |
|---|---|---|---|---|---|
| 1 | importante | Tarjetas fantasma | Post "Gratis de verdad": `recos:9`, `rotas:4` (`B-extra.json`); post "este-finde" (vencido): 10 de 10 rotas (`B-blog-390-claro-post-vencido.png`, una columna de diez cajas grises) | "Revisado a mano, uno por uno" seguido de más cajas rotas que panoramas | En post vencido: las notas como lista simple sin marco de error; en post vigente: colapsar las rotas en una línea ("2 ya pasaron") y conservar la nota como texto |
| 2 | importante | Hora invisible en oscuro | `.reco-hora{color:var(--cat-tinta)}` con `--cat-tinta:${info.tinta}` (hex de claro, l.556): **1,97:1** y **2,13:1** sobre #1E2740 (`B-blog-390-oscuro-post.png`) | Se usó el hex en vez de la variable que invierte | `--cat-tinta:${info.tintaVar}` |
| 3 | importante | Blancos chicos en el post | `.reco-botones .boton` 33 px ×10 (`padding:8px 14px`, l.216); `a.volver` 96×20 (sin el `min-height:44` que sí tiene en comer y en la ficha); `h3 > a` 34 px | | `min-height:44px` en los tres |
| 4 | importante | La leyenda de formatos parece un control | `.formato-chip`: contorno 2,5 px + `--repisa-2` + pastel; `interactivo:false` ×3 | Contrato §4.1: contorno + repisa = "se toca" | Que filtren el índice por formato (es la estructura que codifica algo verdadero), o quitarles la repisa |
| 5 | importante | Contrastes | "El finde" blanco sobre #E8442E **3,96** (`PALETA_FORMATO.finde.tono = rojo-500`); "Gratis" crema sobre #0E8757 **4,41**; "Música" blanco sobre #DE3A1E **4,44** (12-13 px/800); `.reco-rota-msg` **3,57** por `opacity:.75` de `.reco-rota` | | Tonos 600 para pastillas con texto (`--acento-solido`, `--c-musica` oscurecido); opacidad 1 y tinta tenue real |
| 6 | pulido | Caritas bajo 22 px | `.reco-cat .bolita` 19 px, `.reco-rota-msg` 20 px; pastillas de 11 px (`.reco-dia`, `.bandera`, `.etiqueta-evergreen`) | Contrato §6.3 | 22 px; 12 px |
| 7 | pulido | Pasteles fijos de noche | `.formato-chip` y `.reco-nota` con `--suave` y tinta azul fija (`B-blog-390-oscuro.png`) | | variante oscura de `--c-X-suave` |
| 8 | pulido | Cabecera | Loica a 56 px (contrato §6.5: 120) cuando el blog tiene tres animales propios; remate morado | | Los tres animales a 96 px como cabecera, o el del formato más reciente |
| 9 | pulido | Enlace con doble salto | "Ver en el mapa" → `index.html#/e/<id>` → redirect a `mapa.html#/e/` | Funciona gracias al redirect de la portada | Apuntar directo a `mapa.html#/e/` |
| 10 | pulido | Post en portugués | El banner de idioma no aparece cuando coincide (bien); los botones quedan en español bajo IDIOMA=es (`B-blog-390-claro-post-pt.png`) | Esperable | — |

Lo que está bien: la tapa con la foto del primer panorama, la pastilla de formato con animal, "N panoramas revisados", el banner de vencido honesto, "Gratis" verde en pastilla, la nota del editor en globo con el animal del formato, el CTA final "Ver los 9 panoramas en el mapa", compartir con `navigator.share`.

---

## agrega.html

**Veredicto:** funciona y el copy es honesto, pero se siente formulario genérico: hero centrado + tres cajas + panel largo. Nada de lo que las dos críticas previas pidieron para esta página se implementó (promesas sin caja, formulario arriba en celular, éxito que no mienta, Chincol a 120 px celebrando).

| # | Sev. | Hallazgo | Evidencia | Qué está mal | Arreglo |
|---|---|---|---|---|---|
| 1 | importante | Obligatorios sin marcar | `required` en titulo, fecha, lugar, contacto-nombre, contacto; `requiredMarcado:0`, `ariaRequired:0` (`B-extra.json`) | Se descubre qué falta al enviar: 5 errores de golpe (`B-agrega-390-claro-errores.png`) | Marcar los 5 en la etiqueta y decir arriba "Solo 5 campos son obligatorios" |
| 2 | importante | Errores sin semántica | `ariaInvalid:0`, `ariaDescribedby:0`, sin `role=alert`; mensaje 12 px #E8442E sobre crema **3,85:1**. El foco sí va al primer inválido y scrollea (bien) | Lector de pantalla no sabe qué campo falló ni por qué | `aria-invalid="true"` + `aria-describedby` al mensaje; `--acento-solido`; 13 px |
| 3 | importante | Label huérfano y grupo sin fieldset | `#precio` sin label asociado (la etiqueta "Precio" no tiene `for`, l.117); "¿Qué tipo de panorama es?" es un `<label>` sin control | | `for="precio"` en una etiqueta propia ("Valor"); `<fieldset><legend>` para las categorías |
| 4 | importante | El formulario empieza a 817 px | hero 355 px + promesas 329 px; página de 2.578 px a 390 (C11 lo medía en 777 y pedía comprimir; `B-agrega-390-claro.png`) | Quien llega a publicar pasa una pantalla entera de tranquilizadores | Hero compacto en celular (mascota 56, bajada de una línea), promesas debajo del formulario o como una línea |
| 5 | importante | Éxito que afirma lo que no sabe | Tras el `mailto:` muestra "¡Gracias! Revisa que tu correo se haya enviado" (`B-agrega-390-claro-exito.png`); ya marcado en `_critica_diseno` (menciones) y sin cambio; Loica 70 px en verde, no el Chincol celebrando (contrato §6.5) | Marca "honesta" con estado que miente | "Casi listo: envía el correo que se abrió" + botón "Copiar el texto" + Chincol celebrando |
| 6 | importante | Chips de categoría fuera del sistema | `.opcion-cat`: 40 px (<44), borde 1,5 px gris, Manrope 600, animales 18 px (<22), sin repisa; activo = tinta (`B-agrega-390-claro.png`) | Cuarto chip del sitio | `.chip` (44 px, Baloo, contorno, repisa) sobre los radios ocultos |
| 7 | pulido | Promesas en caja | `.promesa{border:1px solid var(--borde)}` (l.38), `b` y `span` ambos 13 px | B12 pidió sacar la caja y dar jerarquía | `border-top:3px solid var(--acento)`, `b` 15 px |
| 8 | pulido | Casilla 24×24 | `#es-gratis` 24 px (la fila sí mide 44 y el label es clicable) | Solo el input es chico | Casilla dibujada de 28 px con contorno, o dejar como está |
| 9 | pulido | Sin validación de formato | Solo vacío: un contacto "hola" o una fecha pasada pasan | | Patrón para correo/@usuario y fecha ≥ hoy, con mensaje que diga cómo arreglarlo |
| 10 | pulido | Mascota y remate | Chincol 84 px (contrato 120, "al lado del formulario"); remate morado | | 120 px, `cordillera({tono:"var(--c-clases)"})` |

Lo que está bien: el copy de las promesas y de los errores (voz propia), inputs a 16 px (sin zoom de iOS), `inputmode` numérico/url, `autocomplete` name/email, fila del checkbox a 44 px, orden de tabulación lógico (0 tabindex positivos), label visible con el teclado abierto a 390×500 (`B-agrega-390x500-claro-teclado.png`), panel con contorno y repisa, un solo botón primario con verbo.

---

## Ficha `e/002da2db71ee5e85.html`

**Veredicto:** la ficha compartible está bien ordenada (CTA sobre el pliegue, compartir, datos), pero se ve más pobre que el resto: la foto flota sin contorno, la descripción llega cortada y el botón secundario promete algo que talleres no cumple.

| # | Sev. | Hallazgo | Evidencia | Qué está mal | Arreglo |
|---|---|---|---|---|---|
| 1 | importante | "Ver en la página de talleres" apunta a un hash que nadie lee | `href="../talleres.html#/e/002da2db71ee5e85"`; `grep hash talleres.html` = 0 resultados | Abre la lista general sin seleccionar ni centrar el taller | Que talleres interprete `#/e/<id>` (centrar + popup) como hace `mapa.html`; mientras tanto, quitar el botón (arriba ya está "← Ver todos los talleres y clases") |
| 2 | importante | Foto sin casa | `.foto`: `fotoBorde: 0px none` (sin contorno ni repisa); comer `.ficha-foto` lleva 3 px + `--repisa-4`, blog `.post-tapa` 3 px | Única imagen del sitio sin contorno de tinta; contrato §4.1 | `border:2.5px solid var(--contorno);box-shadow:var(--repisa-2)` |
| 3 | importante | Descripción truncada con "…" | 4.ª fila de datos termina en "(como jabs, directos, esquivas y…"; `descripcionCortada:true`; el `<meta description>` igual | La ficha es la página canónica que se comparte por WhatsApp | Exportar la descripción completa y cortar con `line-clamp` + "Leer más" |
| 4 | pulido | La cadencia no aparece | `dias_semana:[1,3]` existe pero "Cuándo: martes 25 de agosto, 18:30" esconde que es semanal; el h1 trae el horario embebido ("Ma-Ju 18:30 h.") | | Fila "Se repite: martes y jueves, 18:30-19:30" |
| 5 | pulido | Carita de 20 px en `--tinta-tenue` | `#etiqueta-cat` (contrato §6.3: 22 px) | | 22 px y `--c-X-tinta` |
| 6 | pulido | Sin remate de cordillera | Todas las páginas de contenido lo tienen | | `<div class="remate" id="cordillera">` |

Lo que está bien: CTA arriba del pliegue (y=472 a 390: B1/C3 cumplidos acá), orden categoría → título → acción → compartir → datos, "Precio: Sin información" (no "—"), pie de fuente, `og:image` real, compartir a 44 px con "Agendar", nav con raíz `../` correcta, `body.con-nav-inferior` reservando el hueco.

---

## Transversal

### Inconsistencias (también contra portada y mapa)

1. **Cuatro chips distintos.** `.chip` de loica.css (calendario: 42 px, Baloo, repisa 3 px), las cabeceras de mapa/talleres/descuentos (38 px, 12 px, repisa 2 px, redefinido en cada página), comer (Manrope, borde gris, sin repisa ni animal) y agrega `.opcion-cat` (40 px, borde 1,5 px, animal 18 px). El contrato define uno (§7.1, 44 px).
2. **Tres lenguajes de pin:** gota con carita (mapa), círculo pelado (talleres), disco con % (descuentos). Y de noche el mapa de descuentos se queda de día.
3. **Dos badges para la misma fecha:** banda recta navy/roja de 10 px en la miniatura (loica.css; mapa, calendario, talleres, descuentos) y pastilla contorneada del contrato §7.2 en el blog (`.reco-dia`).
4. **Presencia del animal guía:** portada 122 px, agrega 84, comer 64, blog 56, talleres 18 (fuera de pantalla), descuentos 22. Las dos páginas "app" no tienen ninguno grande en reposo.
5. **Tirador:** rayita gris 44×4,5 en mapa y talleres (contrato: pastilla 52×7 tinta). Zoom ± de 29 px en las tres páginas con mapa.
6. **Vacíos sin acción** en talleres, descuentos (y mapa, según el grupo A); `_ux_filtros` §5.1 sigue sin implementarse.
7. **Remate de cordillera:** morado fijo en comer, blog y agrega; ausente en la ficha; la portada sí lo tiñe por sección.
8. **Texto sobre color decidido página por página** (tinta sobre teal en talleres, crema sobre teal en descuentos, blanco sobre rojo-500 en blog): de ahí salen los ~27 pares bajo 4,5:1. El contrato §7.6 tiene la regla y la tabla.
9. **Pasteles `--c-X-suave` sin variante oscura:** islas claras de noche en descuentos (aviso), blog (leyenda, notas), comer (pedir), agrega (éxito).
10. **"Volver"** 44 px en comer y ficha, 20 px en blog; **"Ver más"** dice "panoramas" en descuentos; **`<h1>`** ausente en talleres y descuentos.

### Los 3 cambios que dan más aire nuevo con menos trabajo

1. **Un animal grande por sección y la cordillera del color de la página.** Chincol a 96 px posado junto a "69 talleres"; Guarén a 96 px en la franja del aviso de descuentos (en vez de la carita de 22); `cordillera({tono:var(--c-comer|--c-fiesta|--c-clases)})` en comer/blog/agrega y remate en la ficha. Una hora, y las secciones dejan de ser "la misma lista con otro color".
2. **Un solo chip y una sola regla de texto sobre color.** Reemplazar `.filtros button` (comer) y `.opcion-cat` (agrega) por `.chip`; un token `--tono-tinta` por categoría y por banco (crema sobre oscuro, tinta sobre claro) aplicado a chips activos, `.banco-nombre`, `.reco-hora`, pastillas de formato y badge del día. Arregla 4 componentes y 20+ contrastes de una.
3. **Sacar del riel lo que no es del riel y respetar el hueco de la nav.** Conteo + botón Mapa en fila propia (descuentos), "Todos" a la vista (talleres), `.ficha,.panel-mapa{bottom:var(--hueco-nav)}`, botón en los vacíos. CSS/HTML de una tarde; destraba los dos *bloquea*.

---

## Animales guía: dónde, tamaño, rol, problema

| Página | Dónde | Tamaño | Rol | Problema |
|---|---|---|---|---|
| talleres | chips (Chungungo ×6, Degú en Gratis) | 22 px carita | categoría / gratis | el mismo animal seis veces no distingue nada |
| talleres | miniaturas (animal de la categoría) | 44 px carita | respaldo sin foto | bien |
| talleres | "Revisado el" (Chincol) | 18 px | firma de la página | <22 px y fuera de pantalla a 390 (x=486) |
| talleres | vacío (Chincol durmiendo) | 78-96 px cuerpo | estado | pose correcta; `opacity:.5` lo apaga; sin botón |
| talleres | fin de lista (Chincol) | 26 px | sello "confirma en la fuente" | ok; único lugar donde el guía aparece en reposo |
| descuentos | chips (Guarén teñido por banco) | 22 px | banco | bien: codifica un dato real |
| descuentos | aviso (Guarén) | 22 px | firma | único guía visible; nunca pasa de 44 px |
| descuentos | miniaturas y avatar de ficha (Guarén por banco) | 44 px | banco | bien |
| descuentos | vacío (Guarén durmiendo) | 78 px | estado | `opacity:.5`; sin botón |
| descuentos | pines del mapa | — | — | sin animal (disco con %) |
| comer | cabecera (Quiltro, mueve la cola) | 64-66 px | anfitrión | ok (contrato pide 120) |
| comer | medalla por tarjeta (Quiltro) | 24 px ×14 | sello de la sección | duplicado con el respaldo en las 5 sin foto |
| comer | respaldo sin foto (Quiltro) | 97 px ×5 (121 a 1440) | "sin foto" | cinco clones idénticos; se lee como hueco |
| comer | ficha: respaldo 96, etiqueta 22, "quien" 32 en Qué pedir | 22-96 px | firma / voz de quien recomienda | bien |
| comer | estados (carga, error, 404, vacío) | 64-70 px | estado | en gris tenue; sin pose |
| blog | cabecera (Loica volando) | 56 px | anfitriona | genérica: el blog tiene tres animales propios |
| blog | leyenda de formatos (Loica/Pudú/Culpeo) | 26 px | formato | bien, pero dentro de "chips" que no se tocan |
| blog | pastilla de formato en tapa | 22 px | formato | bien |
| blog | tapa sin foto (Culpeo) | 84 px | respaldo | bien |
| blog | post: etiqueta 22, respaldo de reco 76 (animal de categoría), `.reco-cat` 19, "quien" de la nota 22, rota 20 | 19-76 px | categoría / voz del editor | 19 y 20 px bajo el mínimo; el animal de categoría en la nota es el del formato (bien) |
| agrega | hero (Chincol) | 84 px | guía de la página | contrato: 120 y celebrando al enviar; no celebra |
| agrega | opciones de categoría (11 animales) | 18 px ×11 | categoría | <22 px |
| agrega | éxito (Loica verde) | 70 px | estado | debería ser el Chincol celebrando |
| ficha e/ | etiqueta de categoría (Chungungo) | 20 px | categoría | <22 px; ningún animal grande (hay foto) |

---

## Métricas

### Áreas táctiles < 44 px (390, Chromium; el alto cuenta la extensión invisible `::before` de `pointer:coarse`, el ancho es el real)

| Página | Fallan / interactivos | 5 peores |
|---|---|---|
| talleres | 19 / 104 (33 sin contar la extensión) | `#tirador` 386×20 · zoom ± 29×29 ×2 · tema 33×26 · idiomas 33×29 ×3 · nav 43 de ancho ×9 |
| descuentos | 31 / 116 (+ficha/mapa: 36) | `.enlace-lugar` 194×18 · tema 33×26 · zoom ± 29×29 ×2 · idiomas 33×29 ×3 · `.pin-dcto` 34×34 ×256 · segmentado 42-57×36 ×9 |
| comer | 22 / 36 | tema 33×26 · idiomas 33×29 ×3 · logo 83×32 · chips de cocina ×7 a 38 px · nav 43 ×9 |
| blog | 14 / 17 índice; 29 / 36 post | `a.volver` 96×20 · `.reco-botones .boton` 33 px ×10 · `h3 > a` 34 px · tema · idiomas · logo |
| agrega | 15 / 26 | `#es-gratis` 24×24 · tema 33×26 · idiomas ×3 · logo 83×32 · `.opcion-cat` 40 px ×11 · nav ×9 |
| ficha | 14 / 23 | tema · idiomas ×3 · logo · nav 43×56 ×9 |

Comunes a todo el sitio: tema 33×26, idiomas 33×29 (la extensión les da 44 de alto pero no de ancho), logo 83×32, celdas de la nav inferior 43 px de ancho (40 a 360). En WebKit los conteos son idénticos.

### Contraste (pares únicos bajo el mínimo, claro y oscuro, todos los estados medidos)

| Página | Pares | Peores |
|---|---|---|
| talleres | 5 | HOY 2,76 (oscuro) · Gratis activo 2,83 · Gimnasia activo 3,49 · HOY 3,96 |
| descuentos | 12 | Entel 2,47 · Santander 2,74 · TODOS 2,76 · Banco de Chile 2,99 (lista y ficha) · Falabella 3,26 · Cencosud 3,65 (todos en oscuro) · Cencosud 3,93 · Banco de Chile 4,03 · Falabella 4,41 (claro) |
| comer | 0 reales | los 3 marcados (1:1-1,29) son falsos positivos: el medidor compara contra el pastel y el texto va sobre el velo |
| blog | 9 | hora 1,97 y 2,13 (oscuro) · rota 3,57 · "El finde" 3,96 · Gratis 4,41 · Música 4,44 |
| agrega | 1 | mensaje de error 3,85 |
| ficha | 0 | — |

### Overflow

Ningún viewport (390, 360) tiene overflow de documento. Rieles con scroll oculto (sin barra ni degradado): talleres `.riel-fecha` 284 px ocultos (314 a 360) y `#filtros` 580-729; descuentos `.riel-fecha` 323 (353 a 360) y `#filtros` 820-850. Chips de comer y agrega envuelven (sin recorte a 360).

### Fuentes < 12 px

Nav inferior 9,5 px (todas); badge del día 10 px (talleres, descuentos, mapa, calendario); descuentos: pastillas 11,5, pines 11; comer: `.local-donde` 10,5, "Imperdible" 11, `.dato b` 11; blog: `.reco-dia`, banderas y "Guía vigente" 11.

### Formulario (agrega)

22 campos; 1 sin label (`#precio`); 1 grupo sin fieldset (categoría); 5 obligatorios sin marcar; 0 `aria-invalid`/`aria-describedby`; 0 tabindex positivos; inputs a 16 px; label visible con el teclado a 390×500.

### Foco, movimiento, copy

- Foco visible: en las 6 páginas los 5 primeros Tab muestran el anillo doble (amarillo + tinta) y el elemento queda en pantalla (`B-*-390-claro-foco.png`, `B-*-1440-claro-foco.png`). Orden a 390: logo → tema → ES/EN/PT → contenido → nav inferior.
- `prefers-reduced-motion`: sigue el martillazo global (`*{transition:none!important;animation:none!important}`) y no la versión fina del contrato §8.5; efecto visible: el panel de talleres cambia de alto a saltos y la ficha de descuentos aparece sin transición. El Quiltro y la Loica dejan de moverse (bien).
- Copy: ningún "Benjamín", "bicho" ni "mascota" en texto visible de las seis páginas (solo nombres de clase `.bicho` en la portada). Voz: "avísame y lo corrijo" (comer) es la única primera persona singular.

---

## Capturas y archivos (en esta carpeta)

- **talleres (30):** `B-talleres-{390,768,1440}-{claro,oscuro}.png`, `-390-claro-{filtro,panel,panel-fin,vacio,foco,reducido,espera3s,sonda}`, `-390-oscuro-{filtro,panel,panel-fin,vacio}`, `-1440-claro-{filtro,panel,popup,vacio,foco}`, `-360-claro`, `-390-banda-{antes,despues,pan,zoom}`, `-768-banda-{antes,despues}`.
- **descuentos (27):** `B-descuentos-{390,768,1440}-{claro,oscuro}.png`, `-390-claro-{filtro,ficha,ficha-vp,lista-fin,mapa,mapa-vp,vacio,foco,reducido}`, `-390-oscuro-{filtro,ficha,lista-fin,mapa,mapa-vp,vacio}`, `-1440-claro-{filtro,ficha,mapa,vacio,foco}`, `-360-claro`.
- **comer (23):** `B-comer-{390,768,1440}-{claro,oscuro}.png`, `-390-claro-{filtro,local,local-sinfoto,noencontrado,foco,reducido}`, `-390-oscuro-{filtro,local,local-sinfoto,noencontrado}`, `-1440-claro-{filtro,local,local-sinfoto,noencontrado,foco}`, `-360-claro`, `-360-claro-bocanariz`.
- **blog (20):** `B-blog-{390,768,1440}-{claro,oscuro}.png`, `-390-claro-{post,post-vencido,post-pt,foco,reducido}`, `-390-oscuro-{post,post-vencido,post-pt}`, `-1440-claro-{post,post-vencido,post-pt,foco}`, `-360-claro`, `-360-claro-panoramas-gratis-santiago`.
- **agrega (17):** `B-agrega-{390,768,1440}-{claro,oscuro}.png`, `-390-claro-{errores,exito,foco,reducido}`, `-390-oscuro-{errores,exito}`, `-1440-claro-{errores,foco}`, `-390x500-claro-teclado`, `-390x500-claro-teclado-contacto`, `-360-claro`.
- **ficha (12):** `B-ficha-{390,768,1440}-{claro,oscuro}.png`, `-390-claro-{fin,foco,reducido}`, `-390-oscuro-fin`, `-1440-claro-foco`, `-360-claro`.
- **WebKit (15):** `B-wk-{talleres,descuentos,comer,blog,agrega,ficha}-{390,1440}-claro.png`, `B-wk-descuentos-390-claro-ficha.png`, `B-wk-agrega-390-claro-errores.png`, `B-wk-comer-390-claro-sinupgrade.png`.
- **Referencias (6):** `B-ref-{index,mapa,calendario}-{390,1440}-claro.png`.
- **Scripts y datos:** `B-captura.py` + `B-medir.js` (pasada principal) → `B-mediciones.json`, `B-captura.log`; `B-resumir.py` → `B-resumen.txt`; `B-extra.py` → `B-extra.json`; `B-webkit.py` → `B-wk-mediciones.json`, `B-webkit.out`; `B-webkit-debug.py` (diagnóstico de la CSP); `B-banda.py`, `B-banda2.py` (banda del mapa).
