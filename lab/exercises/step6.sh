#!/bin/bash
# === ÉTAPE 6 : Exercice pratique - Système familial ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 5; }
get_step_exercise_ids() { echo "6.1 6.2 6.3 6.4 6.5"; }

show_step_exercises() {
    print_step_header 6 "Exercice pratique : système familial"

    echo -e "  ${CYAN}Scénario :${NC} Vous configurez un PC familial sous Linux."
    echo -e "  Famille : ${BOLD}papa${NC}, ${BOLD}maman${NC}, ${BOLD}fils${NC}, ${BOLD}fille${NC}"
    echo ""

    print_exercise "6.1" 4 "Créez les 4 utilisateurs : ${BOLD}papa, maman, fils, fille${NC}.\n     Créez dans chaque home un dossier ${BOLD}Travail${NC} et un dossier ${BOLD}Bazar${NC}."
    print_exercise "6.2" 4 "Créez les groupes ${BOLD}parents${NC} et ${BOLD}enfants${NC}.\n     Ajoutez papa et maman dans ${BOLD}parents${NC}, fils et fille dans ${BOLD}enfants${NC}."
    print_exercise "6.3" 4 "Créez ${BOLD}/home/famille${NC} accessible en lecture/écriture\n     par tous les membres de la famille (groupe ${BOLD}famille${NC}, permissions ${BOLD}770${NC})."
    print_exercise "6.4" 4 "Créez ${BOLD}/home/parents-only${NC} accessible uniquement\n     par le groupe ${BOLD}parents${NC} (permissions ${BOLD}770${NC})."
    print_exercise "6.5" 4 "Créez un compte ${BOLD}invite${NC} (invité) qui n'a accès\n     à aucun des dossiers partagés familiaux."

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 6${NC}"
}

run_validations() {
    print_step_header 6 "Validation - Système familial"

    # 6.1
    echo -e "  ${BOLD}Exercice 6.1${NC} - Utilisateurs et dossiers personnels"
    local users_ok=true
    for user in papa maman fils fille; do
        if ! id "$user" > /dev/null 2>&1; then
            print_fail "Utilisateur $user non trouvé"
            users_ok=false
        fi
    done
    local dirs_ok=true
    for user in papa maman fils fille; do
        if [ ! -d "/home/$user/Travail" ] || [ ! -d "/home/$user/Bazar" ]; then
            print_fail "Dossiers Travail/Bazar manquants pour $user"
            dirs_ok=false
        fi
    done
    if $users_ok && $dirs_ok; then
        print_success "4 utilisateurs avec Travail et Bazar créés"
        add_score "6.1" 4
    fi

    # 6.2
    echo -e "  ${BOLD}Exercice 6.2${NC} - Groupes parents et enfants"
    local grp_ok=true
    if ! getent group parents > /dev/null 2>&1; then
        print_fail "Groupe parents non trouvé"
        grp_ok=false
    fi
    if ! getent group enfants > /dev/null 2>&1; then
        print_fail "Groupe enfants non trouvé"
        grp_ok=false
    fi
    if $grp_ok; then
        local p_ok=true e_ok=true
        for u in papa maman; do
            if ! id "$u" 2>/dev/null | grep -q "parents"; then
                print_fail "$u n'est pas dans le groupe parents"
                p_ok=false
            fi
        done
        for u in fils fille; do
            if ! id "$u" 2>/dev/null | grep -q "enfants"; then
                print_fail "$u n'est pas dans le groupe enfants"
                e_ok=false
            fi
        done
        if $p_ok && $e_ok; then
            print_success "Groupes parents et enfants correctement configurés"
            add_score "6.2" 4
        fi
    fi

    # 6.3
    echo -e "  ${BOLD}Exercice 6.3${NC} - Dossier /home/famille"
    if [ -d "/home/famille" ]; then
        local grp perms
        grp=$(stat -c '%G' /home/famille 2>/dev/null)
        perms=$(stat -c '%a' /home/famille 2>/dev/null)
        if getent group famille > /dev/null 2>&1 && [ "$grp" = "famille" ] && [ "$perms" = "770" ]; then
            print_success "/home/famille (groupe famille, permissions 770)"
            add_score "6.3" 4
        else
            [ "$grp" != "famille" ] && print_fail "Groupe: $grp (attendu: famille)"
            [ "$perms" != "770" ] && print_fail "Permissions: $perms (attendu: 770)"
        fi
    else
        print_fail "Dossier /home/famille non trouvé"
        print_hint "Créez un groupe famille, ajoutez tous les membres, puis mkdir + chgrp + chmod"
    fi

    # 6.4
    echo -e "  ${BOLD}Exercice 6.4${NC} - Dossier /home/parents-only"
    if [ -d "/home/parents-only" ]; then
        local grp perms
        grp=$(stat -c '%G' /home/parents-only 2>/dev/null)
        perms=$(stat -c '%a' /home/parents-only 2>/dev/null)
        if [ "$grp" = "parents" ] && [ "$perms" = "770" ]; then
            print_success "/home/parents-only (groupe parents, permissions 770)"
            add_score "6.4" 4
        else
            [ "$grp" != "parents" ] && print_fail "Groupe: $grp (attendu: parents)"
            [ "$perms" != "770" ] && print_fail "Permissions: $perms (attendu: 770)"
        fi
    else
        print_fail "Dossier /home/parents-only non trouvé"
    fi

    # 6.5
    echo -e "  ${BOLD}Exercice 6.5${NC} - Compte invite"
    if id invite > /dev/null 2>&1; then
        local in_famille=false in_parents=false in_enfants=false
        id invite 2>/dev/null | grep -q "famille" && in_famille=true
        id invite 2>/dev/null | grep -q "parents" && in_parents=true
        id invite 2>/dev/null | grep -q "enfants" && in_enfants=true
        if ! $in_famille && ! $in_parents && ! $in_enfants; then
            print_success "Compte invite créé, sans accès aux dossiers familiaux"
            add_score "6.5" 4
        else
            print_fail "invite ne devrait pas être dans les groupes famille/parents/enfants"
        fi
    else
        print_fail "Utilisateur invite non trouvé"
        print_hint "adduser invite"
    fi
}
