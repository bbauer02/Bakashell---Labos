#!/bin/bash
# === ÉTAPE 19 : Exercice d'intégration finale - Serveur web ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 5; }
get_step_exercise_ids() { echo "19.1 19.2 19.3 19.4 19.5"; }

show_step_exercises() {
    print_step_header 19 "Intégration finale : Administrer un serveur web"

    echo -e "  ${CYAN}Scénario :${NC} Vous configurez un serveur web pour une entreprise."
    echo ""

    print_exercise "19.1" 4 "Créez un utilisateur ${BOLD}webmaster${NC} et un groupe ${BOLD}www${NC}.\n     Ajoutez webmaster au groupe www.\n     Créez l'arborescence ${BOLD}/var/www/monsite/${NC} avec les\n     sous-dossiers ${BOLD}html${NC}, ${BOLD}logs${NC} et ${BOLD}backup${NC}.\n     Le dossier /var/www/monsite doit appartenir au groupe ${BOLD}www${NC}\n     avec les permissions ${BOLD}775${NC}."
    print_exercise "19.2" 4 "Créez ${BOLD}/var/www/monsite/html/index.html${NC} contenant\n     ${BOLD}\"<h1>Bienvenue</h1>\"${NC}.\n     Créez ${BOLD}/var/www/monsite/logs/access.log${NC} avec au moins\n     5 lignes simulant des logs (ex: GET /page 200)."
    print_exercise "19.3" 4 "Écrivez un script ${BOLD}/home/webmaster/backup.sh${NC} exécutable qui :\n     - Crée une archive tar.gz du dossier html dans backup/\n     - Sauvegarde le résultat de df -h dans backup/disk-report.txt\n     Puis exécutez-le."
    print_exercise "19.4" 4 "Créez un fichier cron ${BOLD}/etc/cron.d/backup-web${NC} qui planifie\n     l'exécution de ${BOLD}/home/webmaster/backup.sh${NC}\n     tous les jours à ${BOLD}3h du matin${NC}.\n     ${DIM}(format: 0 3 * * * root /home/webmaster/backup.sh)${NC}"
    print_exercise "19.5" 4 "Créez un script ${BOLD}/home/webmaster/monitoring.sh${NC} exécutable\n     qui génère un rapport avec : date, espace disque,\n     mémoire et nombre de processus.\n     Le rapport doit être sauvegardé dans\n     ${BOLD}/var/www/monsite/logs/monitoring.txt${NC}.\n     Puis exécutez-le."

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 19${NC}"
}

