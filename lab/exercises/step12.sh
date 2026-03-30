#!/bin/bash
# === ÉTAPE 12 : Variables d'environnement et configuration shell ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "12.1 12.2 12.3 12.4"; }

show_step_exercises() {
    print_step_header 12 "Variables d'environnement et configuration shell"

    print_exercise "12.1" 3 "Sauvegardez la liste de toutes les variables d'environnement\n     dans ${BOLD}/home/etudiant/env-vars.txt${NC}\n     ${DIM}(utilisez env ou printenv)${NC}"
    print_exercise "12.2" 3 "Créez une variable d'environnement ${BOLD}PROJET=linux-lab${NC}\n     et sauvegardez sa valeur dans ${BOLD}/home/etudiant/projet.txt${NC}\n     ${DIM}(export PROJET=linux-lab)${NC}"
    print_exercise "12.3" 3 "Affichez le contenu de ${BOLD}\$PATH${NC} et sauvegardez-le\n     dans ${BOLD}/home/etudiant/mon-path.txt${NC}"
    print_exercise "12.4" 3 "Ajoutez l'alias ${BOLD}ll='ls -la'${NC} dans ${BOLD}/root/.bashrc${NC}\n     pour qu'il soit disponible à chaque ouverture de terminal."

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 12${NC}"
}

run_validations() {
    print_step_header 12 "Validation - Variables d'environnement"

    # 12.1
    echo -e "  ${BOLD}Exercice 12.1${NC} - Liste des variables d'environnement"
    if [ -f "/home/etudiant/env-vars.txt" ]; then
        if grep -qE "(PATH=|HOME=|SHELL=)" /home/etudiant/env-vars.txt 2>/dev/null; then
            print_success "Variables d'environnement sauvegardées"
            add_score "12.1" 3
        else
            print_fail "Le fichier ne contient pas les variables d'environnement"
            print_hint "env > /home/etudiant/env-vars.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/env-vars.txt non trouvé"
        print_hint "env > /home/etudiant/env-vars.txt"
    fi

    # 12.2
    echo -e "  ${BOLD}Exercice 12.2${NC} - Variable PROJET"
    if [ -f "/home/etudiant/projet.txt" ]; then
        if grep -q "linux-lab" /home/etudiant/projet.txt 2>/dev/null; then
            print_success "Variable PROJET=linux-lab sauvegardée"
            add_score "12.2" 3
        else
            print_fail "Le fichier ne contient pas 'linux-lab'"
            print_hint "export PROJET=linux-lab && echo \$PROJET > /home/etudiant/projet.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/projet.txt non trouvé"
        print_hint "export PROJET=linux-lab && echo \$PROJET > /home/etudiant/projet.txt"
    fi

    # 12.3
    echo -e "  ${BOLD}Exercice 12.3${NC} - Contenu du PATH"
    if [ -f "/home/etudiant/mon-path.txt" ]; then
        if grep -qE "(\/usr\/bin|\/usr\/local\/bin|\/bin)" /home/etudiant/mon-path.txt 2>/dev/null; then
            print_success "Contenu du PATH sauvegardé"
            add_score "12.3" 3
        else
            print_fail "Le fichier ne contient pas un PATH valide"
            print_hint "echo \$PATH > /home/etudiant/mon-path.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/mon-path.txt non trouvé"
        print_hint "echo \$PATH > /home/etudiant/mon-path.txt"
    fi

    # 12.4
    echo -e "  ${BOLD}Exercice 12.4${NC} - Alias ll dans .bashrc"
    local bashrc_file="/root/.bashrc"
    if [ -f "$bashrc_file" ]; then
        if grep -q "alias ll=" "$bashrc_file" 2>/dev/null; then
            print_success "Alias ll ajouté dans .bashrc"
            add_score "12.4" 3
        else
            print_fail "Alias ll non trouvé dans $bashrc_file"
            print_hint "echo \"alias ll='ls -la'\" >> /root/.bashrc"
        fi
    else
        print_fail "Fichier $bashrc_file non trouvé"
        print_hint "echo \"alias ll='ls -la'\" >> /root/.bashrc"
    fi
}
