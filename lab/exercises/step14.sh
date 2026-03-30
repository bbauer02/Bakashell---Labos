#!/bin/bash
# === ÉTAPE 14 : Archivage et compression ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "14.1 14.2 14.3 14.4"; }

show_step_exercises() {
    print_step_header 14 "Archivage et compression"

    print_exercise "14.1" 3 "Créez un dossier ${BOLD}/home/etudiant/archive-test${NC} contenant\n     3 fichiers (${BOLD}a.txt, b.txt, c.txt${NC}) puis créez une archive\n     ${BOLD}/home/etudiant/archive-test.tar.gz${NC}"
    print_exercise "14.2" 3 "Extrayez l'archive ${BOLD}archive-test.tar.gz${NC} dans\n     ${BOLD}/home/etudiant/extraction/${NC}\n     ${DIM}(utilisez tar -xzf avec l'option -C)${NC}"
    print_exercise "14.3" 3 "Créez un fichier ${BOLD}/home/etudiant/compress-me.txt${NC} avec du\n     contenu puis compressez-le avec ${BOLD}gzip${NC}.\n     ${DIM}(le fichier .gz doit exister)${NC}"
    print_exercise "14.4" 3 "Créez une archive ${BOLD}/home/etudiant/backup.zip${NC} contenant\n     le dossier ${BOLD}/home/etudiant/archive-test${NC}\n     ${DIM}(utilisez zip -r)${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 14${NC}"
}

run_validations() {
    print_step_header 14 "Validation - Archivage et compression"

    # 14.1
    echo -e "  ${BOLD}Exercice 14.1${NC} - Créer une archive tar.gz"
    if [ -f "/home/etudiant/archive-test.tar.gz" ]; then
        if tar -tzf /home/etudiant/archive-test.tar.gz 2>/dev/null | grep -qE "(a\.txt|b\.txt|c\.txt)"; then
            print_success "Archive tar.gz créée avec les 3 fichiers"
            add_score "14.1" 3
        else
            print_fail "L'archive ne contient pas les fichiers attendus"
            print_hint "Créez les fichiers dans archive-test/ puis : tar -czf archive-test.tar.gz archive-test/"
        fi
    else
        print_fail "Archive /home/etudiant/archive-test.tar.gz non trouvée"
        print_hint "mkdir -p /home/etudiant/archive-test && touch /home/etudiant/archive-test/{a,b,c}.txt && cd /home/etudiant && tar -czf archive-test.tar.gz archive-test/"
    fi

    # 14.2
    echo -e "  ${BOLD}Exercice 14.2${NC} - Extraire l'archive"
    if [ -d "/home/etudiant/extraction" ]; then
        if find /home/etudiant/extraction -name "a.txt" 2>/dev/null | grep -q "a.txt"; then
            print_success "Archive extraite dans /home/etudiant/extraction/"
            add_score "14.2" 3
        else
            print_fail "Les fichiers extraits ne sont pas trouvés dans extraction/"
            print_hint "mkdir -p /home/etudiant/extraction && tar -xzf /home/etudiant/archive-test.tar.gz -C /home/etudiant/extraction/"
        fi
    else
        print_fail "Dossier /home/etudiant/extraction non trouvé"
        print_hint "mkdir -p /home/etudiant/extraction && tar -xzf /home/etudiant/archive-test.tar.gz -C /home/etudiant/extraction/"
    fi

    # 14.3
    echo -e "  ${BOLD}Exercice 14.3${NC} - Compression avec gzip"
    if [ -f "/home/etudiant/compress-me.txt.gz" ]; then
        print_success "Fichier compress-me.txt compressé en .gz"
        add_score "14.3" 3
    else
        if [ -f "/home/etudiant/compress-me.txt" ]; then
            print_fail "Le fichier existe mais n'a pas été compressé"
            print_hint "gzip /home/etudiant/compress-me.txt"
        else
            print_fail "Fichier compress-me.txt.gz non trouvé"
            print_hint "echo 'Du contenu' > /home/etudiant/compress-me.txt && gzip /home/etudiant/compress-me.txt"
        fi
    fi

    # 14.4
    echo -e "  ${BOLD}Exercice 14.4${NC} - Archive zip"
    if [ -f "/home/etudiant/backup.zip" ]; then
        if unzip -l /home/etudiant/backup.zip 2>/dev/null | grep -qE "(a\.txt|b\.txt|c\.txt)"; then
            print_success "Archive backup.zip créée"
            add_score "14.4" 3
        else
            print_fail "L'archive zip ne contient pas les fichiers attendus"
            print_hint "cd /home/etudiant && zip -r backup.zip archive-test/"
        fi
    else
        print_fail "Archive /home/etudiant/backup.zip non trouvée"
        print_hint "cd /home/etudiant && zip -r backup.zip archive-test/"
    fi
}
