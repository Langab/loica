# Vigilancia de Instagram — el circuito que no vende por ticketera

Buena parte de la vida nocturna, las ferias de barrio y el stand up de entrada
liberada **no pasan por ninguna ticketera**: se anuncian solo en Instagram, con
un afiche y una fecha en el pie de foto. Passline y PortalDisc ya cubren lo que
se vende con entrada online (43 fiestas hoy), así que acá va lo que queda fuera:
puerta, entrada liberada, o promoción pura.

## El flujo

Instagram no se puede rastrear con Python (la API no lee cuentas ajenas y el
scraping viola sus términos y arriesga tu cuenta). Pero SÍ se puede mirar con
un navegador normal, que es lo que hace cualquiera. El flujo es:

1. Abrís la cuenta en tu Chrome con la extensión de Claude.
2. La extensión saca los posts recientes: **texto del pie, permalink y la
   imagen del afiche**.
3. Me pasás ese texto crudo (o lo guardás como está).
4. Yo interpreto el afiche desordenado —"🔥ESTE VIERNES DIRTY PERREO @ Coco,
   Bellavista, 23hrs, +18, link en bio"— y lo dejo estructurado en
   `datos/manual/instagram.yaml`, con fecha, lugar, comuna y precio.
5. La corrida diaria lo levanta como cualquier otra fuente.

Ese paso 4 es exactamente el trabajo de criterio que un scraper no puede hacer:
un pie de foto no es un campo de fecha, es prosa con emojis.

## La regla de siempre

Cada evento necesita `fuente_url` = el **permalink del post de Instagram**. Sin
link no se guarda: es lo que mantiene a Loica como índice que deriva tráfico a
la cuenta original, no como copia. La imagen se enlaza, nunca se descarga.

## Lista de cuentas a vigilar

Curada con lo confirmado esta sesión. El resto se agrega a medida que aparecen.

### Vida nocturna / fiestas
| Cuenta | Local | Comuna | Nota |
|---|---|---|---|
| @limonstgo | Limón | Recoleta | Dardignac 142. Entrada liberada, no vende por ticketera |
| (Dirty Perreo) | itinerante (Coco, etc.) | Varía | OJO: parte ya entra por Passline; revisar duplicados |

### Stand up / comedia
| Cuenta | Local | Comuna | Nota |
|---|---|---|---|
| @comedybarrioitalia | Comedy Restobar | Providencia | Barrio Italia. El sitio comedy.cl da 403 |
| (Bar Palermo) | Palermo | Providencia | Barrio Italia. Parte entra por PortalDisc (teatropalermo es otro, Puente Alto) |

### Ferias de diseño / emprendedores
| Cuenta | Qué | Nota |
|---|---|---|
| (productores de feria) | Drugstore, plazas | Las ferias las publica el productor, no el lugar. Buscar por hashtag de la feria puntual |

## Cómo entra al pipeline

Se escribe en `datos/manual/instagram.yaml` con el mismo formato que
`_plantilla.yaml`, poniendo `fuente_nombre: Instagram` y el permalink como
`fuente_url`. El nombre del archivo no importa para la atribución; el
`fuente_nombre` sí.
