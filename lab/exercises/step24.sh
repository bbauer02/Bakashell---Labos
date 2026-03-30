#!/bin/bash
# === ÉTAPE 24 : Sécurité de base ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 5; }
get_step_exercise_ids() { echo "24.1 24.2 24.3 24.4 24.5"; }

show_step_exercises() {
    print_step_header 24 "Sécurité de base"

    print_exercise "24.1" 3 "Trouvez tous les fichiers avec le bit ${BOLD}SUID${NC} activé\n     sur le système et sauvegardez la liste dans\n     ${BOLD}/home/etudiant/suid-files.txt${NC}\n     ${DIM}(find / -perm -4000 -type f 2>/dev/null)${NC}"
    print_exercise "24.2" 3 "Trouvez les fichiers ${BOLD}modifiables par tout le monde${NC}\n     (world-writable) dans ${BOLD}/etc${NC} et sauvegardez dans\n     ${BOLD}/home/etudiant/world-writable.txt${NC}\n     ${DIM}(find /etc -perm -o+w -type f 2>/dev/null)${NC}"
    print_exercise "24.3" 4 "Créez un utilisateur ${BOLD}securise${NC} et configurez une\n     politique de mot de passe : expiration dans ${BOLD}90 jours${NC}\n     maximum. Verrouillez ensuite le compte.\n     ${DIM}(chage -M 90, passwd -l)${NC}"
    print_exercise "24.4" 3 "Vérifiez qu'aucun compte utilisateur n'a un ${BOLD}UID 0${NC}\n     (droits root) à part root lui-même.\n     Sauvegardez le résultat dans ${BOLD}/home/etudiant/uid-zero.txt${NC}\n     ${DIM}(awk -F: '\$3 == 0' /etc/passwd)${NC}"
    print_exercise "24.5" 4 "Créez un script d'audit ${BOLD}/home/etudiant/audit-securite.sh${NC}\n     exécutable qui génère un rapport ${BOLD}/home/etudiant/audit.txt${NC}\n     contenant : fichiers SUID, ports en écoute, utilisateurs\n     avec shell de connexion, et fichiers modifiés dans /etc\n     ces dernières 24h. Puis exécutez-le."

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 24${NC}"
}

