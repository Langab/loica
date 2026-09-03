# Prompt semanal de Passline — reemplazado el 02-09-2026

Desde el 02-09-2026 el prompt único de la extracción asistida es `_prompt_asistido.md` (v7).
Lo que pedía este archivo —solo Passline, con un CSV de 10 columnas— es ahora el **Bloque 1
del CSV 1** de ese prompt: mismas reglas duras, encabezado de 13 columnas y la mecánica
probada (`<buttom>`, concurrencia 3, JSON-LD por ficha). No copies este archivo.

El CSV va como `asistida.csv` dentro de la carpeta con fecha de la pasada,
`datos/manual/loica_asistida_AAAAMMDD/` (ocho dígitos, sin guiones), y se sube con git;
la corrida en la nube arranca sola al ver la carpeta nueva y publica en ~2 horas:

```bash
git add datos/manual/loica_asistida_$(date +%Y%m%d)/
git commit -m "Passline al $(date +%F)"
git push
```

Manda la carpeta más nueva y lo que ella no trae se pierde: si la pasada es solo Passline,
copiá adentro los CSV de la anterior que no regeneraste (carteleras y descuentos).
