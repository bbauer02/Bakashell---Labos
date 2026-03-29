#!/bin/bash
# === ÉTAPE 5 : Super-utilisateur et processus ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 3; }
get_step_exercise_ids() { echo "5.1 5.2 5.3"; }

show_step_exercises() {
    print_step_header 5 "Super-utilisateur et processus"

    print_exercise "5.1" 4 "Créez un utilisateur ${BOLD}stagiaire${NC} et ajoutez-le au groupe ${BOLD}sudo${NC}\n     pour qu'il puisse utiliser sudo."
    print_exercise "5.2" 3 "Lancez un processus en arrière-plan (${BOLD}sleep 3600 &${NC}) puis\n     sauvegardez la liste des processus dans ${BOLD}/home/etudiant/processus.txt${NC}"
    print_exercise "5.3" 4 "Trouvez le PID du processus ${BOLD}sleep${NC} et terminez-le avec ${BOLD}kill${NC}.\n     Le processus sleep ne doit plus être actif."

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 5${NC}"
}

run_validations() {
    print_step_header 5 "Validation - Super-utilisateur et processus"

    # 5.1
    echo -e "  ${BOLD}Exercice 5.1${NC} - Utilisateur stagiaire dans sudo"
    if id stagiaire > /dev/null 2>&1; then
        if id stagiaire 2>/dev/null | grep -q "sudo"; then
            print_success "stagiaire est dans le groupe sudo"
            add_score "5.1" 4
        else
            print_fail "stagiaire existe mais n'est pas dans le groupe sudo"
            print_hint "adduser stagiaire sudo"
        fi
    else
        print_fail "Utilisateur stagiaire non trouvé"
        print_hint "adduser stagiaire && adduser stagiaire sudo"
    fi

    # 5.2
    echo -e "  ${BOLD}Exercice 5.2${NC} - Liste des processus"
    if [ -f "/home/etudiant/processus.txt" ]; then
        if grep -qE "(PID|pid|%CPU|COMMAND|CMD)" "/home/etudiant/processus.txt" 2>/dev/null; then
            print_success "Liste des processus sauvegardée"
            add_score "5.2" 3
        else
            print_fail "Le fichier ne semble pas contenir une liste de processus"
            print_hint "ps aux > /home/etudiant/processus.txt ou top -bn1 > /home/etudiant/processus.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/processus.txt non trouvé"
        print_hint "sleep 3600 & puis ps aux > /home/etudiant/processus.txt"
    fi

    # 5.3
    echo -e "  ${BOLD}Exercice 5.3${NC} - Terminer le processus sleep"
    if pgrep -x sleep > /dev/null 2>&1; then
        print_fail "Un processus sleep est encore actif (PID: $(pgrep -x sleep))"
        print_hint "kill $(pgrep -x sleep)"
    else
        print_success "Aucun processus sleep actif - bien terminé !"
        add_score "5.3" 4
    fi
}
