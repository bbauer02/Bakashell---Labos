#!/bin/bash
# === Linux Lab - Main Validation Engine ===

source /opt/linux-lab/utils.sh

EXERCISES_DIR="/opt/linux-lab/exercises"

show_help() {
    echo ""
    echo -e "${BOLD}Commandes disponibles :${NC}"
    echo ""
    echo -e "  ${CYAN}check status${NC}         Voir votre score et progression"
    echo -e "  ${CYAN}check step <N>${NC}       Voir les exercices de l'étape N"
    echo -e "  ${CYAN}check validate <N>${NC}   Valider les exercices de l'étape N"
    echo -e "  ${CYAN}check steps${NC}          Lister toutes les étapes"
    echo -e "  ${CYAN}check reset${NC}          Remettre le score à zéro"
    echo -e "  ${CYAN}check help${NC}           Afficher cette aide"
    echo ""
    echo -e "  ${DIM}Raccourci : 'check <N>' équivaut à 'check validate <N>'${NC}"
    echo ""
}

show_steps() {
    echo ""
    echo -e "${BOLD}Étapes du tutoriel :${NC}"
    echo ""
    echo -e "  ${CYAN}1${NC}  - Premiers pas : navigation dans le système"
    echo -e "  ${CYAN}2${NC}  - Le manuel et les chemins"
    echo -e "  ${CYAN}3${NC}  - Créer, écrire, gérer fichiers et dossiers"
    echo -e "  ${CYAN}4${NC}  - Utilisateurs, groupes et permissions"
    echo -e "  ${CYAN}5${NC}  - Super-utilisateur et processus"
    echo -e "  ${CYAN}6${NC}  - Exercice pratique : système familial"
    echo -e "  ${CYAN}7${NC}  - Installer des programmes"
    echo -e "  ${CYAN}8${NC}  - Montage et systèmes de fichiers"
    echo -e "  ${CYAN}9${NC}  - Recherche de fichiers et de contenu"
    echo -e "  ${CYAN}10${NC} - Redirections et pipes"
    echo -e "  ${CYAN}11${NC} - Édition de texte en terminal"
    echo -e "  ${CYAN}12${NC} - Variables d'environnement et shell"
    echo -e "  ${CYAN}13${NC} - Réseau de base"
    echo -e "  ${CYAN}14${NC} - Archivage et compression"
    echo -e "  ${CYAN}15${NC} - Filtrage et traitement de texte"
    echo -e "  ${CYAN}16${NC} - Introduction au scripting Bash"
    echo -e "  ${CYAN}17${NC} - Tâches planifiées (cron)"
    echo -e "  ${CYAN}18${NC} - Surveillance du système"
    echo -e "  ${CYAN}19${NC} - Intégration finale : serveur web"
    echo -e "  ${CYAN}20${NC} - Liens symboliques et liens durs"
    echo -e "  ${CYAN}21${NC} - Expressions régulières"
    echo -e "  ${CYAN}22${NC} - SSH et accès distant"
    echo -e "  ${CYAN}23${NC} - Gestion des logs"
    echo -e "  ${CYAN}24${NC} - Sécurité de base"
    echo ""

    # Show completion status per step
    for i in $(seq 1 24); do
        local count=0
        local total=0
        if [ -f "${EXERCISES_DIR}/step${i}.sh" ]; then
            source "${EXERCISES_DIR}/step${i}.sh"
            total=$(get_step_total 2>/dev/null || echo 0)
            for ex_id in $(get_step_exercise_ids 2>/dev/null); do
                if is_completed "$ex_id"; then
                    count=$((count + 1))
                fi
            done
            if [ "$total" -gt 0 ]; then
                if [ "$count" -eq "$total" ]; then
                    echo -e "     ${GREEN}✅ Étape ${i} : ${count}/${total} exercices${NC}"
                elif [ "$count" -gt 0 ]; then
                    echo -e "     ${YELLOW}🔶 Étape ${i} : ${count}/${total} exercices${NC}"
                else
                    echo -e "     ${DIM}⬜ Étape ${i} : ${count}/${total} exercices${NC}"
                fi
            fi
        fi
    done
    echo ""
}

show_step() {
    local step=$1
    if [ ! -f "${EXERCISES_DIR}/step${step}.sh" ]; then
        echo -e "${RED}Étape ${step} non trouvée. Utilisez 'check steps' pour voir les étapes disponibles.${NC}"
        return 1
    fi
    source "${EXERCISES_DIR}/step${step}.sh"
    show_step_exercises
}

validate_step() {
    local step=$1
    if [ ! -f "${EXERCISES_DIR}/step${step}.sh" ]; then
        echo -e "${RED}Étape ${step} non trouvée. Utilisez 'check steps' pour voir les étapes disponibles.${NC}"
        return 1
    fi
    source "${EXERCISES_DIR}/step${step}.sh"
    run_validations
    print_score
}

reset_progress() {
    echo '{"score":0,"total":0,"completed":[]}' > "$PROGRESS_FILE"
    echo -e "${GREEN}Progression remise à zéro !${NC}"
}

# Main command parsing
case "${1:-help}" in
    status)
        print_score
        ;;
    steps)
        show_steps
        ;;
    step)
        show_step "${2}"
        ;;
    validate)
        validate_step "${2}"
        ;;
    reset)
        reset_progress
        ;;
    help|--help|-h)
        show_help
        ;;
    [1-9]|1[0-9]|2[0-4])
        validate_step "${1}"
        ;;
    *)
        echo -e "${RED}Commande inconnue: ${1}${NC}"
        show_help
        ;;
esac
