#!/bin/bash
# === ÉTAPE 18 : Surveillance du système ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "18.1 18.2 18.3 18.4"; }

show_step_exercises() {
    print_step_header 18 "Surveillance du système"

    print_exercise "18.1" 3 "Affichez l'espace disque et sauvegardez dans\n     ${BOLD}/home/etudiant/disk-usage.txt${NC}\n     ${DIM}(utilisez df -h)${NC}"
    print_exercise "18.2" 3 "Affichez l'utilisation de la mémoire et sauvegardez dans\n     ${BOLD}/home/etudiant/memory.txt${NC}\n     ${DIM}(utilisez free -h)${NC}"
    print_exercise "18.3" 3 "Affichez le temps de fonctionnement du système (uptime)\n     et sauvegardez dans ${BOLD}/home/etudiant/uptime.txt${NC}"
    print_exercise "18.4" 3 "Créez un script ${BOLD}/home/etudiant/rapport.sh${NC} exécutable\n     qui génère un rapport complet (date, uptime, disque, mémoire)\n     et le sauvegarde dans ${BOLD}/home/etudiant/rapport-systeme.txt${NC}\n     Puis exécutez-le."

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 18${NC}"
}

run_validations() {
    print_step_header 18 "Validation - Surveillance du système"

    # 18.1
    echo -e "  ${BOLD}Exercice 18.1${NC} - Espace disque"
    if [ -f "/home/etudiant/disk-usage.txt" ]; then
        if grep -qE "(Filesystem|Sys\.fich\.|tmpfs|\/dev\/)" /home/etudiant/disk-usage.txt 2>/dev/null; then
            print_success "Informations disque sauvegardées"
            add_score "18.1" 3
        else
            print_fail "Le fichier ne contient pas un résultat de df"
            print_hint "df -h > /home/etudiant/disk-usage.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/disk-usage.txt non trouvé"
        print_hint "df -h > /home/etudiant/disk-usage.txt"
    fi

    # 18.2
    echo -e "  ${BOLD}Exercice 18.2${NC} - Mémoire"
    if [ -f "/home/etudiant/memory.txt" ]; then
        if grep -qEi "(Mem|Swap|total)" /home/etudiant/memory.txt 2>/dev/null; then
            print_success "Informations mémoire sauvegardées"
            add_score "18.2" 3
        else
            print_fail "Le fichier ne contient pas un résultat de free"
            print_hint "free -h > /home/etudiant/memory.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/memory.txt non trouvé"
        print_hint "free -h > /home/etudiant/memory.txt"
    fi

    # 18.3
    echo -e "  ${BOLD}Exercice 18.3${NC} - Uptime"
    if [ -f "/home/etudiant/uptime.txt" ]; then
        if grep -qEi "(up|load|average)" /home/etudiant/uptime.txt 2>/dev/null; then
            print_success "Uptime sauvegardé"
            add_score "18.3" 3
        else
            print_fail "Le fichier ne contient pas un résultat de uptime"
            print_hint "uptime > /home/etudiant/uptime.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/uptime.txt non trouvé"
        print_hint "uptime > /home/etudiant/uptime.txt"
    fi

    # 18.4
    echo -e "  ${BOLD}Exercice 18.4${NC} - Script de rapport"
    if [ -f "/home/etudiant/rapport.sh" ]; then
        if [ -x "/home/etudiant/rapport.sh" ]; then
            if [ -f "/home/etudiant/rapport-systeme.txt" ]; then
                local has_disk has_mem has_date
                has_disk=$(grep -cEi "(Filesystem|Sys\.fich\.|tmpfs|\/dev\/)" /home/etudiant/rapport-systeme.txt 2>/dev/null)
                has_mem=$(grep -cEi "(Mem|Swap)" /home/etudiant/rapport-systeme.txt 2>/dev/null)
                has_date=$(grep -cE "[0-9]{4}|[0-9]{2}:[0-9]{2}" /home/etudiant/rapport-systeme.txt 2>/dev/null)
                if [ "$has_disk" -ge 1 ] && [ "$has_mem" -ge 1 ]; then
                    print_success "Rapport système complet généré"
                    add_score "18.4" 3
                else
                    print_fail "Le rapport ne contient pas toutes les informations"
                    print_hint "Le script doit inclure date, uptime, df -h et free -h"
                fi
            else
                print_fail "Le rapport /home/etudiant/rapport-systeme.txt n'existe pas"
                print_hint "Exécutez votre script : ./rapport.sh"
            fi
        else
            print_fail "Le script n'est pas exécutable"
            print_hint "chmod +x /home/etudiant/rapport.sh"
        fi
    else
        print_fail "Script /home/etudiant/rapport.sh non trouvé"
    fi
}
