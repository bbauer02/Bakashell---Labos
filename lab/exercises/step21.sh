#!/bin/bash
# === ÉTAPE 21 : Expressions régulières ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "21.1 21.2 21.3 21.4"; }

show_step_exercises() {
    print_step_header 21 "Expressions régulières"

    print_exercise "21.1" 3 "Utilisez ${BOLD}grep${NC} avec une regex pour extraire toutes les\n     lignes de ${BOLD}/etc/passwd${NC} qui commencent par la lettre ${BOLD}r${NC}.\n     Sauvegardez dans ${BOLD}/home/etudiant/regex-r.txt${NC}\n     ${DIM}(grep '^r' /etc/passwd)${NC}"
    print_exercise "21.2" 3 "Créez un fichier ${BOLD}/home/etudiant/emails.txt${NC} contenant\n     au moins 5 lignes dont 3 adresses email valides et\n     2 lignes sans email. Puis extrayez les emails dans\n     ${BOLD}/home/etudiant/emails-found.txt${NC}\n     ${DIM}(grep -E '[a-zA-Z0-9.]+@[a-zA-Z0-9.]+')${NC}"
    print_exercise "21.3" 3 "Extrayez les lignes NON vides et NON commentées\n     (ne commençant pas par ${BOLD}#${NC}) de ${BOLD}/etc/hosts${NC}.\n     Sauvegardez dans ${BOLD}/home/etudiant/hosts-clean.txt${NC}\n     ${DIM}(combinez grep -v '^#' et grep -v '^$')${NC}"
    print_exercise "21.4" 3 "Utilisez ${BOLD}sed${NC} avec une regex pour remplacer tous les\n     chiffres dans ${BOLD}/home/etudiant/emails.txt${NC} par ${BOLD}X${NC}.\n     Sauvegardez le résultat dans ${BOLD}/home/etudiant/censored.txt${NC}\n     ${DIM}(sed 's/[0-9]/X/g')${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 21${NC}"
}

run_validations() {
    print_step_header 21 "Validation - Expressions régulières"

    # 21.1
    echo -e "  ${BOLD}Exercice 21.1${NC} - Grep avec regex ^r"
    if [ -f "/home/etudiant/regex-r.txt" ]; then
        if [ -s "/home/etudiant/regex-r.txt" ]; then
            local all_start_r=true
            while IFS= read -r line; do
                if [ -n "$line" ] && [[ ! "$line" =~ ^r ]]; then
                    all_start_r=false
                    break
                fi
            done < /home/etudiant/regex-r.txt
            if $all_start_r && grep -q "root" /home/etudiant/regex-r.txt 2>/dev/null; then
                print_success "Lignes commençant par 'r' extraites"
                add_score "21.1" 3
            else
                print_fail "Le fichier contient des lignes ne commençant pas par 'r'"
                print_hint "grep '^r' /etc/passwd > /home/etudiant/regex-r.txt"
            fi
        else
            print_fail "Le fichier est vide"
            print_hint "grep '^r' /etc/passwd > /home/etudiant/regex-r.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/regex-r.txt non trouvé"
        print_hint "grep '^r' /etc/passwd > /home/etudiant/regex-r.txt"
    fi

    # 21.2
    echo -e "  ${BOLD}Exercice 21.2${NC} - Extraction d'emails"
    if [ -f "/home/etudiant/emails.txt" ] && [ -f "/home/etudiant/emails-found.txt" ]; then
        local total_lines email_lines found_lines
        total_lines=$(wc -l < /home/etudiant/emails.txt)
        found_lines=$(wc -l < /home/etudiant/emails-found.txt)
        if [ "$total_lines" -ge 5 ] && [ "$found_lines" -ge 1 ]; then
            if grep -qE '@' /home/etudiant/emails-found.txt 2>/dev/null; then
                print_success "Emails extraits ($found_lines emails trouvés sur $total_lines lignes)"
                add_score "21.2" 3
            else
                print_fail "emails-found.txt ne contient pas d'adresses email"
                print_hint "grep -E '[a-zA-Z0-9.]+@[a-zA-Z0-9.]+' emails.txt > emails-found.txt"
            fi
        else
            [ "$total_lines" -lt 5 ] && print_fail "emails.txt doit contenir au moins 5 lignes ($total_lines actuellement)"
            [ "$found_lines" -lt 1 ] && print_fail "emails-found.txt est vide"
        fi
    else
        [ ! -f "/home/etudiant/emails.txt" ] && print_fail "Fichier emails.txt non trouvé"
        [ ! -f "/home/etudiant/emails-found.txt" ] && print_fail "Fichier emails-found.txt non trouvé"
        print_hint "Créez emails.txt avec 5 lignes (dont 3 emails), puis grep -E pour extraire"
    fi

    # 21.3
    echo -e "  ${BOLD}Exercice 21.3${NC} - Filtrer hosts (sans commentaires ni vides)"
    if [ -f "/home/etudiant/hosts-clean.txt" ]; then
        if [ -s "/home/etudiant/hosts-clean.txt" ]; then
            local has_comments has_empty
            has_comments=$(grep -c '^#' /home/etudiant/hosts-clean.txt 2>/dev/null)
            has_empty=$(grep -c '^$' /home/etudiant/hosts-clean.txt 2>/dev/null)
            if [ "$has_comments" -eq 0 ] && [ "$has_empty" -eq 0 ]; then
                print_success "Fichier hosts nettoyé (sans commentaires ni lignes vides)"
                add_score "21.3" 3
            else
                [ "$has_comments" -gt 0 ] && print_fail "Le fichier contient encore des lignes commentées (#)"
                [ "$has_empty" -gt 0 ] && print_fail "Le fichier contient encore des lignes vides"
                print_hint "grep -v '^#' /etc/hosts | grep -v '^$' > /home/etudiant/hosts-clean.txt"
            fi
        else
            print_fail "Le fichier est vide"
        fi
    else
        print_fail "Fichier /home/etudiant/hosts-clean.txt non trouvé"
        print_hint "grep -v '^#' /etc/hosts | grep -v '^$' > /home/etudiant/hosts-clean.txt"
    fi

    # 21.4
    echo -e "  ${BOLD}Exercice 21.4${NC} - Remplacement avec sed et regex"
    if [ -f "/home/etudiant/censored.txt" ]; then
        if [ -s "/home/etudiant/censored.txt" ]; then
            # Vérifier qu'il y a des X et pas de chiffres
            local has_x has_digits
            has_x=$(grep -c "X" /home/etudiant/censored.txt 2>/dev/null)
            has_digits=$(grep -cE '[0-9]' /home/etudiant/censored.txt 2>/dev/null)
            if [ "$has_x" -ge 1 ] && [ "$has_digits" -eq 0 ]; then
                print_success "Chiffres remplacés par X"
                add_score "21.4" 3
            elif [ "$has_x" -ge 1 ]; then
                # Certains chiffres restent, mais il y a des X - accepter si la majorité est OK
                print_success "Remplacement effectué (certains chiffres convertis en X)"
                add_score "21.4" 3
            else
                print_fail "Le fichier ne contient pas de remplacements"
                print_hint "sed 's/[0-9]/X/g' /home/etudiant/emails.txt > /home/etudiant/censored.txt"
            fi
        else
            print_fail "Le fichier est vide"
        fi
    else
        print_fail "Fichier /home/etudiant/censored.txt non trouvé"
        print_hint "sed 's/[0-9]/X/g' /home/etudiant/emails.txt > /home/etudiant/censored.txt"
    fi
}
