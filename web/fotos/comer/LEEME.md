# Fotos de "Dónde comer"

## Cómo funciona hoy

El campo `foto` de cada local en `web/comer.json` es una **URL al servidor del
propio local** (su sitio, su bodega de imágenes o su plataforma de reservas).
Es la misma regla que usa el resto del sitio: las fotos de los eventos se
enlazan a las del organizador, **nunca se copian**.

Eso tiene dos consecuencias conocidas:

1. Si el local cambia de sitio, la foto muere. Cuando eso pasa, `onerror` la
   saca y la tarjeta queda con el pastel oliva y el Quiltro, que es un estado
   válido y no un hueco roto.
2. Algunos servidores bloquean la lectura desde otro dominio (hotlink
   protection). `barriolastarria.cl`, por ejemplo, devuelve 404 si el pedido
   viene desde fuera, así que sus fotos no sirven acá aunque se vean bien en
   el navegador.

## Cuáles faltan

Estos cinco locales no tienen sitio propio con una foto enlazable —publican
solo en Instagram, y las URL del CDN de Instagram caducan en horas:

```
alleria            Instagram: @alleria.cl
costa-bright       Instagram: @costa_bright
bar-de-rene        el sitio es JS y no expone imágenes
margo              el sitio solo publica el logo
ramen-kintaro      Instagram: @ramenkintaro
```

Y uno tiene una imagen que **es su logo, no una foto del local**:

```
bocanariz          su tarjeta social, sobre fondo blanco
```

## Poner una foto propia

Es lo que conviene a la larga: no depende de nadie, no se cae y pesa lo que uno
quiera. Se deja el archivo en esta carpeta y se apunta `foto` a él:

```json
"foto": "fotos/comer/alleria.jpg"
```

El nombre del archivo es el `slug` del local. La lista completa:

```
alleria.jpg          golfo-di-napoli.jpg   rishtedar.jpg
baco.jpg             holy-moly.jpg         siam-thai.jpg
bar-de-rene.jpg      margo.jpg             sole-mio.jpg
bocanariz.jpg        ramen-kintaro.jpg     trattoria-da-noi.jpg
costa-bright.jpg     fuente-alemana.jpg
```

## Qué tamaño

La tarjeta del índice recorta en **cuadrado** y la ficha en **16:9**, las dos
con `object-fit: cover` y centradas. Conviene entonces:

- Lado corto de al menos **1000 px**.
- Que lo importante esté **al centro**: los bordes se recortan en el cuadrado.
- Y que se vea el local o el plato, no el logo: el nombre ya va escrito encima.
- JPG con calidad ~80. Sobre 300 KB por foto la página empieza a pesar: son
  catorce en la misma grilla.

Para dejar una foto lista desde el terminal, con ImageMagick:

```bash
magick original.jpg -auto-orient -resize 1400x1400^ -quality 80 web/fotos/comer/alleria.jpg
```

## Si el local cambia

Cambiar la foto es reemplazar el archivo con el mismo nombre. El `slug` no se
toca nunca una vez publicado: es lo que viaja en los links compartidos
(`comer.html#/l/alleria`).
