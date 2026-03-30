#!/bin/bash
# === ÉTAPE 15 : Filtrage et traitement de texte ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 3; }
get_step_exercise_ids() { echo "15.1 15.2 15.3"; }

show_step_exercises() {
    print_step_header 15 "Filtrage et traitement de texte"

    print_exercise "15.1" 3 "Extrayez les noms d'utilisateurs (1er champ) de ${BOLD}/etc/passwd${NC},\n     comptez les occurrences de chaque shell (dernier champ),\n     et sauvegardez le résultat trié dans\n     ${BOLD}/home/etudiant/shells-count.txt${NC}\n     ${DIM}(cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn)${NC}"
    print_exercise "15.2" 3 "Créez un fichier ${BOLD}/home/etudiant/data.txt${NC} contenant\n     10 lignes de noms (un par ligne, avec des doublons),\n     puis créez ${BOLD}/home/etudiant/data-unique.txt${NC} contenant\n     les noms triés sans doublons.\n     ${DIM}(sort + uniq ou sort -u)${NC}"
    print_exercise "15.3" 3 "Utilisez ${BOLD}awk${NC} pour extraire les noms d'utilisateurs et\n     leur UID (champs 1 et 3) de ${BOLD}/etc/passwd${NC} et sauvegardez\n     dans ${BOLD}/home/etudiant/users-uid.txt${NC}\n     ${DIM}(awk -F: '{print \$1, \$3}' /etc/passwd)${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 15${NC}"
}

run_validations() {
    print_step_header 15 "Validation - Filtrage et traitement de texte"

    # 15.1
    echo -e "  ${BOLD}Exercice 15.1${NC} - Comptage des shells"
    if [ -f "/home/etudiant/shells-count.txt" ]; then
        if grep -qE "(bash|sh|nologin|false|sync)" /home/etudiant/shells-count.txt 2>/dev/null; then
            print_success "Comptage des shells sauvegardé"
            add_score "15.1" 3
        else
            print_fail "Le fichier ne contient pas un comptage de shells valide"
            print_hint "cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn > /home/etudiant/shells-count.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/shells-count.txt non trouvé"
        print_hint "cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn > /home/etudiant/shells-count.txt"
    fi

    # 15.2
    echo -e "  ${BOLD}Exercice 15.2${NC} - Données triées sans doublons"
    if [ -f "/home/etudiant/data.txt" ] && [ -f "/home/etudiant/data-unique.txt" ]; then
        local data_lines unique_lines
        data_lines=$(wc -l < /home/etudiant/data.txt)
        unique_lines=$(wc -l < /home/etudiant/data-unique.txt)
        if [ "$data_lines" -ge 10 ] && [ "$unique_lines" -lt "$data_lines" ] && [ "$unique_lines" -gt 0 ]; then
            # Vérifier que c'est trié
            local is_sorted
            is_sorted=$(sort -c /home/etudiant/data-unique.txt 2>&1)
            if [ -z "$is_sorted" ]; then
                print_success "Données triées sans doublons ($data_lines lignes → $unique_lines uniques)"
                add_score "15.2" 3
            else
                print_fail "Le fichier data-unique.txt n'est pas trié"
                print_hint "sort -u /home/etudiant/data.txt > /home/etudiant/data-unique.txt"
            fi
        else
            [ "$data_lines" -lt 10 ] && print_fail "data.txt doit contenir au moins 10 lignes (actuellement $data_lines)"
            [ "$unique_lines" -ge "$data_lines" ] && print_fail "data-unique.txt doit avoir moins de lignes que data.txt (ajoutez des doublons dans data.txt)"
            print_hint "Créez data.txt avec des doublons puis : sort -u data.txt > data-unique.txt"
        fi
    else
        [ ! -f "/home/etudiant/data.txt" ] && print_fail "Fichier data.txt non trouvé"
        [ ! -f "/home/etudiant/data-unique.txt" ] && print_fail "Fichier data-unique.txt non trouvé"
        print_hint "Créez data.txt avec 10 lignes (avec doublons) puis sort -u data.txt > data-unique.txt"
    fi

    # 15.3
    echo -e "  ${BOLD}Exercice 15.3${NC} - Extraction avec awk"
    if [ -f "/home/etudiant/users-uid.txt" ]; then
        if grep -q "root" /home/etudiant/users-uid.txt 2>/dev/null && grep -qE "[0-9]+" /home/etudiant/users-uid.txt 2>/dev/null; then
            print_success "Noms et UIDs extraits avec awk"
            add_score "15.3" 3
        else
            print_fail "Le fichier ne contient pas les noms et UIDs attendus"
            print_hint "awk -F: '{print \$1, \$3}' /etc/passwd > /home/etudiant/users-uid.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/users-uid.txt non trouvé"
        print_hint "awk -F: '{print \$1, \$3}' /etc/passwd > /home/etudiant/users-uid.txt"
    fi
}