run_validations() {
    print_step_header 24 "Validation - Sécurité de base"

    # 24.1
    echo -e "  ${BOLD}Exercice 24.1${NC} - Fichiers SUID"
    if [ -f "/home/etudiant/suid-files.txt" ]; then
        # Le fichier peut être vide si aucun fichier SUID, ou contenir des chemins
        if [ -f "/home/etudiant/suid-files.txt" ]; then
            # Vérifier que la recherche a été faite (même si résultat vide)
            local suid_count
            suid_count=$(wc -l < /home/etudiant/suid-files.txt)
            print_success "Recherche SUID effectuée ($suid_count fichiers trouvés)"
            add_score "24.1" 3
        fi
    else
        print_fail "Fichier /home/etudiant/suid-files.txt non trouvé"
        print_hint "find / -perm -4000 -type f 2>/dev/null > /home/etudiant/suid-files.txt"
    fi

    # 24.2
    echo -e "  ${BOLD}Exercice 24.2${NC} - Fichiers world-writable"
    if [ -f "/home/etudiant/world-writable.txt" ]; then
        # Le fichier peut être vide si aucun fichier world-writable (c'est bien !)
        print_success "Recherche world-writable effectuée"
        add_score "24.2" 3
    else
        print_fail "Fichier /home/etudiant/world-writable.txt non trouvé"
        print_hint "find /etc -perm -o+w -type f 2>/dev/null > /home/etudiant/world-writable.txt"
    fi

    # 24.3
    echo -e "  ${BOLD}Exercice 24.3${NC} - Politique de mot de passe"
    if id securise > /dev/null 2>&1; then
        local max_days locked
        max_days=$(chage -l securise 2>/dev/null | grep -i "maximum" | grep -oE '[0-9]+' | head -1)
        locked=$(passwd -S securise 2>/dev/null | awk '{print $2}')
        local ex3_ok=true
        if [ "$max_days" != "90" ]; then
            print_fail "Expiration: $max_days jours (attendu: 90)"
            ex3_ok=false
        fi
        if [ "$locked" != "L" ]; then
            print_fail "Le compte n'est pas verrouillé (statut: $locked)"
            ex3_ok=false
        fi
        if $ex3_ok; then
            print_success "Utilisateur securise : expiration 90 jours + compte verrouillé"
            add_score "24.3" 4
        else
            print_hint "chage -M 90 securise && passwd -l securise"
        fi
    else
        print_fail "Utilisateur securise non trouvé"
        print_hint "adduser securise && chage -M 90 securise && passwd -l securise"
    fi

    # 24.4
    echo -e "  ${BOLD}Exercice 24.4${NC} - Vérification UID 0"
    if [ -f "/home/etudiant/uid-zero.txt" ]; then
        if [ -s "/home/etudiant/uid-zero.txt" ]; then
            # Vérifier que seul root a l'UID 0
            local uid_zero_count
            uid_zero_count=$(wc -l < /home/etudiant/uid-zero.txt)
            if grep -q "root" /home/etudiant/uid-zero.txt 2>/dev/null; then
                print_success "Audit UID 0 effectué ($uid_zero_count compte(s) avec UID 0)"
                add_score "24.4" 3
            else
                print_fail "Le fichier ne contient pas root"
                print_hint "awk -F: '\$3 == 0 {print \$1}' /etc/passwd > /home/etudiant/uid-zero.txt"
            fi
        else
            print_fail "Le fichier est vide (root devrait y être)"
            print_hint "awk -F: '\$3 == 0 {print \$1}' /etc/passwd > /home/etudiant/uid-zero.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/uid-zero.txt non trouvé"
        print_hint "awk -F: '\$3 == 0 {print \$1}' /etc/passwd > /home/etudiant/uid-zero.txt"
    fi

    # 24.5
    echo -e "  ${BOLD}Exercice 24.5${NC} - Script d'audit de sécurité"
    if [ -f "/home/etudiant/audit-securite.sh" ] && [ -x "/home/etudiant/audit-securite.sh" ]; then
        if [ -f "/home/etudiant/audit.txt" ]; then
            local has_suid has_ports has_users
            has_suid=$(grep -ciE "(suid|perm|4000)" /home/etudiant/audit.txt 2>/dev/null || grep -c "/" /home/etudiant/audit.txt 2>/dev/null)
            has_ports=$(grep -ciE "(ss|netstat|port|listen|LISTEN)" /home/etudiant/audit.txt 2>/dev/null)
            has_users=$(grep -ciE "(bash|shell|passwd)" /home/etudiant/audit.txt 2>/dev/null)
            local total_checks=0
            [ "$has_suid" -ge 1 ] && total_checks=$((total_checks + 1))
            [ "$has_ports" -ge 1 ] && total_checks=$((total_checks + 1))
            [ "$has_users" -ge 1 ] && total_checks=$((total_checks + 1))
            if [ "$total_checks" -ge 2 ]; then
                print_success "Script d'audit complet — rapport généré"
                add_score "24.5" 4
            else
                print_fail "Le rapport ne contient pas assez d'informations"
                print_hint "Le script doit inclure : fichiers SUID, ports, utilisateurs avec shell, fichiers modifiés"
            fi
        else
            print_fail "Fichier /home/etudiant/audit.txt non trouvé"
            print_hint "Exécutez votre script : ./audit-securite.sh"
        fi
    else
        [ ! -f "/home/etudiant/audit-securite.sh" ] && print_fail "Script audit-securite.sh non trouvé"
        [ -f "/home/etudiant/audit-securite.sh" ] && [ ! -x "/home/etudiant/audit-securite.sh" ] && print_fail "Le script n'est pas exécutable"
    fi
}
