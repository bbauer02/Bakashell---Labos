#!/bin/bash
# === ÉTAPE 17 : Tâches planifiées avec cron ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 3; }
get_step_exercise_ids() { echo "17.1 17.2 17.3"; }

show_step_exercises() {
    print_step_header 17 "Tâches planifiées avec cron"

    print_exercise "17.1" 3 "Affichez la crontab actuelle et sauvegardez le résultat\n     (ou le message 'no crontab') dans\n     ${BOLD}/home/etudiant/crontab-actuelle.txt${NC}\n     ${DIM}(crontab -l)${NC}"
    print_exercise "17.2" 3 "Créez un fichier cron ${BOLD}/etc/cron.d/backup-lab${NC} contenant\n     une tâche qui exécute ${BOLD}/home/etudiant/hello.sh${NC}\n     tous les jours à ${BOLD}2h du matin${NC}.\n     ${DIM}(format: 0 2 * * * root /home/etudiant/hello.sh)${NC}"
    print_exercise "17.3" 3 "Créez un script ${BOLD}/home/etudiant/cleanup.sh${NC} exécutable\n     qui supprime les fichiers .tmp de /tmp,\n     puis placez-le dans ${BOLD}/etc/cron.daily/${NC}\n     ${DIM}(les scripts dans cron.daily s'exécutent chaque jour)${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 17${NC}"
}

run_validations() {
    print_step_header 17 "Validation - Tâches planifiées"

    # 17.1
    echo -e "  ${BOLD}Exercice 17.1${NC} - Afficher la crontab"
    if [ -f "/home/etudiant/crontab-actuelle.txt" ]; then
        if [ -s "/home/etudiant/crontab-actuelle.txt" ] || [ -f "/home/etudiant/crontab-actuelle.txt" ]; then
            print_success "Crontab sauvegardée"
            add_score "17.1" 3
        fi
    else
        print_fail "Fichier /home/etudiant/crontab-actuelle.txt non trouvé"
        print_hint "crontab -l > /home/etudiant/crontab-actuelle.txt 2>&1"
    fi

    # 17.2
    echo -e "  ${BOLD}Exercice 17.2${NC} - Tâche cron dans /etc/cron.d/"
    if [ -f "/etc/cron.d/backup-lab" ]; then
        if grep -qE "^[0-9*].*hello\.sh" /etc/cron.d/backup-lab 2>/dev/null; then
            if grep -qE "^0\s+2\s+" /etc/cron.d/backup-lab 2>/dev/null; then
                print_success "Tâche cron configurée (tous les jours à 2h)"
                add_score "17.2" 3
            else
                print_fail "L'heure n'est pas correcte (attendu: 0 2 * * *)"
                print_hint "Format: 0 2 * * * root /home/etudiant/hello.sh"
            fi
        else
            print_fail "Le fichier ne contient pas une tâche cron valide"
            print_hint "echo '0 2 * * * root /home/etudiant/hello.sh' > /etc/cron.d/backup-lab"
        fi
    else
        print_fail "Fichier /etc/cron.d/backup-lab non trouvé"
        print_hint "echo '0 2 * * * root /home/etudiant/hello.sh' > /etc/cron.d/backup-lab"
    fi

    # 17.3
    echo -e "  ${BOLD}Exercice 17.3${NC} - Script dans cron.daily"
    if [ -f "/etc/cron.daily/cleanup.sh" ] || [ -f "/etc/cron.daily/cleanup" ]; then
        local script_path
        if [ -f "/etc/cron.daily/cleanup.sh" ]; then
            script_path="/etc/cron.daily/cleanup.sh"
        else
            script_path="/etc/cron.daily/cleanup"
        fi
        if [ -x "$script_path" ]; then
            if grep -qE "(rm|find).*\.tmp" "$script_path" 2>/dev/null || grep -qE "tmp" "$script_path" 2>/dev/null; then
                print_success "Script de nettoyage placé dans cron.daily"
                add_score "17.3" 3
            else
                print_fail "Le script ne semble pas supprimer les fichiers .tmp"
                print_hint "Le script doit contenir une commande pour supprimer les .tmp de /tmp"
            fi
        else
            print_fail "Le script n'est pas exécutable"
            print_hint "chmod +x $script_path"
        fi
    else
        print_fail "Script non trouvé dans /etc/cron.daily/"
        print_hint "Créez le script puis copiez-le : cp /home/etudiant/cleanup.sh /etc/cron.daily/"
    fi
}
