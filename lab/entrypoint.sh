#!/bin/bash
source /opt/linux-lab/utils.sh

# Always start fresh — reset progress on container start
echo '{"score":0,"total":0,"completed":[]}' > "$PROGRESS_FILE"

MODE="${1:-web}"

if [ "$MODE" = "web" ]; then
    # ─── Web Mode (KodeKloud-style) ───
    echo "🐧 Linux Lab - Mode Web"
    echo "   Interface disponible sur http://localhost:8080"
    exec python3 /opt/linux-lab/web/server.py

elif [ "$MODE" = "cli" ] || [ "$MODE" = "bash" ]; then
    # ─── CLI Mode (terminal only) ───
    print_banner
    echo -e "  Bienvenue dans le ${BOLD}Linux CLI Lab${NC} !"
    echo -e "  Un environnement interactif pour apprendre les commandes Linux."
    echo ""
    echo -e "  ${CYAN}Commandes utiles :${NC}"
    echo -e "    ${BOLD}check steps${NC}        → Voir toutes les étapes"
    echo -e "    ${BOLD}check step 1${NC}       → Voir les exercices de l'étape 1"
    echo -e "    ${BOLD}check 1${NC}            → Valider l'étape 1"
    echo -e "    ${BOLD}check status${NC}       → Voir votre score"
    echo -e "    ${BOLD}check help${NC}         → Aide complète"
    echo ""
    echo -e "  ${DIM}Commencez par : check step 1${NC}"
    echo ""
    print_score
    exec bash

else
    echo "Usage: entrypoint.sh [web|cli]"
    echo "  web  - Lance l'interface web (défaut)"
    echo "  cli  - Lance le mode terminal"
    exit 1
fi
