#!/bin/bash
# === ÉTAPE 13 : Réseau de base ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "13.1 13.2 13.3 13.4"; }

show_step_exercises() {
    print_step_header 13 "Réseau de base"

    print_exercise "13.1" 3 "Affichez les informations réseau de la machine et sauvegardez\n     dans ${BOLD}/home/etudiant/network-info.txt${NC}\n     ${DIM}(utilisez ip a ou hostname -I)${NC}"
    print_exercise "13.2" 3 "Sauvegardez le nom de la machine (hostname) dans\n     ${BOLD}/home/etudiant/hostname.txt${NC}"
    print_exercise "13.3" 3 "Affichez les ports en écoute et sauvegardez le résultat\n     dans ${BOLD}/home/etudiant/ports.txt${NC}\n     ${DIM}(utilisez ss -tuln ou netstat -tuln)${NC}"
    print_exercise "13.4" 3 "Ajoutez une entrée dans ${BOLD}/etc/hosts${NC} qui associe\n     l'IP ${BOLD}192.168.1.100${NC} au nom ${BOLD}serveur-local${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 13${NC}"
}

run_validations() {
    print_step_header 13 "Validation - Réseau de base"

    # 13.1
    echo -e "  ${BOLD}Exercice 13.1${NC} - Informations réseau"
    if [ -f "/home/etudiant/network-info.txt" ]; then
        if [ -s "/home/etudiant/network-info.txt" ]; then
            print_success "Informations réseau sauvegardées"
            add_score "13.1" 3
        else
            print_fail "Le fichier est vide"
            print_hint "ip a > /home/etudiant/network-info.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/network-info.txt non trouvé"
        print_hint "ip a > /home/etudiant/network-info.txt"
    fi

    # 13.2
    echo -e "  ${BOLD}Exercice 13.2${NC} - Hostname"
    if [ -f "/home/etudiant/hostname.txt" ]; then
        if [ -s "/home/etudiant/hostname.txt" ]; then
            print_success "Hostname sauvegardé ($(cat /home/etudiant/hostname.txt | head -1))"
            add_score "13.2" 3
        else
            print_fail "Le fichier est vide"
            print_hint "hostname > /home/etudiant/hostname.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/hostname.txt non trouvé"
        print_hint "hostname > /home/etudiant/hostname.txt"
    fi

    # 13.3
    echo -e "  ${BOLD}Exercice 13.3${NC} - Ports en écoute"
    if [ -f "/home/etudiant/ports.txt" ]; then
        if [ -s "/home/etudiant/ports.txt" ]; then
            print_success "Liste des ports sauvegardée"
            add_score "13.3" 3
        else
            print_fail "Le fichier est vide"
            print_hint "ss -tuln > /home/etudiant/ports.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/ports.txt non trouvé"
        print_hint "ss -tuln > /home/etudiant/ports.txt"
    fi

    # 13.4
    echo -e "  ${BOLD}Exercice 13.4${NC} - Entrée dans /etc/hosts"
    if grep -q "192.168.1.100" /etc/hosts 2>/dev/null; then
        if grep "192.168.1.100" /etc/hosts | grep -q "serveur-local"; then
            print_success "Entrée 192.168.1.100 serveur-local ajoutée dans /etc/hosts"
            add_score "13.4" 3
        else
            print_fail "L'IP 192.168.1.100 est présente mais pas associée à serveur-local"
            print_hint "echo '192.168.1.100 serveur-local' >> /etc/hosts"
        fi
    else
        print_fail "Entrée 192.168.1.100 non trouvée dans /etc/hosts"
        print_hint "echo '192.168.1.100 serveur-local' >> /etc/hosts"
    fi
}
