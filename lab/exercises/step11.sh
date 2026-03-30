#!/bin/bash
# === ÉTAPE 11 : Édition de texte en terminal ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 3; }
get_step_exercise_ids() { echo "11.1 11.2 11.3"; }

show_step_exercises() {
    print_step_header 11 "Édition de texte en terminal"

    print_exercise "11.1" 3 "Créez un fichier ${BOLD}/home/etudiant/config.txt${NC} avec ${BOLD}nano${NC}\n     contenant exactement 3 lignes :\n     ${BOLD}serveur=localhost${NC}\n     ${BOLD}port=8080${NC}\n     ${BOLD}debug=false${NC}"
    print_exercise "11.2" 3 "Créez un fichier ${BOLD}/home/etudiant/memo.txt${NC} avec ${BOLD}vim${NC}\n     contenant le texte ${BOLD}\"Vim est un éditeur puissant\"${NC}"
    print_exercise "11.3" 3 "Utilisez ${BOLD}sed${NC} pour remplacer ${BOLD}debug=false${NC} par\n     ${BOLD}debug=true${NC} dans ${BOLD}/home/etudiant/config.txt${NC}\n     ${DIM}(utilisez sed -i pour modifier le fichier directement)${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 11${NC}"
}

run_validations() {
    print_step_header 11 "Validation - Édition de texte"

    # 11.1
    echo -e "  ${BOLD}Exercice 11.1${NC} - Fichier config.txt avec nano"
    if [ -f "/home/etudiant/config.txt" ]; then
        local has_serveur has_port has_debug
        has_serveur=$(grep -c "serveur=localhost" /home/etudiant/config.txt 2>/dev/null)
        has_port=$(grep -c "port=8080" /home/etudiant/config.txt 2>/dev/null)
        has_debug=$(grep -c "debug=" /home/etudiant/config.txt 2>/dev/null)
        if [ "$has_serveur" -ge 1 ] && [ "$has_port" -ge 1 ] && [ "$has_debug" -ge 1 ]; then
            print_success "config.txt contient les 3 lignes de configuration"
            add_score "11.1" 3
        else
            [ "$has_serveur" -lt 1 ] && print_fail "Ligne 'serveur=localhost' manquante"
            [ "$has_port" -lt 1 ] && print_fail "Ligne 'port=8080' manquante"
            [ "$has_debug" -lt 1 ] && print_fail "Ligne 'debug=...' manquante"
            print_hint "nano /home/etudiant/config.txt et ajoutez les 3 lignes"
        fi
    else
        print_fail "Fichier /home/etudiant/config.txt non trouvé"
        print_hint "nano /home/etudiant/config.txt"
    fi

    # 11.2
    echo -e "  ${BOLD}Exercice 11.2${NC} - Fichier memo.txt avec vim"
    if [ -f "/home/etudiant/memo.txt" ]; then
        if grep -qi "vim" /home/etudiant/memo.txt 2>/dev/null; then
            print_success "memo.txt contient le texte sur Vim"
            add_score "11.2" 3
        else
            print_fail "memo.txt ne contient pas le texte attendu"
            print_hint "vim /home/etudiant/memo.txt (i pour insérer, Echap puis :wq pour sauver)"
        fi
    else
        print_fail "Fichier /home/etudiant/memo.txt non trouvé"
        print_hint "vim /home/etudiant/memo.txt"
    fi

    # 11.3
    echo -e "  ${BOLD}Exercice 11.3${NC} - Remplacement avec sed"
    if [ -f "/home/etudiant/config.txt" ]; then
        if grep -q "debug=true" /home/etudiant/config.txt 2>/dev/null; then
            print_success "debug=false remplacé par debug=true"
            add_score "11.3" 3
        else
            if grep -q "debug=false" /home/etudiant/config.txt 2>/dev/null; then
                print_fail "debug=false n'a pas été remplacé par debug=true"
                print_hint "sed -i 's/debug=false/debug=true/' /home/etudiant/config.txt"
            else
                print_fail "La ligne debug= n'est pas dans le bon format"
                print_hint "Assurez-vous que config.txt contient debug=true"
            fi
        fi
    else
        print_fail "Fichier config.txt non trouvé — faites d'abord l'exercice 11.1"
    fi
}
