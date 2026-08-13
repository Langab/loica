#!/bin/bash
# Programa la corrida diaria del pipeline con launchd (el "cron" de macOS).
#
# Uso:
#   bash scripts/instalar_agenda.sh          # instalar / actualizar
#   bash scripts/instalar_agenda.sh --quitar # desinstalar
#
# La corrida queda a las 11:00. Qué necesita el Mac para que funcione:
#
#   - PRENDIDO (o durmiendo): si está durmiendo a las 11:00, launchd corre la
#     corrida apenas despierte — el día no se pierde, solo se corre más tarde.
#   - APAGADO no corre nada: launchd no existe con el equipo apagado, y esa
#     corrida no se recupera al encenderlo al día siguiente (la de ese día sí).
#   - Sesión iniciada del usuario (es un LaunchAgent de usuario, no un demonio).
#   - Red, y credenciales de git que no pidan clave (el push es desatendido).
#
# Para que despierte solo antes de la corrida (opcional, pide contraseña):
#   sudo pmset repeat wakeorpoweron MTWRFSU 10:55:00

set -euo pipefail

ETIQUETA="cl.loica.pipeline"
PLIST="$HOME/Library/LaunchAgents/${ETIQUETA}.plist"
PROYECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$(command -v python3)"
HORA=${HORA:-11}
MINUTO=${MINUTO:-0}

if [[ "${1:-}" == "--quitar" ]]; then
    launchctl bootout "gui/$(id -u)/${ETIQUETA}" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Agenda diaria desinstalada."
    exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents" "$PROYECTO/datos/logs"

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${ETIQUETA}</string>

    <!-- run_todo.py, no run_diario.py: encadena extraer + exportar + publicar.
         Programar solo run_diario dejaba la base al día y el sitio viejo. -->
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>${PROYECTO}/run_todo.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${PROYECTO}</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>${HORA}</integer>
        <key>Minute</key><integer>${MINUTO}</integer>
    </dict>

    <!-- Si el Mac estaba durmiendo a la hora fijada, corre al despertar -->
    <key>RunAtLoad</key>
    <false/>

    <key>StandardOutPath</key>
    <string>${PROYECTO}/datos/logs/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>${PROYECTO}/datos/logs/launchd.err.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>TICKETMASTER_API_KEY</key>
        <string>${TICKETMASTER_API_KEY:-}</string>
    </dict>
</dict>
</plist>
PLIST_EOF

launchctl bootout "gui/$(id -u)/${ETIQUETA}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Listo: el pipeline correrá todos los días a las ${HORA}:$(printf '%02d' "$MINUTO")."
echo
echo "Comandos útiles:"
echo "  launchctl list | grep ${ETIQUETA}          # ver si está cargado"
echo "  launchctl kickstart gui/$(id -u)/${ETIQUETA}  # correr ahora mismo"
echo "  bash scripts/instalar_agenda.sh --quitar   # desinstalar"
echo
echo "Los informes quedan en: ${PROYECTO}/informes/"
