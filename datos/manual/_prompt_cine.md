# Prompt de cartelera de cine — reemplazado el 02-09-2026

Desde el 02-09-2026 el prompt único de la extracción asistida es `_prompt_asistido.md` (v7).
Lo que pedía este archivo es ahora la sección **"CSV 2 — Cartelera de cine"** de ese prompt:
mismo encabezado de 14 columnas, un archivo por cadena, las 20 salas de Cinépolis con sus
slugs y sus cuatro trampas, Cineplanet por sus tres JSON desde una pestaña parada en
cineplanet.cl, y MUVIX / Cine UC a ojo. No copies este archivo.

Los tres `cartelera_*.csv` van dentro de la carpeta con fecha de la pasada,
`datos/manual/loica_asistida_AAAAMMDD/` (ocho dígitos, sin guiones), y se suben con git;
la corrida en la nube arranca sola al ver la carpeta nueva y publica en ~2 horas:

```bash
git add datos/manual/loica_asistida_$(date +%Y%m%d)/
git commit -m "Cartelera de cine al $(date +%F)"
git push
```

Manda la carpeta más nueva y lo que ella no trae se pierde: una pasada solo de cine copia
adentro `asistida.csv`, los `descuentos_*.csv` y las carteleras que no regeneró desde la
anterior. Si se quiere programar: `_tarea_programada_cine.md`.
