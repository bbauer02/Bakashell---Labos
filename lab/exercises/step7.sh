#!/bin/bash
# === ÉTAPE 7 : Installer des programmes ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 2; }
get_step_exercise_ids() { echo "7.1 7.2"; }

show_step_exercises() {
    print_step_header 7 "Installer des programmes"

    print_exercise "7.1" 4 "Mettez à jour la liste des paquets avec ${BOLD}apt-get update${NC}\n     puis installez le paquet ${BOLD}curl${NC} avec apt-get."
    print_exercise "7.2" 4 "Téléchargez un fichier depuis internet avec ${BOLD}wget${NC} ou ${BOLD}curl${NC}\n     et sauvegardez-le dans ${BOLD}/home/etudiant/download-test.txt${NC}\n     ${DIM}(ex: wget -O /home/etudiant/download-test.txt http://example.com)${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 7${NC}"
}

run_validations() {
    print_step_header 7 "Validation - Installer des programmes"

    # 7.1
    echo -e "  ${BOLD}Exercice 7.1${NC} - Installation de curl"
    if command -v curl > /dev/null 2>&1; then
        print_success "curl est installé"
        add_score "7.1" 4
    else
        print_fail "curl n'est pas installé"
        print_hint "apt-get update && apt-get install -y curl"
    fi

    # 7.2
    echo -e "  ${BOLD}Exercice 7.2${NC} - Téléchargement de fichier"
    if [ -f "/home/etudiant/download-test.txt" ]; then
        if [ -s "/home/etudiant/download-test.txt" ]; then
            print_success "Fichier téléchargé avec succès"
            add_score "7.2" 4
        else
            print_fail "Le fichier est vide"
        fi
    else
        print_fail "Fichier /home/etudiant/download-test.txt non trouvé"
        print_hint "wget -O /home/etudiant/download-test.txt http://example.com"
    fi
}
