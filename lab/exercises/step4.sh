#!/bin/bash
# === ÉTAPE 4 : Utilisateurs, groupes et permissions ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 5; }
get_step_exercise_ids() { echo "4.1 4.2 4.3 4.4 4.5"; }

show_step_exercises() {
    print_step_header 4 "Utilisateurs, groupes et permissions"

    print_exercise "4.1" 3 "Créez un utilisateur ${BOLD}alice${NC} et un utilisateur ${BOLD}bob${NC}."
    print_exercise "4.2" 3 "Créez un groupe ${BOLD}equipe${NC} et ajoutez-y ${BOLD}alice${NC} et ${BOLD}bob${NC}."
    print_exercise "4.3" 4 "Créez un dossier ${BOLD}/home/partage${NC} appartenant au groupe ${BOLD}equipe${NC}."
    print_exercise "4.4" 4 "Mettez les permissions de ${BOLD}/home/partage${NC} à ${BOLD}770${NC}\n     (lecture/écriture/exécution pour user et groupe, rien pour les autres)."
    print_exercise "4.5" 3 "Créez un fichier ${BOLD}/home/partage/secret.txt${NC} avec les permissions\n     ${BOLD}640${NC} (rw pour owner, r pour groupe, rien pour others)."

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 4${NC}"
}

run_validations() {
    print_step_header 4 "Validation - Utilisateurs, groupes et permissions"

    # 4.1
    echo -e "  ${BOLD}Exercice 4.1${NC} - Utilisateurs alice et bob"
    local alice_ok=false bob_ok=false
    if id alice > /dev/null 2>&1; then alice_ok=true; fi
    if id bob > /dev/null 2>&1; then bob_ok=true; fi

    if $alice_ok && $bob_ok; then
        print_success "Utilisateurs alice et bob créés"
        add_score "4.1" 3
    else
        $alice_ok || print_fail "Utilisateur alice non trouvé"
        $bob_ok || print_fail "Utilisateur bob non trouvé"
        print_hint "adduser alice && adduser bob"
    fi

    # 4.2
    echo -e "  ${BOLD}Exercice 4.2${NC} - Groupe equipe"
    if getent group equipe > /dev/null 2>&1; then
        local members
        members=$(getent group equipe | cut -d: -f4)
        local alice_in=false bob_in=false
        if echo "$members" | grep -q "alice"; then alice_in=true; fi
        if echo "$members" | grep -q "bob"; then bob_in=true; fi
        if id alice 2>/dev/null | grep -q "equipe"; then alice_in=true; fi
        if id bob 2>/dev/null | grep -q "equipe"; then bob_in=true; fi

        if $alice_in && $bob_in; then
            print_success "Groupe equipe créé avec alice et bob"
            add_score "4.2" 3
        else
            $alice_in || print_fail "alice n'est pas dans le groupe equipe"
            $bob_in || print_fail "bob n'est pas dans le groupe equipe"
            print_hint "adduser alice equipe && adduser bob equipe"
        fi
    else
        print_fail "Groupe equipe non trouvé"
        print_hint "addgroup equipe"
    fi

    # 4.3
    echo -e "  ${BOLD}Exercice 4.3${NC} - Dossier /home/partage (groupe equipe)"
    if [ -d "/home/partage" ]; then
        local grp
        grp=$(stat -c '%G' /home/partage 2>/dev/null)
        if [ "$grp" = "equipe" ]; then
            print_success "/home/partage appartient au groupe equipe"
            add_score "4.3" 4
        else
            print_fail "/home/partage appartient au groupe '$grp' au lieu de 'equipe'"
            print_hint "chgrp equipe /home/partage"
        fi
    else
        print_fail "Dossier /home/partage non trouvé"
        print_hint "mkdir /home/partage && chgrp equipe /home/partage"
    fi

    # 4.4
    echo -e "  ${BOLD}Exercice 4.4${NC} - Permissions 770 sur /home/partage"
    if [ -d "/home/partage" ]; then
        local perms
        perms=$(stat -c '%a' /home/partage 2>/dev/null)
        if [ "$perms" = "770" ]; then
            print_success "Permissions 770 correctes sur /home/partage"
            add_score "4.4" 4
        else
            print_fail "Permissions actuelles : $perms (attendu : 770)"
            print_hint "chmod 770 /home/partage"
        fi
    else
        print_fail "Dossier /home/partage non trouvé"
    fi

    # 4.5
    echo -e "  ${BOLD}Exercice 4.5${NC} - Fichier secret.txt avec permissions 640"
    if [ -f "/home/partage/secret.txt" ]; then
        local perms
        perms=$(stat -c '%a' /home/partage/secret.txt 2>/dev/null)
        if [ "$perms" = "640" ]; then
            print_success "secret.txt avec permissions 640"
            add_score "4.5" 3
        else
            print_fail "Permissions actuelles : $perms (attendu : 640)"
            print_hint "chmod 640 /home/partage/secret.txt"
        fi
    else
        print_fail "Fichier /home/partage/secret.txt non trouvé"
        print_hint "touch /home/partage/secret.txt && chmod 640 /home/partage/secret.txt"
    fi
}
