# Registro de extracciones asistidas — archivo cerrado

> **Desde el 01-09-2026 este registro ya no se alimenta.** Cada pasada llega
> como una carpeta con fecha dentro de `datos/manual/`
> (`loica_asistida_20260901/`) que trae su CSV, su cartelera, sus descuentos y
> su `RESUMEN_*.md`, y que **queda ahí**: la pasada anterior no se pisa, así
> que la entrada al pipeline y el archivo histórico son la misma carpeta.
> Comparar dos pasadas es un `diff` entre dos carpetas.
>
> Lo que hay acá abajo son las pasadas del formato viejo, cuando
> `datos/manual/asistida.csv` se reemplazaba en cada sesión y había que sacarle
> una copia para no perderla. Se dejan como están.

Cada pasada con el navegador dejaba acá su CSV y su resumen, con fecha y hora,
**tal como llegaron**.

Existía por tres razones concretas:

1. **Para poder comparar pasadas.** El 25-08-2026 una extracción trajo 279 eventos de
   Passline y otra 632; sin los dos archivos guardados no había forma de saber si el
   catálogo había cambiado o si la sesión había quedado corta. Con ellos se vio en un
   minuto que faltó apretar "ver más eventos".
2. **Porque el CSV de trabajo se reemplazaba entero.** `datos/manual/asistida.csv` se
   pisaba en cada pasada; sin este registro, la anterior solo existía en el historial de
   git y había que ir a buscarla a mano. Esta es la razón que la carpeta con fecha
   resolvió, y por la que el registro ya no hace falta.
3. **Porque los resúmenes traen hallazgos que no caben en el CSV.** El del 25-08
   documenta la API pública de Passline y la REST abierta del CEP: dos fuentes que
   pueden dejar de ser manuales. Eso vale más que los eventos de esa semana. Ese papel
   lo cumple ahora el `RESUMEN_*.md` que viaja dentro de cada carpeta.

## Cómo se nombraban

    AAAA-MM-DD_HHMM_asistida.csv     el CSV de eventos tal como llegó
    AAAA-MM-DD_HHMM_resumen.md       el resumen de la sesión
    AAAA-MM-DD_HHMM_cartelera.csv    si esa pasada trajo cine
