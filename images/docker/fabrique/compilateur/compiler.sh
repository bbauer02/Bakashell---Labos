#!/bin/sh
# Génère un script de traitement dans /work, puis l'exécute.
set -e
mkdir -p /work
printf '#!/bin/sh\necho "OK-$(hostname)"\n' > /work/traitement.sh
chmod +x /work/traitement.sh
echo "Script généré, exécution…"
/work/traitement.sh
