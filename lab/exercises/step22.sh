#!/bin/bash
# === ÉTAPE 22 : SSH et accès distant ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 5; }
get_step_exercise_ids() { echo "22.1 22.2 22.3 22.4 22.5"; }

show_step_exercises() {
    print_step_header 22 "SSH et accès distant"

    echo -e "  ${CYAN}Info :${NC} Un serveur SSH ${BOLD}ssh-target${NC} est disponible sur le réseau."
    echo -e "  Utilisateur : ${BOLD}etudiant${NC} / Mot de passe : ${BOLD}etudiant${NC}"
    echo -e "  ${DIM}(Ce serveur est verrouillé : connexion uniquement, aucune commande possible)${NC}"
    echo ""

    print_exercise "22.1" 3 "Générez une paire de clés SSH de type ${BOLD}ed25519${NC}\n     dans ${BOLD}/root/.ssh/${NC} (sans passphrase).\n     ${DIM}(ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N \"\")${NC}"
    print_exercise "22.2" 3 "Vérifiez les permissions du dossier ${BOLD}/root/.ssh${NC}\n     (doit être ${BOLD}700${NC}) et de la clé privée\n     (doit être ${BOLD}600${NC}). Corrigez si nécessaire."
    print_exercise "22.3" 3 "Créez un fichier de configuration SSH\n     ${BOLD}/root/.ssh/config${NC} contenant un alias ${BOLD}serveur-test${NC}\n     qui pointe vers l'hôte ${BOLD}ssh-target${NC}\n     avec l'utilisateur ${BOLD}etudiant${NC}."
    print_exercise "22.4" 3 "Ajoutez votre clé publique au fichier\n     ${BOLD}/root/.ssh/authorized_keys${NC}\n     avec les permissions ${BOLD}600${NC}."
    print_exercise "22.5" 4 "Connectez-vous au serveur ${BOLD}ssh-target${NC} et\n     sauvegardez la sortie dans ${BOLD}/root/ssh-test.txt${NC}.\n     ${DIM}(sshpass -p 'etudiant' ssh -o StrictHostKeyChecking=no etudiant@ssh-target > /root/ssh-test.txt)${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 22${NC}"
}

