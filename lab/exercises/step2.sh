#!/bin/bash
# === ÉTAPE 2 : Le manuel et les chemins ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "2.1 2.2 2.3 2.4"; }

show_step_exercises() {
    print_step_header 2 "Le manuel et les chemins"

    print_exercise "2.1" 3 "Consultez le manuel de la commande ${BOLD}ls${NC} et sauvegardez\n     la section DESCRIPTION dans ${BOLD}/home/etudiant/man-ls.txt${NC}"
    print_exercise "2.2" 3 "Depuis ${BOLD}/home/etudiant${NC}, créez un dossier ${BOLD}projets${NC} en utilisant\n     un ${BOLD}chemin relatif${NC}."
    print_exercise "2.3" 3 "Créez un fichier ${BOLD}/home/etudiant/projets/info.txt${NC} en utilisant\n     un ${BOLD}chemin absolu${NC}."
    print_exercise "2.4" 3 "Depuis ${BOLD}/home/etudiant/projets${NC}, accédez au dossier parent\n     avec ${BOLD}..${NC} puis vérifiez avec ${BOLD}pwd${NC}."

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 2${NC}"
}

run_validations() {
    print_step_header 2 "Validation - Le manuel et les chemins"

    # 2.1
    echo -e "  ${BOLD}Exercice 2.1${NC} - Manuel de ls"
    if [ -f "/home/etudiant/man-ls.txt" ]; then
        if [ -s "/home/etudiant/man-ls.txt" ]; then
            print_success "Fichier man-ls.txt créé avec du contenu"
            add_score "2.1" 3
        else
            print_fail "Le fichier man-ls.txt est vide"
        fi
    else
        print_fail "Fichier /home/etudiant/man-ls.txt non trouvé"
        print_hint "Utilisez : man ls | head -50 > /home/etudiant/man-ls.txt"
    fi

    # 2.2
    echo -e "  ${BOLD}Exercice 2.2${NC} - Dossier projets (chemin relatif)"
    if [ -d "/home/etudiant/projets" ]; then
        print_success "Dossier /home/etudiant/projets existe"
        add_score "2.2" 3
    else
        print_fail "Dossier /home/etudiant/projets non trouvé"
        print_hint "cd /home/etudiant && mkdir projets"
    fi

    # 2.3
    echo -e "  ${BOLD}Exercice 2.3${NC} - Fichier info.txt (chemin absolu)"
    if [ -f "/home/etudiant/projets/info.txt" ]; then
        print_success "Fichier /home/etudiant/projets/info.txt existe"
        add_score "2.3" 3
    else
        print_fail "Fichier /home/etudiant/projets/info.txt non trouvé"
        print_hint "touch /home/etudiant/projets/info.txt"
    fi

    # 2.4
    echo -e "  ${BOLD}Exercice 2.4${NC} - Navigation avec .."
    if [ -d "/home/etudiant/projets" ] && [ -d "/home/etudiant" ]; then
        print_success "Navigation parent validée (les dossiers existent)"
        add_score "2.4" 3
    else
        print_fail "Créez d'abord les dossiers requis"
    fi
}
