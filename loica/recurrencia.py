"""Cadencia semanal: talleres municipales que se repiten, no eventos únicos.

Los municipios casi no publican eventos con fecha. Publican talleres que
ocurren "lunes, miércoles y viernes de 19:00 a 20:30, desde marzo". Este
módulo traduce esa forma de escribir a lo que el modelo sí entiende: la
primera sesión, la última, y una frase legible con la cadencia.

LIMITACIÓN CONOCIDA: `Evento` todavía no tiene un campo de recurrencia. Mientras
no exista, un taller semanal se guarda como UN evento con rango de fechas y la
cadencia escrita en la descripción. Eso alcanza para el mapa y para el filtro
"gratis", pero NO para "¿qué hay este sábado?": un taller de todos los sábados
aparece como un evento largo, no como algo que ocurre este fin de semana.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timedelta

# lunes = 0, como date.weekday()
DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4,
    "sabado": 5, "domingo": 6,
}

# Abreviaturas que usan los municipios en los títulos ("Academia Preferente
# Lu-Mi-Vi"). Solo las inequívocas: "M" sola es martes o miércoles según la
# comuna, así que no se adivina.
ABREVIATURAS = {
    "lu": 0, "lun": 0, "ma": 1, "mar": 1, "mi": 2, "mie": 2, "ju": 3, "jue": 3,
    "vi": 4, "vie": 4, "sa": 5, "sab": 5, "do": 6, "dom": 6,
}

NOMBRES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _plano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").lower()


def parsear_dias(*textos: str) -> list[int]:
    """Devuelve los días de la semana (0=lunes) mencionados en los textos.

    Acepta "Lunes, Miércoles y Viernes", ["lunes","miércoles"], "Lu-Mi-Vi".
    Devuelve lista ordenada y sin repetidos. Si no reconoce nada, lista vacía:
    sin días no hay taller, y es preferible descartarlo a inventarle un horario.
    """
    encontrados: set[int] = set()
    for texto in textos:
        if not texto:
            continue
        plano = _plano(str(texto))

        for nombre, indice in DIAS_SEMANA.items():
            if re.search(rf"(?<![a-z]){nombre}(?![a-z])", plano):
                encontrados.add(indice)

        # Abreviaturas solo si el texto no traía ningún nombre completo: así
        # "Sábado" no se lee además como "sa" en otra parte de la frase.
        if not encontrados:
            for abrev, indice in ABREVIATURAS.items():
                if re.search(rf"(?<![a-z]){abrev}(?![a-z])", plano):
                    encontrados.add(indice)

    return sorted(encontrados)


def parsear_hora(texto: str) -> time | None:
    """"19:00", "19.00 hrs", "9:30 a 11:00" → la hora de inicio."""
    if not texto:
        return None
    m = re.search(r"\b([01]?\d|2[0-3])[:.h](\d{2})\b", str(texto))
    if not m:
        return None
    try:
        return time(int(m.group(1)), int(m.group(2)))
    except ValueError:
        return None


def ocurrencias(dias: list[int], desde: date, hasta: date,
                tope: int = 400) -> list[date]:
    """Todas las fechas entre `desde` y `hasta` que caen en esos días."""
    if not dias or hasta < desde:
        return []

    fechas: list[date] = []
    actual = desde
    while actual <= hasta and len(fechas) < tope:
        if actual.weekday() in dias:
            fechas.append(actual)
        actual += timedelta(days=1)
    return fechas


def rango_de_sesiones(dias: list[int], desde: date, hasta: date,
                      hora: time | None = None) -> tuple[datetime, datetime] | None:
    """Primera y última sesión reales de un taller.

    No es lo mismo que el rango que publica el municipio: si el ciclo va del 1
    al 31 de agosto y el taller es solo los sábados, la primera sesión es el
    primer sábado, no el día 1.
    """
    fechas = ocurrencias(dias, desde, hasta)
    if not fechas:
        return None

    momento = hora or time(0, 0)
    return (datetime.combine(fechas[0], momento),
            datetime.combine(fechas[-1], momento))


def sesiones_futuras(dias: list[int], hora: time | None = None,
                     desde: date | None = None, hasta: date | None = None,
                     horizonte_dias: int = 30,
                     hoy: date | None = None) -> list[datetime]:
    """Las próximas sesiones de un taller, una por fecha.

    Se emite una ocurrencia por sesión y no un solo evento con rango largo,
    porque `colapsar_multidia` después hace lo correcto con cada caso:

    - Un taller de lunes, miércoles y viernes tiene huecos de 1 a 3 días, así
      que se fusiona en una sola tarjeta con rango y la cadencia en el texto.
    - Un taller de solo los sábados tiene huecos de 7 días, sobre el máximo
      tolerado, así que sobrevive como sesiones sueltas. Es lo que hace que
      aparezca en "este fin de semana", que es justamente donde se lo busca.

    Los programas municipales suelen partir en marzo y seguir todo el año: la
    fecha que interesa no es cuándo empezó el programa sino cuándo es la
    próxima sesión, por eso la ventana arranca hoy.
    """
    hoy = hoy or date.today()
    inicio_ventana = max(desde, hoy) if desde else hoy
    fin_ventana = hoy + timedelta(days=horizonte_dias)
    if hasta:
        fin_ventana = min(fin_ventana, hasta)

    momento = hora or time(0, 0)
    return [datetime.combine(f, momento)
            for f in ocurrencias(dias, inicio_ventana, fin_ventana)]


def frase_cadencia(dias: list[int], hora_inicio: str | time | None = None,
                   hora_fin: str | time | None = None) -> str:
    """"Todos los lunes, miércoles y viernes de 19:00 a 20:30".

    Va a la descripción del evento: es el dato que le dice al usuario que esto
    se repite, mientras el modelo no tenga un campo propio para la recurrencia.
    """
    if not dias:
        return ""

    nombres = [NOMBRES[d] for d in dias]
    if len(nombres) == 1:
        cuando = f"todos los {nombres[0]}"
    else:
        cuando = "todos los " + ", ".join(nombres[:-1]) + f" y {nombres[-1]}"

    def _texto_hora(valor) -> str:
        if isinstance(valor, time):
            return valor.strftime("%H:%M")
        hora = parsear_hora(str(valor or ""))
        return hora.strftime("%H:%M") if hora else ""

    inicio, fin = _texto_hora(hora_inicio), _texto_hora(hora_fin)
    if inicio and fin:
        return f"{cuando} de {inicio} a {fin}"
    if inicio:
        return f"{cuando} a las {inicio}"
    return cuando