run_validations() {
    print_step_header 19 "Validation - Intégration finale"

    # 19.1
    echo -e "  ${BOLD}Exercice 19.1${NC} - Environnement serveur web"
    local ex1_ok=true
    if ! id webmaster > /dev/null 2>&1; then
        print_fail "Utilisateur webmaster non trouvé"
        ex1_ok=false
    fi
    if ! getent group www > /dev/null 2>&1; then
        print_fail "Groupe www non trouvé"
        ex1_ok=false
    fi
    if $ex1_ok && ! id webmaster 2>/dev/null | grep -q "www"; then
        print_fail "webmaster n'est pas dans le groupe www"
        ex1_ok=false
    fi
    for dir in html logs backup; do
        if [ ! -d "/var/www/monsite/$dir" ]; then
            print_fail "Dossier /var/www/monsite/$dir manquant"
            ex1_ok=false
        fi
    done
    if $ex1_ok; then
        local grp perms
        grp=$(stat -c '%G' /var/www/monsite 2>/dev/null)
        perms=$(stat -c '%a' /var/www/monsite 2>/dev/null)
        if [ "$grp" = "www" ] && [ "$perms" = "775" ]; then
            print_success "Environnement web configuré (webmaster, www, arborescence, permissions)"
            add_score "19.1" 4
        else
            [ "$grp" != "www" ] && print_fail "Groupe de /var/www/monsite: $grp (attendu: www)"
            [ "$perms" != "775" ] && print_fail "Permissions de /var/www/monsite: $perms (attendu: 775)"
        fi
    fi

    # 19.2
    echo -e "  ${BOLD}Exercice 19.2${NC} - Contenu web et logs"
    local ex2_ok=true
    if [ -f "/var/www/monsite/html/index.html" ]; then
        if ! grep -qi "bienvenue" /var/www/monsite/html/index.html 2>/dev/null; then
            print_fail "index.html ne contient pas 'Bienvenue'"
            ex2_ok=false
        fi
    else
        print_fail "Fichier /var/www/monsite/html/index.html non trouvé"
        ex2_ok=false
    fi
    if [ -f "/var/www/monsite/logs/access.log" ]; then
        local log_lines
        log_lines=$(wc -l < /var/www/monsite/logs/access.log)
        if [ "$log_lines" -lt 5 ]; then
            print_fail "access.log doit contenir au moins 5 lignes ($log_lines actuellement)"
            ex2_ok=false
        fi
    else
        print_fail "Fichier /var/www/monsite/logs/access.log non trouvé"
        ex2_ok=false
    fi
    if $ex2_ok; then
        print_success "Contenu web et logs créés"
        add_score "19.2" 4
    fi

    # 19.3
    echo -e "  ${BOLD}Exercice 19.3${NC} - Script de sauvegarde"
    if [ -f "/home/webmaster/backup.sh" ] && [ -x "/home/webmaster/backup.sh" ]; then
        local has_tar has_df
        has_tar=$(grep -c "tar" /home/webmaster/backup.sh 2>/dev/null)
        has_df=$(grep -c "df" /home/webmaster/backup.sh 2>/dev/null)
        if [ "$has_tar" -ge 1 ] && [ "$has_df" -ge 1 ]; then
            # Vérifier que le script a été exécuté
            local backup_found=false
            if ls /var/www/monsite/backup/*.tar.gz 1>/dev/null 2>&1; then
                backup_found=true
            fi
            if [ -f "/var/www/monsite/backup/disk-report.txt" ] && $backup_found; then
                print_success "Script de sauvegarde fonctionnel (archive + rapport disque)"
                add_score "19.3" 4
            else
                $backup_found || print_fail "Aucune archive .tar.gz trouvée dans backup/"
                [ ! -f "/var/www/monsite/backup/disk-report.txt" ] && print_fail "disk-report.txt non trouvé dans backup/"
                print_hint "Exécutez votre script : /home/webmaster/backup.sh"
            fi
        else
            print_fail "Le script doit contenir tar (archive) et df (rapport disque)"
        fi
    else
        [ ! -f "/home/webmaster/backup.sh" ] && print_fail "Script /home/webmaster/backup.sh non trouvé"
        [ -f "/home/webmaster/backup.sh" ] && [ ! -x "/home/webmaster/backup.sh" ] && print_fail "Le script n'est pas exécutable"
    fi

    # 19.4
    echo -e "  ${BOLD}Exercice 19.4${NC} - Tâche cron de sauvegarde"
    if [ -f "/etc/cron.d/backup-web" ]; then
        if grep -qE "^0\s+3\s+.*backup\.sh" /etc/cron.d/backup-web 2>/dev/null; then
            print_success "Tâche cron configurée (sauvegarde à 3h)"
            add_score "19.4" 4
        else
            print_fail "La tâche cron n'a pas le bon format"
            print_hint "echo '0 3 * * * root /home/webmaster/backup.sh' > /etc/cron.d/backup-web"
        fi
    else
        print_fail "Fichier /etc/cron.d/backup-web non trouvé"
        print_hint "echo '0 3 * * * root /home/webmaster/backup.sh' > /etc/cron.d/backup-web"
    fi

    # 19.5
    echo -e "  ${BOLD}Exercice 19.5${NC} - Script de monitoring"
    if [ -f "/home/webmaster/monitoring.sh" ] && [ -x "/home/webmaster/monitoring.sh" ]; then
        if [ -f "/var/www/monsite/logs/monitoring.txt" ]; then
            local has_disk has_mem
            has_disk=$(grep -cEi "(Filesystem|Sys\.fich\.|tmpfs|\/dev\/)" /var/www/monsite/logs/monitoring.txt 2>/dev/null)
            has_mem=$(grep -cEi "(Mem|Swap)" /var/www/monsite/logs/monitoring.txt 2>/dev/null)
            if [ "$has_disk" -ge 1 ] && [ "$has_mem" -ge 1 ]; then
                print_success "Rapport de monitoring complet généré"
                add_score "19.5" 4
            else
                print_fail "Le rapport ne contient pas toutes les informations"
                print_hint "Le script doit inclure date, df -h, free -h et ps aux"
            fi
        else
            print_fail "Fichier /var/www/monsite/logs/monitoring.txt non trouvé"
            print_hint "Exécutez votre script : /home/webmaster/monitoring.sh"
        fi
    else
        [ ! -f "/home/webmaster/monitoring.sh" ] && print_fail "Script /home/webmaster/monitoring.sh non trouvé"
        [ -f "/home/webmaster/monitoring.sh" ] && [ ! -x "/home/webmaster/monitoring.sh" ] && print_fail "Le script n'est pas exécutable"
    fi
}
