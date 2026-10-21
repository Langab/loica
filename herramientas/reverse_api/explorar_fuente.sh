#!/usr/bin/env bash
# Explora UNA fuente con reverse-api-engineer (modo agent, no interactivo) para
# descubrir la API interna que usa su página. Es una herramienta de
# EXPLORACIÓN, se usa una vez por fuente y a mano: la corrida diaria nunca la
# llama (la corrida no usa modelos de lenguaje). Ver LEEME.md al lado.
#
# Uso:
#   herramientas/reverse_api/explorar_fuente.sh <id_fuente> <url> "<prompt>"
#
# Variables opcionales:
#   RAE_TIMEOUT_SEG   tope de la corrida en segundos (por defecto 900 = 15 min)
#   RAE_MODELO        claude-sonnet-4-6 (defecto) | claude-opus-4-6 | claude-haiku-4-5
#   RAE_HEADLESS      1 (defecto) navegador sin ventana; 0 para mirarlo trabajar
#   LOICA_EXPLORACION carpeta de trabajo (por defecto ../exploracion_apis, FUERA
#                     del repo: los HAR graban cookies y cabeceras y no van a git)
#
# Deja en <exploracion>/<id_fuente>/:
#   resultado_AAAA-MM-DD_HHMM.json   el JSON de --json (run_id, har_path, script_path, usage)
#   log_AAAA-MM-DD_HHMM.txt          stderr de la herramienta
# y la herramienta deja el HAR y el cliente generado en ~/.reverse-api/runs/.

set -uo pipefail

if [ $# -lt 3 ]; then
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
  exit 2
fi

ID="$1"; URL="$2"; PEDIDO="$3"

RAIZ_REPO="$(cd "$(dirname "$0")/../.." && pwd)"
EXPLORACION="${LOICA_EXPLORACION:-$(dirname "$RAIZ_REPO")/exploracion_apis}"
TOPE="${RAE_TIMEOUT_SEG:-900}"
MODELO="${RAE_MODELO:-claude-sonnet-4-6}"
HEADLESS="${RAE_HEADLESS:-1}"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
if ! command -v reverse-api-engineer >/dev/null 2>&1; then
  echo "Falta reverse-api-engineer. Instalar: brew install uv && uv tool install 'reverse-api-engineer[manual]'" >&2
  exit 3
fi

# La exploración no puede caer dentro del repo: un HAR trae cookies.
case "$EXPLORACION/" in
  "$RAIZ_REPO"/*) echo "La carpeta de exploración no puede estar dentro del repo ($EXPLORACION)" >&2; exit 4 ;;
esac

DIR="$EXPLORACION/$ID"
mkdir -p "$DIR"
SELLO="$(date +%Y-%m-%d_%H%M)"
SALIDA="$DIR/resultado_$SELLO.json"
LOG="$DIR/log_$SELLO.txt"

# Las reglas del proyecto viajan dentro del prompt: el agente maneja un
# navegador de verdad y tiene que saber qué NO hacer.
REGLAS="Reglas obligatorias: solo lectura (navega y observa, no envíes formularios, no compres, no inicies sesión ni crees cuentas, no aceptes nada que pida datos personales); si aparece un captcha, un desafío anti-bot (Cloudflare u otro) o un 403, detente y repórtalo, no intentes evadirlo; respeta robots.txt del sitio y de cualquier dominio de API que descubras; no uses cabeceras falsas para hacerte pasar por otro cliente. El objetivo es encontrar un endpoint JSON público y estable (sin token de sesión) que entregue la agenda de eventos con título, fecha, hora, lugar y link a la ficha, y documentar su URL, parámetros de paginación/filtro y estructura de respuesta. El cliente Python generado debe usar solo requests, con un User-Agent identificado y pausas entre peticiones."

ARGS=(agent --json --no-interactive -m "$MODELO" -u "$URL" -p "$PEDIDO

$REGLAS")
[ "$HEADLESS" = "1" ] && ARGS+=(--headless)

echo "[$ID] explorando $URL (tope ${TOPE}s, modelo $MODELO) -> $DIR" >&2

cd "$DIR" || exit 5
set -m   # el comando queda en su propio grupo de procesos: así el tope mata también al navegador
reverse-api-engineer "${ARGS[@]}" >"$SALIDA" 2>"$LOG" &
PID=$!
set +m

TRANSCURRIDO=0
while kill -0 "$PID" 2>/dev/null; do
  if [ "$TRANSCURRIDO" -ge "$TOPE" ]; then
    echo "[$ID] tope de ${TOPE}s alcanzado: se corta la corrida" >&2
    kill -TERM -- "-$PID" 2>/dev/null; sleep 5; kill -KILL -- "-$PID" 2>/dev/null
    printf '{"schema_version":1,"status":"error","error":"timeout de %ss (corte de explorar_fuente.sh)","error_kind":"interrupted"}\n' "$TOPE" >"$SALIDA.timeout"
    break
  fi
  sleep 5; TRANSCURRIDO=$((TRANSCURRIDO + 5))
done
wait "$PID" 2>/dev/null; CODIGO=$?

echo "[$ID] terminó con código $CODIGO en ~${TRANSCURRIDO}s. Resultado: $SALIDA" >&2
if command -v python3 >/dev/null 2>&1 && [ -s "$SALIDA" ]; then
  python3 - "$SALIDA" <<'PY' >&2
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception as e:
    print("  (el resultado no es JSON:", e, ")"); sys.exit()
u = d.get("usage") or {}
print("  estado:", d.get("status"), "| run_id:", d.get("run_id"))
print("  script:", d.get("script_path"))
print("  har:   ", d.get("har_path"))
print("  tokens: in=%s out=%s cache_r=%s cache_w=%s costo_usd=%s" % (
    u.get("input_tokens"), u.get("output_tokens"), u.get("cache_read_tokens"),
    u.get("cache_write_tokens"), u.get("total_cost_usd")))
if d.get("error"):
    print("  error:", d.get("error_kind"), d.get("error"))
PY
fi
exit "$CODIGO"
