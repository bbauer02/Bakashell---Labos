#!/bin/bash
# === ÉTAPE 20 : Liens symboliques et liens durs ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "20.1 20.2 20.3 20.4"; }

show_step_exercises() {
    print_step_header 20 "Liens symboliques et liens durs"

    print_exercise "20.1" 3 "Créez un fichier ${BOLD}/home/etudiant/original.txt${NC} contenant\n     ${BOLD}\"Fichier original\"${NC}, puis créez un lien dur\n     ${BOLD}/home/etudiant/lien-dur.txt${NC} pointant vers ce fichier.\n     ${DIM}(ln original.txt lien-dur.txt)${NC}"
    print_exercise "20.2" 3 "Vérifiez que ${BOLD}original.txt${NC} et ${BOLD}lien-dur.txt${NC} ont le\n     même inode. Sauvegardez le résultat de ${BOLD}ls -li${NC} dans\n     ${BOLD}/home/etudiant/inodes.txt${NC}"
    print_exercise "20.3" 3 "Créez un lien symbolique ${BOLD}/home/etudiant/lien-sym${NC}\n     pointant vers le dossier ${BOLD}/etc${NC}.\n     ${DIM}(ln -s /etc lien-sym)${NC}"
    print_exercise "20.4" 3 "Créez un lien symbolique ${BOLD}/home/etudiant/raccourci-passwd${NC}\n     pointant vers ${BOLD}/etc/passwd${NC}. Vérifiez que vous pouvez\n     lire le fichier via le lien : ${BOLD}cat raccourci-passwd${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 20${NC}"
}

run_validations() {
    print_step_header 20 "Validation - Liens symboliques et liens durs"

    # 20.1
    echo -e "  ${BOLD}Exercice 20.1${NC} - Lien dur"
    if [ -f "/home/etudiant/original.txt" ] && [ -f "/home/etudiant/lien-dur.txt" ]; then
        local inode_orig inode_dur
        inode_orig=$(stat -c '%i' /home/etudiant/original.txt 2>/dev/null)
        inode_dur=$(stat -c '%i' /home/etudiant/lien-dur.txt 2>/dev/null)
        if [ "$inode_orig" = "$inode_dur" ]; then
            if grep -q "original" /home/etudiant/original.txt 2>/dev/null; then
                print_success "Lien dur créé (même inode: $inode_orig)"
                add_score "20.1" 3
            else
                print_fail "original.txt ne contient pas le texte attendu"
                print_hint "echo 'Fichier original' > /home/etudiant/original.txt"
            fi
        else
            print_fail "Les fichiers n'ont pas le même inode (ce n'est pas un lien dur)"
            print_hint "ln /home/etudiant/original.txt /home/etudiant/lien-dur.txt"
        fi
    else
        [ ! -f "/home/etudiant/original.txt" ] && print_fail "Fichier original.txt non trouvé"
        [ ! -f "/home/etudiant/lien-dur.txt" ] && print_fail "Fichier lien-dur.txt non trouvé"
        print_hint "echo 'Fichier original' > /home/etudiant/original.txt && ln /home/etudiant/original.txt /home/etudiant/lien-dur.txt"
    fi

    # 20.2
    echo -e "  ${BOLD}Exercice 20.2${NC} - Vérification des inodes"
    if [ -f "/home/etudiant/inodes.txt" ]; then
        if grep -qE "^[0-9]+" /home/etudiant/inodes.txt 2>/dev/null; then
            print_success "Listing des inodes sauvegardé"
            add_score "20.2" 3
        else
            print_fail "Le fichier ne contient pas de numéros d'inode"
            print_hint "ls -li /home/etudiant/original.txt /home/etudiant/lien-dur.txt > /home/etudiant/inodes.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/inodes.txt non trouvé"
        print_hint "ls -li /home/etudiant/original.txt /home/etudiant/lien-dur.txt > /home/etudiant/inodes.txt"
    fi

    # 20.3
    echo -e "  ${BOLD}Exercice 20.3${NC} - Lien symbolique vers /etc"
    if [ -L "/home/etudiant/lien-sym" ]; then
        local target
        target=$(readlink /home/etudiant/lien-sym)
        if [ "$target" = "/etc" ]; then
            print_success "Lien symbolique lien-sym → /etc"
            add_score "20.3" 3
        else
            print_fail "Le lien pointe vers '$target' au lieu de '/etc'"
            print_hint "rm /home/etudiant/lien-sym && ln -s /etc /home/etudiant/lien-sym"
        fi
    else
        if [ -e "/home/etudiant/lien-sym" ]; then
            print_fail "lien-sym existe mais n'est pas un lien symbolique"
        else
            print_fail "Lien symbolique /home/etudiant/lien-sym non trouvé"
        fi
        print_hint "ln -s /etc /home/etudiant/lien-sym"
    fi

    # 20.4
    echo -e "  ${BOLD}Exercice 20.4${NC} - Lien symbolique vers /etc/passwd"
    if [ -L "/home/etudiant/raccourci-passwd" ]; then
        local target
        target=$(readlink /home/etudiant/raccourci-passwd)
        if [ "$target" = "/etc/passwd" ]; then
            if cat /home/etudiant/raccourci-passwd > /dev/null 2>&1; then
                print_success "Lien symbolique raccourci-passwd → /etc/passwd (lisible)"
                add_score "20.4" 3
            else
                print_fail "Le lien existe mais n'est pas lisible"
            fi
        else
            print_fail "Le lien pointe vers '$target' au lieu de '/etc/passwd'"
        fi
    else
        print_fail "Lien symbolique /home/etudiant/raccourci-passwd non trouvé"
        print_hint "ln -s /etc/passwd /home/etudiant/raccourci-passwd"
    fi
}
