#!/bin/bash
# === ÉTAPE 9 : Recherche de fichiers et de contenu ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "9.1 9.2 9.3 9.4"; }

show_step_exercises() {
    print_step_header 9 "Recherche de fichiers et de contenu"

    print_exercise "9.1" 3 "Utilisez ${BOLD}find${NC} pour trouver tous les fichiers ${BOLD}.conf${NC}\n     dans ${BOLD}/etc${NC} et sauvegardez le résultat dans\n     ${BOLD}/home/etudiant/conf-files.txt${NC}"
    print_exercise "9.2" 3 "Utilisez ${BOLD}grep${NC} pour trouver toutes les lignes contenant\n     ${BOLD}\"root\"${NC} dans ${BOLD}/etc/passwd${NC} et sauvegardez dans\n     ${BOLD}/home/etudiant/root-lines.txt${NC}"
    print_exercise "9.3" 3 "Comptez le nombre de lignes dans ${BOLD}/etc/passwd${NC} et\n     sauvegardez le nombre dans ${BOLD}/home/etudiant/nb-users.txt${NC}\n     ${DIM}(utilisez wc)${NC}"
    print_exercise "9.4" 3 "Trouvez tous les dossiers dans ${BOLD}/var${NC} et sauvegardez\n     le résultat dans ${BOLD}/home/etudiant/var-dirs.txt${NC}\n     ${DIM}(utilisez find avec -type d)${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 9${NC}"
}

run_validations() {
    print_step_header 9 "Validation - Recherche de fichiers et de contenu"

    # 9.1
    echo -e "  ${BOLD}Exercice 9.1${NC} - Trouver les fichiers .conf"
    if [ -f "/home/etudiant/conf-files.txt" ]; then
        if grep -q "\.conf" "/home/etudiant/conf-files.txt" 2>/dev/null; then
            print_success "Fichiers .conf trouvés et sauvegardés"
            add_score "9.1" 3
        else
            print_fail "Le fichier ne contient pas de fichiers .conf"
            print_hint "find /etc -name '*.conf' > /home/etudiant/conf-files.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/conf-files.txt non trouvé"
        print_hint "find /etc -name '*.conf' > /home/etudiant/conf-files.txt"
    fi

    # 9.2
    echo -e "  ${BOLD}Exercice 9.2${NC} - Grep root dans /etc/passwd"
    if [ -f "/home/etudiant/root-lines.txt" ]; then
        if grep -q "root" "/home/etudiant/root-lines.txt" 2>/dev/null; then
            print_success "Lignes contenant 'root' sauvegardées"
            add_score "9.2" 3
        else
            print_fail "Le fichier ne contient pas de lignes avec 'root'"
            print_hint "grep root /etc/passwd > /home/etudiant/root-lines.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/root-lines.txt non trouvé"
        print_hint "grep root /etc/passwd > /home/etudiant/root-lines.txt"
    fi

    # 9.3
    echo -e "  ${BOLD}Exercice 9.3${NC} - Compter les lignes de /etc/passwd"
    if [ -f "/home/etudiant/nb-users.txt" ]; then
        if [ -s "/home/etudiant/nb-users.txt" ]; then
            local content
            content=$(cat /home/etudiant/nb-users.txt | tr -d '[:space:]')
            if [[ "$content" =~ ^[0-9]+$ ]] && [ "$content" -gt 0 ]; then
                print_success "Nombre de lignes sauvegardé ($content)"
                add_score "9.3" 3
            else
                print_fail "Le fichier ne contient pas un nombre valide"
                print_hint "wc -l < /etc/passwd > /home/etudiant/nb-users.txt"
            fi
        else
            print_fail "Le fichier est vide"
            print_hint "wc -l < /etc/passwd > /home/etudiant/nb-users.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/nb-users.txt non trouvé"
        print_hint "wc -l < /etc/passwd > /home/etudiant/nb-users.txt"
    fi

    # 9.4
    echo -e "  ${BOLD}Exercice 9.4${NC} - Trouver les dossiers dans /var"
    if [ -f "/home/etudiant/var-dirs.txt" ]; then
        if grep -q "/var" "/home/etudiant/var-dirs.txt" 2>/dev/null; then
            print_success "Dossiers de /var sauvegardés"
            add_score "9.4" 3
        else
            print_fail "Le fichier ne contient pas de chemins /var"
            print_hint "find /var -type d > /home/etudiant/var-dirs.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/var-dirs.txt non trouvé"
        print_hint "find /var -type d > /home/etudiant/var-dirs.txt"
    fi
}
