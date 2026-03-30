#!/bin/bash
# === ÉTAPE 10 : Redirections et Pipes ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "10.1 10.2 10.3 10.4"; }

show_step_exercises() {
    print_step_header 10 "Redirections et Pipes"

    print_exercise "10.1" 3 "Utilisez un pipe pour compter le nombre de fichiers\n     dans ${BOLD}/etc${NC} et sauvegardez le résultat dans\n     ${BOLD}/home/etudiant/nb-etc.txt${NC}\n     ${DIM}(ls /etc | wc -l)${NC}"
    print_exercise "10.2" 3 "Redirigez les erreurs d'une commande ${BOLD}find /root${NC}\n     dans ${BOLD}/home/etudiant/erreurs.txt${NC} (sans afficher les erreurs)\n     ${DIM}(utilisez 2>)${NC}"
    print_exercise "10.3" 3 "Utilisez ${BOLD}tee${NC} pour sauvegarder le listing de ${BOLD}/usr/bin${NC}\n     dans ${BOLD}/home/etudiant/programmes.txt${NC}\n     ${DIM}(ls /usr/bin | tee /home/etudiant/programmes.txt)${NC}"
    print_exercise "10.4" 3 "Extrayez les noms d'utilisateurs de ${BOLD}/etc/passwd${NC},\n     triez-les et sauvegardez dans ${BOLD}/home/etudiant/users-sorted.txt${NC}\n     ${DIM}(combinez cut, sort et une redirection)${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 10${NC}"
}

run_validations() {
    print_step_header 10 "Validation - Redirections et Pipes"

    # 10.1
    echo -e "  ${BOLD}Exercice 10.1${NC} - Compter les fichiers de /etc"
    if [ -f "/home/etudiant/nb-etc.txt" ]; then
        local content
        content=$(cat /home/etudiant/nb-etc.txt | tr -d '[:space:]')
        if [[ "$content" =~ ^[0-9]+$ ]] && [ "$content" -gt 0 ]; then
            print_success "Nombre de fichiers dans /etc sauvegardé ($content)"
            add_score "10.1" 3
        else
            print_fail "Le fichier ne contient pas un nombre valide"
            print_hint "ls /etc | wc -l > /home/etudiant/nb-etc.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/nb-etc.txt non trouvé"
        print_hint "ls /etc | wc -l > /home/etudiant/nb-etc.txt"
    fi

    # 10.2
    echo -e "  ${BOLD}Exercice 10.2${NC} - Redirection des erreurs"
    if [ -f "/home/etudiant/erreurs.txt" ]; then
        if [ -s "/home/etudiant/erreurs.txt" ] || [ -f "/home/etudiant/erreurs.txt" ]; then
            print_success "Fichier erreurs.txt créé (redirection 2>)"
            add_score "10.2" 3
        fi
    else
        print_fail "Fichier /home/etudiant/erreurs.txt non trouvé"
        print_hint "find /root 2> /home/etudiant/erreurs.txt"
    fi

    # 10.3
    echo -e "  ${BOLD}Exercice 10.3${NC} - Utilisation de tee"
    if [ -f "/home/etudiant/programmes.txt" ]; then
        local nb_lines
        nb_lines=$(wc -l < /home/etudiant/programmes.txt)
        if [ "$nb_lines" -gt 10 ]; then
            print_success "Liste des programmes sauvegardée ($nb_lines programmes)"
            add_score "10.3" 3
        else
            print_fail "Le fichier semble incomplet (seulement $nb_lines lignes)"
            print_hint "ls /usr/bin | tee /home/etudiant/programmes.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/programmes.txt non trouvé"
        print_hint "ls /usr/bin | tee /home/etudiant/programmes.txt"
    fi

    # 10.4
    echo -e "  ${BOLD}Exercice 10.4${NC} - Utilisateurs triés"
    if [ -f "/home/etudiant/users-sorted.txt" ]; then
        # Vérifier que c'est trié et contient des noms d'utilisateurs
        local first_line
        first_line=$(head -1 /home/etudiant/users-sorted.txt)
        local is_sorted
        is_sorted=$(sort -c /home/etudiant/users-sorted.txt 2>&1)
        if [ -z "$is_sorted" ] && [ -s "/home/etudiant/users-sorted.txt" ]; then
            print_success "Noms d'utilisateurs triés correctement"
            add_score "10.4" 3
        else
            print_fail "Le fichier n'est pas correctement trié"
            print_hint "cut -d: -f1 /etc/passwd | sort > /home/etudiant/users-sorted.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/users-sorted.txt non trouvé"
        print_hint "cut -d: -f1 /etc/passwd | sort > /home/etudiant/users-sorted.txt"
    fi
}
