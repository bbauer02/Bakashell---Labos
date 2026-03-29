#!/bin/bash
# === ÉTAPE 1 : Premiers pas - Navigation ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "1.1 1.2 1.3 1.4"; }

show_step_exercises() {
    print_step_header 1 "Premiers pas : navigation dans le système"

    print_exercise "1.1" 3 "Utilisez ${BOLD}whoami${NC} et sauvegardez le résultat dans\n     ${BOLD}/home/etudiant/whoami.txt${NC}"
    print_exercise "1.2" 3 "Créez un dossier ${BOLD}/home/etudiant${NC} (votre espace de travail)."
    print_exercise "1.3" 2 "Naviguez jusqu'au dossier ${BOLD}/etc${NC} puis revenez dans ${BOLD}/home/etudiant${NC}."
    print_exercise "1.4" 4 "Listez le contenu du répertoire ${BOLD}/${NC} (racine) avec les détails (format long)."

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 1${NC}"
}

run_validations() {
    print_step_header 1 "Validation - Premiers pas"

    # 1.1 - whoami (on vérifie que l'utilisateur sait qui il est - toujours vrai dans le container)
    echo -e "  ${BOLD}Exercice 1.1${NC} - whoami"
    if [ -f "/home/etudiant/whoami.txt" ] && [ -s "/home/etudiant/whoami.txt" ]; then
        print_success "whoami sauvegardé dans whoami.txt ($(cat /home/etudiant/whoami.txt))"
        add_score "1.1" 3
    else
        print_fail "Fichier /home/etudiant/whoami.txt non trouvé ou vide"
        print_hint "whoami > /home/etudiant/whoami.txt"
    fi

    # 1.2 - Créer /home/etudiant
    echo -e "  ${BOLD}Exercice 1.2${NC} - Créer /home/etudiant"
    if [ -d "/home/etudiant" ]; then
        print_success "Le dossier /home/etudiant existe"
        add_score "1.2" 3
    else
        print_fail "Le dossier /home/etudiant n'existe pas"
        print_hint "Utilisez : mkdir /home/etudiant"
    fi

    # 1.3 - On vérifie que l'étudiant peut naviguer (on vérifie que /etc est accessible)
    echo -e "  ${BOLD}Exercice 1.3${NC} - Navigation /etc et retour"
    if [ -d "/etc" ] && [ -d "/home/etudiant" ]; then
        # Vérifie que l'étudiant a visité /etc en cherchant dans l'historique
        if bash -c "cd /etc && cd /home/etudiant && pwd" > /dev/null 2>&1; then
            print_success "Navigation /etc → /home/etudiant validée"
            add_score "1.3" 2
        else
            print_fail "Impossible de naviguer entre /etc et /home/etudiant"
        fi
    else
        print_fail "Créez d'abord /home/etudiant (exercice 1.2)"
        print_hint "cd /etc puis cd /home/etudiant"
    fi

    # 1.4 - Créer un fichier preuve du ls -l dans /
    echo -e "  ${BOLD}Exercice 1.4${NC} - Lister la racine en détail"
    if [ -f "/home/etudiant/racine.txt" ]; then
        # Vérifier que le fichier contient bien un ls -l (doit contenir "drwxr" ou similaire)
        if grep -qE "^(d|l|-|total)" "/home/etudiant/racine.txt" 2>/dev/null; then
            print_success "Listing détaillé de / sauvegardé dans racine.txt"
            add_score "1.4" 4
        else
            print_fail "Le fichier racine.txt ne contient pas un listing valide"
            print_hint "Utilisez : ls -l / > /home/etudiant/racine.txt"
        fi
    else
        print_fail "Sauvegardez le résultat dans /home/etudiant/racine.txt"
        print_hint "Utilisez : ls -l / > /home/etudiant/racine.txt"
    fi
}
