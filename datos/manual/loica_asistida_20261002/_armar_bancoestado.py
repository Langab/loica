"""Arma descuentos_bancoestado.csv de la pasada del 02-10-2026.

Base: el script del 01-10 (sesión de la corrida mensual). Cambia lo que cambió la
página: BancoEstado publicó el lote de octubre ("Válido desde 01 de octubre"), con
fichas nuevas en Parque Arauco, varias en la RM y una tanda de descuentos SOLO
ONLINE ("Online Todos los días", tope $14.000) que no tienen local: esas entran sin
dirección ni comuna y con "Compra online" en las condiciones.
Datos crudos: bancoestado_20261002.jsonl, las 61 fichas de la RM (región con
"Metropolitana" o "En Parque Arauco"), verificadas por SHA-256 contra la pestaña.
Las cadenas (Tarragona, Burger King, Juan Maestro, Barrio Chick'en, Doggis,
Domino's, PedidosYa, Papa John's) siguen enlazadas desde la página hoy: se
conservan sus filas del 01-10.
"""
import csv, json, re, sys
from pathlib import Path

URL = ("https://www.bancoestado.cl/content/bancoestado-public/cl/es/home/home/"
       "todosuma---bancoestado-personas/un-mes-de-sabores---bancoestado-personas.html")
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
ORDEN = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
TODOS = ";".join(ORDEN)
RM = {"Santiago", "Providencia", "Las Condes", "Vitacura", "Lo Barnechea", "Ñuñoa", "La Reina",
      "La Florida", "Recoleta", "Huechuraba", "Cerrillos", "Independencia", "Puente Alto",
      "San Bernardo", "Maipú", "Estación Central", "San Miguel", "La Cisterna", "Peñalolén",
      "Talagante", "Melipilla", "Pirque", "Colina"}
ALIAS = {"Nuñoa": "Ñuñoa", "Peñalolen": "Peñalolén", "Santiago Centro": "Santiago",
         "Comuna de Peñalolén": "Peñalolén"}
SIN_COMUNA_RM = {"Av. Américo Vespucio local 1108 B, Mall Paseo Quilín", "Av. Manuel Montt 2559"}
FIJOS = {"Av. Kennedy 5413, Mall Parque Arauco": ("Av. Kennedy 5413, Mall Parque Arauco", "Las Condes"),
         "Constitución 241, Terrazas San Cristobal, Providencia.": ("Constitución 241, Terrazas San Cristóbal", "Providencia")}
DIAS_LOCAL = {"Mall Parque Arauco, Las Condes (Lunes a Miércoles)": ("Mall Parque Arauco", "Las Condes", "lunes;martes;miercoles"),
              "Mallplaza Vespucio, La Florida (Todos los días.)": ("Mallplaza Vespucio", "La Florida", TODOS)}
ONLINE = re.compile(r"^Regi[oó]n Metropolitana\.?$")


def plano(t):
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        t = t.replace(a, b)
    return t.lower()


def dias(etiqueta):
    t = plano(etiqueta.split(" - ")[0]).replace("online", "").strip()
    if "todos los dias" in t:
        return TODOS
    m = re.fullmatch(r"(\w+) a (\w+)", t)
    canon = lambda w: w if w in ORDEN else (w[:-1] if w.endswith("s") and w[:-1] in ORDEN else None)
    if m and canon(m.group(1)) and canon(m.group(2)):   # "lunes" termina en s y NO es plural
        i, j = ORDEN.index(canon(m.group(1))), ORDEN.index(canon(m.group(2)))
        rango = ORDEN[i:j + 1] if i <= j else ORDEN[i:] + ORDEN[:j + 1]   # "domingo a miércoles" da la vuelta
        return ";".join(d for d in ORDEN if d in rango)
    return ";".join(d for d in ORDEN if re.search(rf"\b{d}s?\b", t))


def vigencia(txt):
    f = re.findall(r"(\d{1,2}) de (\w+)(?: de)? ?(\d{4})?", txt.lower())
    if not f:
        return ""
    d, m, a = f[-1]
    return f"{int(a or 2026):04d}-{MESES[m]:02d}-{int(d):02d}"


def partir(local):
    limpio = local.strip().rstrip(".")
    if local in FIJOS:
        return FIJOS[local]
    if local in SIN_COMUNA_RM:
        return limpio, ""
    if "," in limpio:
        cabeza, cola = limpio.rsplit(",", 1)
        cola = ALIAS.get(cola.strip(), cola.strip())
        if cola in RM:
            return cabeza.strip(), cola
    return None


crudo, ayer, salida = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
filas, fuera = [], []
for linea in crudo.read_text(encoding="utf-8").splitlines():
    modal, tarjeta, imagen, ficha, links = json.loads(linea)
    region, dias_txt, monto, nombre = tarjeta
    medio = ficha[0]
    vig = vigencia(ficha[1])
    locales = ficha[ficha.index("Locales disponibles:") + 1:]
    tope = re.search(r"Tope \$([\d.]+)", medio)
    online = dias_txt.lower().startswith("online")
    base = {"banco": "BancoEstado", "comercio": nombre, "lat": "", "lon": "", "logo": imagen,
            "monto": monto, "tope": tope.group(1).replace(".", "") if tope else "", "vigencia": vig,
            "sitio_web": links[0] if links else "", "categoria": "", "url": URL,
            "tarjeta": "Tarjeta de Crédito Visa BancoEstado"}
    if online:
        if any(ONLINE.match(l.strip()) for l in locales):
            filas.append({**base, "direccion": "", "comuna": "", "dias": dias(dias_txt),
                          "condiciones": f"Compra online (despacho en la Región Metropolitana). {medio} {ficha[1]}"})
        else:
            fuera.append((nombre, "online fuera de la RM"))
        continue
    for local in locales:
        if local in DIAS_LOCAL:
            direccion, comuna, dias_local = DIAS_LOCAL[local]
        else:
            partes = partir(local)
            if partes is None:
                fuera.append((nombre, local))
                continue
            (direccion, comuna), dias_local = partes, dias(dias_txt)
        filas.append({**base, "direccion": direccion, "comuna": comuna, "dias": dias_local,
                      "condiciones": f"{medio} {ficha[1]}"})

CADENAS = {"Tarragona", "Burger King", "Juan Maestro", "Barrio Chick'en", "Doggis", "Domino's Pizza", "PedidosYa", "Papa John's"}
for f in csv.DictReader(open(ayer, encoding="utf-8")):
    if f["comercio"] in CADENAS:
        filas.append(f)

campos = ["banco", "comercio", "direccion", "comuna", "lat", "lon", "logo", "dias", "monto", "tope", "vigencia",
          "sitio_web", "categoria", "url", "tarjeta", "condiciones"]
with salida.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=campos)
    w.writeheader()
    w.writerows({k: f.get(k, "") for k in campos} for f in filas)
print(len(filas), "filas de", len({r['comercio'] for r in filas}), "comercios;", len(fuera), "locales fuera de la RM")
sin_dia = [r["comercio"] for r in filas if not r["dias"] and r["comercio"] != "PedidosYa"]
print("sin día:", sin_dia)
for n, l in fuera:
    if "Región" not in l:
        print("  fuera:", n, "|", l)