run_validations() {
    print_step_header 22 "Validation - SSH et accès distant"

    # 22.1
    echo -e "  ${BOLD}Exercice 22.1${NC} - Génération de clés SSH"
    if [ -f "/root/.ssh/id_ed25519" ] && [ -f "/root/.ssh/id_ed25519.pub" ]; then
        if head -1 /root/.ssh/id_ed25519 | grep -q "OPENSSH PRIVATE KEY" 2>/dev/null; then
            if grep -q "ssh-ed25519" /root/.ssh/id_ed25519.pub 2>/dev/null; then
                print_success "Paire de clés ed25519 générée"
                add_score "22.1" 3
            else
                print_fail "La clé publique n'est pas de type ed25519"
            fi
        else
            print_fail "La clé privée n'est pas valide"
        fi
    else
        [ ! -f "/root/.ssh/id_ed25519" ] && print_fail "Clé privée /root/.ssh/id_ed25519 non trouvée"
        [ ! -f "/root/.ssh/id_ed25519.pub" ] && print_fail "Clé publique /root/.ssh/id_ed25519.pub non trouvée"
        print_hint "ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ''"
    fi

    # 22.2
    echo -e "  ${BOLD}Exercice 22.2${NC} - Permissions SSH"
    local perms_ok=true
    if [ -d "/root/.ssh" ]; then
        local dir_perms
        dir_perms=$(stat -c '%a' /root/.ssh 2>/dev/null)
        if [ "$dir_perms" != "700" ]; then
            print_fail "Permissions de /root/.ssh: $dir_perms (attendu: 700)"
            perms_ok=false
        fi
    else
        print_fail "Dossier /root/.ssh non trouvé"
        perms_ok=false
    fi
    if [ -f "/root/.ssh/id_ed25519" ]; then
        local key_perms
        key_perms=$(stat -c '%a' /root/.ssh/id_ed25519 2>/dev/null)
        if [ "$key_perms" != "600" ]; then
            print_fail "Permissions de la clé privée: $key_perms (attendu: 600)"
            perms_ok=false
        fi
    else
        print_fail "Clé privée non trouvée — faites d'abord l'exercice 22.1"
        perms_ok=false
    fi
    if $perms_ok; then
        print_success "Permissions SSH correctes (.ssh=700, clé privée=600)"
        add_score "22.2" 3
    else
        print_hint "chmod 700 /root/.ssh && chmod 600 /root/.ssh/id_ed25519"
    fi

    # 22.3
    echo -e "  ${BOLD}Exercice 22.3${NC} - Configuration SSH"
    if [ -f "/root/.ssh/config" ]; then
        local has_host has_hostname has_user
        has_host=$(grep -ci "Host serveur-test" /root/.ssh/config 2>/dev/null)
        has_hostname=$(grep -ci "HostName.*ssh-target" /root/.ssh/config 2>/dev/null)
        has_user=$(grep -ci "User.*etudiant" /root/.ssh/config 2>/dev/null)
        if [ "$has_host" -ge 1 ] && [ "$has_hostname" -ge 1 ] && [ "$has_user" -ge 1 ]; then
            print_success "Configuration SSH avec alias serveur-test"
            add_score "22.3" 3
        else
            [ "$has_host" -lt 1 ] && print_fail "Alias 'Host serveur-test' manquant"
            [ "$has_hostname" -lt 1 ] && print_fail "HostName ssh-target manquant"
            [ "$has_user" -lt 1 ] && print_fail "User etudiant manquant"
            print_hint "Créez le fichier avec Host serveur-test, HostName ssh-target, User etudiant"
        fi
    else
        print_fail "Fichier /root/.ssh/config non trouvé"
        print_hint "nano /root/.ssh/config"
    fi

    # 22.4
    echo -e "  ${BOLD}Exercice 22.4${NC} - Clé publique dans authorized_keys"
    if [ -f "/root/.ssh/authorized_keys" ]; then
        local ak_perms
        ak_perms=$(stat -c '%a' /root/.ssh/authorized_keys 2>/dev/null)
        if grep -q "ssh-ed25519" /root/.ssh/authorized_keys 2>/dev/null; then
            if [ "$ak_perms" = "600" ]; then
                print_success "Clé publique ajoutée à authorized_keys (permissions 600)"
                add_score "22.4" 3
            else
                print_fail "Permissions de authorized_keys: $ak_perms (attendu: 600)"
                print_hint "chmod 600 /root/.ssh/authorized_keys"
            fi
        else
            print_fail "authorized_keys ne contient pas de clé ed25519"
            print_hint "cat /root/.ssh/id_ed25519.pub >> /root/.ssh/authorized_keys"
        fi
    else
        print_fail "Fichier /root/.ssh/authorized_keys non trouvé"
        print_hint "cat /root/.ssh/id_ed25519.pub >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys"
    fi

    # 22.5
    echo -e "  ${BOLD}Exercice 22.5${NC} - Connexion SSH réelle"
    if [ -f "/root/ssh-test.txt" ]; then
        if grep -q "CONNEXION_REUSSIE" /root/ssh-test.txt 2>/dev/null; then
            print_success "Connexion SSH au serveur distant réussie !"
            add_score "22.5" 4
        else
            print_fail "Le fichier /root/ssh-test.txt ne contient pas la preuve de connexion"
            print_hint "sshpass -p 'etudiant' ssh -o StrictHostKeyChecking=no etudiant@ssh-target > /root/ssh-test.txt"
        fi
    else
        print_fail "Fichier /root/ssh-test.txt non trouvé"
        print_hint "Connectez-vous à ssh-target et redirigez la sortie : sshpass -p 'etudiant' ssh -o StrictHostKeyChecking=no etudiant@ssh-target > /root/ssh-test.txt"
    fi
}
