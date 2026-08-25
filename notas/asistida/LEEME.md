# Registro de extracciones asistidas

Cada pasada con el navegador deja acá su CSV y su resumen, con fecha y hora, **tal
como llegaron**. Es un archivo histórico, no una entrada al pipeline: lo que el
pipeline lee vive en `datos/manual/`.

Existe por tres razones concretas:

1. **Para poder comparar pasadas.** El 25-08-2026 una extracción trajo 279 eventos de
   Passline y otra 632; sin los dos archivos guardados no había forma de saber si el
   catálogo había cambiado o si la sesión había quedado corta. Con ellos se vio en un
   minuto que faltó apretar "ver más eventos".
2. **Porque el CSV de trabajo se reemplaza entero.** `datos/manual/asistida.csv` se
   pisa en cada pasada; sin este registro, la anterior solo existe en el historial de
   git y hay que ir a buscarla a mano.
3. **Porque los resúmenes traen hallazgos que no caben en el CSV.** El del 25-08
   documenta la API pública de Passline y la REST abierta del CEP: dos fuentes que
   pueden dejar de ser manuales. Eso vale más que los eventos de esa semana.

## Cómo se nombran

    AAAA-MM-DD_HHMM_asistida.csv     el CSV de eventos tal como llegó
    AAAA-MM-DD_HHMM_resumen.md       el resumen de la sesión
    AAAA-MM-DD_HHMM_cartelera.csv    si esa pasada trajo cine
