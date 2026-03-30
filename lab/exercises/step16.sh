#!/bin/bash
# === ÉTAPE 16 : Introduction au scripting Bash ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "16.1 16.2 16.3 16.4"; }

show_step_exercises() {
    print_step_header 16 "Introduction au scripting Bash"

    print_exercise "16.1" 3 "Créez un script ${BOLD}/home/etudiant/hello.sh${NC} qui affiche\n     ${BOLD}\"Bonjour depuis mon script !\"${NC}\n     N'oubliez pas le shebang ${BOLD}#!/bin/bash${NC} et rendez-le exécutable."
    print_exercise "16.2" 3 "Créez un script ${BOLD}/home/etudiant/info-system.sh${NC} qui :\n     - Affiche la date du jour\n     - Affiche le nom de l'utilisateur\n     - Affiche le dossier courant\n     ${DIM}(utilisez les commandes date, whoami, pwd)${NC}"
    print_exercise "16.3" 3 "Créez un script ${BOLD}/home/etudiant/check-file.sh${NC} qui prend\n     un argument (un chemin) et affiche ${BOLD}\"EXISTE\"${NC} si le fichier\n     existe ou ${BOLD}\"ABSENT\"${NC} sinon.\n     ${DIM}(utilisez if [ -e \"\$1\" ])${NC}"
    print_exercise "16.4" 3 "Créez un script ${BOLD}/home/etudiant/create-users.sh${NC} qui utilise\n     une boucle ${BOLD}for${NC} pour créer les fichiers\n     ${BOLD}user1.txt, user2.txt, user3.txt, user4.txt, user5.txt${NC}\n     dans ${BOLD}/home/etudiant/users/${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 16${NC}"
}

run_validations() {
    print_step_header 16 "Validation - Scripting Bash"

    # 16.1
    echo -e "  ${BOLD}Exercice 16.1${NC} - Script hello.sh"
    if [ -f "/home/etudiant/hello.sh" ]; then
        if head -1 /home/etudiant/hello.sh | grep -q "#!/bin/bash"; then
            if [ -x "/home/etudiant/hello.sh" ]; then
                local output
                output=$(/home/etudiant/hello.sh 2>/dev/null)
                if echo "$output" | grep -qi "bonjour"; then
                    print_success "hello.sh fonctionne et affiche le message"
                    add_score "16.1" 3
                else
                    print_fail "Le script ne produit pas le bon message"
                    print_hint "Le script doit afficher 'Bonjour depuis mon script !'"
                fi
            else
                print_fail "Le script n'est pas exécutable"
                print_hint "chmod +x /home/etudiant/hello.sh"
            fi
        else
            print_fail "Le script ne commence pas par #!/bin/bash"
            print_hint "La première ligne doit être #!/bin/bash"
        fi
    else
        print_fail "Script /home/etudiant/hello.sh non trouvé"
    fi

    # 16.2
    echo -e "  ${BOLD}Exercice 16.2${NC} - Script info-system.sh"
    if [ -f "/home/etudiant/info-system.sh" ]; then
        if head -1 /home/etudiant/info-system.sh | grep -q "#!/bin/bash"; then
            local has_date has_whoami has_pwd
            has_date=$(grep -c "date" /home/etudiant/info-system.sh 2>/dev/null)
            has_whoami=$(grep -c "whoami" /home/etudiant/info-system.sh 2>/dev/null)
            has_pwd=$(grep -c "pwd" /home/etudiant/info-system.sh 2>/dev/null)
            if [ "$has_date" -ge 1 ] && [ "$has_whoami" -ge 1 ] && [ "$has_pwd" -ge 1 ]; then
                if [ -x "/home/etudiant/info-system.sh" ]; then
                    print_success "Script info-system.sh correctement écrit"
                    add_score "16.2" 3
                else
                    print_fail "Le script n'est pas exécutable"
                    print_hint "chmod +x /home/etudiant/info-system.sh"
                fi
            else
                print_fail "Le script doit utiliser date, whoami et pwd"
                print_hint "Ajoutez les commandes date, whoami et pwd dans le script"
            fi
        else
            print_fail "Le script ne commence pas par #!/bin/bash"
        fi
    else
        print_fail "Script /home/etudiant/info-system.sh non trouvé"
    fi

    # 16.3
    echo -e "  ${BOLD}Exercice 16.3${NC} - Script check-file.sh"
    if [ -f "/home/etudiant/check-file.sh" ]; then
        if [ -x "/home/etudiant/check-file.sh" ]; then
            local out_exists out_absent
            out_exists=$(/home/etudiant/check-file.sh /etc/passwd 2>/dev/null)
            out_absent=$(/home/etudiant/check-file.sh /fichier/inexistant 2>/dev/null)
            if echo "$out_exists" | grep -qi "EXISTE" && echo "$out_absent" | grep -qi "ABSENT"; then
                print_success "check-file.sh fonctionne correctement"
                add_score "16.3" 3
            else
                print_fail "Le script ne produit pas les bonnes sorties"
                print_hint "Testez: ./check-file.sh /etc/passwd → EXISTE, ./check-file.sh /toto → ABSENT"
            fi
        else
            print_fail "Le script n'est pas exécutable"
            print_hint "chmod +x /home/etudiant/check-file.sh"
        fi
    else
        print_fail "Script /home/etudiant/check-file.sh non trouvé"
    fi

    # 16.4
    echo -e "  ${BOLD}Exercice 16.4${NC} - Script create-users.sh avec boucle"
    if [ -f "/home/etudiant/create-users.sh" ]; then
        if grep -q "for" /home/etudiant/create-users.sh 2>/dev/null; then
            if [ -x "/home/etudiant/create-users.sh" ]; then
                # Exécuter le script
                /home/etudiant/create-users.sh 2>/dev/null
                local all_ok=true
                for i in 1 2 3 4 5; do
                    if [ ! -f "/home/etudiant/users/user${i}.txt" ]; then
                        all_ok=false
                        break
                    fi
                done
                if $all_ok; then
                    print_success "Script avec boucle for — 5 fichiers créés"
                    add_score "16.4" 3
                else
                    print_fail "Tous les fichiers user1.txt à user5.txt n'ont pas été créés"
                    print_hint "Le script doit créer /home/etudiant/users/user1.txt à user5.txt"
                fi
            else
                print_fail "Le script n'est pas exécutable"
                print_hint "chmod +x /home/etudiant/create-users.sh"
            fi
        else
            print_fail "Le script ne contient pas de boucle for"
            print_hint "Utilisez : for i in 1 2 3 4 5; do ... done"
        fi
    else
        print_fail "Script /home/etudiant/create-users.sh non trouvé"
    fi
}
