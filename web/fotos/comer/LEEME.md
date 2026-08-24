# Fotos de "Dónde comer"

Cada local tiene **dos** campos de foto en `web/comer.json`:

- `foto` — la del cuadrado del índice, y la que va arriba de la ficha en 16:9.
  Es la fachada o la foto que identifica al local.
- `otra_foto` — la segunda, un plato o el local por dentro. Sale **solo dentro
  de la ficha**, en 4:3, entre el último párrafo y el pero. En el índice no
  aparece: catorce cuadrados ya bastan para elegir, y la gracia de entrar a la
  ficha es ver algo que afuera no estaba.

Las dos pueden ir vacías. Vacía o rota, `onerror` la saca: arriba queda el
Quiltro sobre el pastel oliva —que es un estado válido de la tarjeta y no un
hueco roto— y la segunda simplemente no se dibuja.

## De dónde salen

Son **URL al servidor del propio local**: su sitio, la plataforma donde publica
su carta o su ficha de delivery. Es la misma regla del resto del sitio —las
fotos de los eventos se enlazan a las del organizador, **nunca se copian**— y
por eso ninguna de estas fotos vive en esta carpeta.

Eso tiene dos consecuencias conocidas:

1. Si el local cambia de sitio, la foto muere y queda el Quiltro.
2. Algunos servidores bloquean la lectura desde otro dominio (hotlink
   protection). `barriolastarria.cl`, por ejemplo, devuelve 404 si el pedido
   viene desde fuera, así que sus fotos no sirven acá aunque se vean bien en
   el navegador.

Dónde estaba la foto de cada uno, para cuando haya que renovarlas:

| local | de dónde |
| --- | --- |
| alleria | su ficha en PedidosYa (`pedidosya.dhmedia.io`), que es donde publica sus fotos: no tiene sitio propio |
| baco | `er-s3-prod` — la galería de su carta digital; su sitio propio es solo una portada |
| bar-de-rene | su WordPress, `wp-json/wp/v2/media` |
| bocanariz | su WordPress, `wp-json/wp/v2/media` (pide User-Agent de navegador o responde 406) |
| costa-bright | **no tiene** — ver abajo |
| fuente-alemana | su sitio |
| golfo-di-napoli | su WordPress; solo publica platos, no tiene foto de la fachada |
| holy-moly | `tofuu.getjusto.com`, su tienda getjusto (`holymoly.cl/pedir`) |
| margo | su sitio, hecho en Odoo (`/web/image/<id>-<hash>/<nombre>`) |
| ramen-kintaro | `tofuu.getjusto.com`, vía `kintaro.cl` |
| rishtedar | su sitio, `/images/locales/` |
| siam-thai | Wix (`static.wixstatic.com`); acepta medidas en la URL: `/v1/fill/w_1200,h_1200,al_c,q_80/` |
| sole-mio | su WordPress |
| trattoria-da-noi | su WordPress, `danoi.cl` |

Truco que sirvió en casi todos: si el local tiene WordPress,
`https://SITIO/wp-json/wp/v2/media?per_page=100&media_type=image` devuelve la
biblioteca entera con medidas, y ahí está lo que la portada no muestra.

## Cuál falta

```
costa-bright       Instagram: @costa_bright — no tiene sitio, ni carta digital,
                   ni ficha de delivery. No hay nada que enlazar.
```

Mientras tanto su tarjeta muestra al Quiltro, que es un estado válido.

## Poner una foto propia

Es lo que conviene a la larga: no depende de nadie, no se cae y pesa lo que uno
quiera. Se deja el archivo en esta carpeta y se apunta `foto` (o `otra_foto`) a
él:

```json
"foto": "fotos/comer/costa-bright.jpg",
"otra_foto": "fotos/comer/costa-bright-dentro.jpg"
```

El nombre del archivo es el `slug` del local. La lista completa:

```
alleria.jpg          golfo-di-napoli.jpg   rishtedar.jpg
baco.jpg             holy-moly.jpg         siam-thai.jpg
bar-de-rene.jpg      margo.jpg             sole-mio.jpg
bocanariz.jpg        ramen-kintaro.jpg     trattoria-da-noi.jpg
costa-bright.jpg     fuente-alemana.jpg
```

Ojo con una cosa: una foto ajena bajada de otro sitio y subida acá deja de ser
un enlace y pasa a ser una copia publicada en loicasantiago.cl. Para eso hay
que tenerla propia o pedirla.

## Qué tamaño

La tarjeta del índice recorta en **cuadrado**, la foto de arriba de la ficha en
**16:9** y la segunda en **4:3**, las tres con `object-fit: cover` y centradas.
Conviene entonces:

- Lado corto de al menos **1000 px**.
- Que lo importante esté **al centro**: los bordes se recortan en el cuadrado.
- Y que se vea el local o el plato, no el logo: el nombre ya va escrito encima.
- JPG con calidad ~80. Sobre 300 KB la foto empieza a pesar **si es la del
  índice**: son catorce en la misma grilla. La segunda carga de a una dentro de
  la ficha, así que ahí el techo es más suelto.

Para dejar una foto lista desde el terminal, con ImageMagick:

```bash
magick original.jpg -auto-orient -resize 1400x1400^ -quality 80 web/fotos/comer/costa-bright.jpg
```

## Si el local cambia

Cambiar la foto es reemplazar el archivo con el mismo nombre. El `slug` no se
toca nunca una vez publicado: es lo que viaja en los links compartidos
(`comer.html#/l/alleria`).
