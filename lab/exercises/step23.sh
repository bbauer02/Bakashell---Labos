#!/bin/bash
# === ÉTAPE 23 : Gestion des logs ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 4; }
get_step_exercise_ids() { echo "23.1 23.2 23.3 23.4"; }

show_step_exercises() {
    print_step_header 23 "Gestion des logs"

    print_exercise "23.1" 3 "Listez tous les fichiers de log dans ${BOLD}/var/log/${NC}\n     et sauvegardez le résultat dans\n     ${BOLD}/home/etudiant/liste-logs.txt${NC}\n     ${DIM}(ls -la /var/log/)${NC}"
    print_exercise "23.2" 3 "Créez un faux fichier de log ${BOLD}/var/log/app-test.log${NC}\n     contenant au moins 10 lignes horodatées au format :\n     ${BOLD}2026-03-30 10:00:00 INFO Message${NC}\n     Incluez au moins 2 lignes ${BOLD}ERROR${NC} et 2 lignes ${BOLD}WARNING${NC}."
    print_exercise "23.3" 3 "Extrayez uniquement les lignes ${BOLD}ERROR${NC} de votre log\n     et sauvegardez dans ${BOLD}/home/etudiant/errors.txt${NC}.\n     Comptez le nombre d'erreurs et sauvegardez dans\n     ${BOLD}/home/etudiant/error-count.txt${NC}"
    print_exercise "23.4" 3 "Créez un script ${BOLD}/home/etudiant/log-analyzer.sh${NC}\n     exécutable qui analyse ${BOLD}/var/log/app-test.log${NC} et\n     produit un résumé dans ${BOLD}/home/etudiant/log-summary.txt${NC}\n     contenant le nombre de lignes INFO, WARNING et ERROR.\n     Puis exécutez-le."

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 23${NC}"
}

run_validations() {
    print_step_header 23 "Validation - Gestion des logs"

    # 23.1
    echo -e "  ${BOLD}Exercice 23.1${NC} - Liste des fichiers de log"
    if [ -f "/home/etudiant/liste-logs.txt" ]; then
        if grep -qE "(syslog|dpkg|log)" /home/etudiant/liste-logs.txt 2>/dev/null; then
            print_success "Liste des logs sauvegardée"
            add_score "23.1" 3
        else
            print_fail "Le fichier ne semble pas contenir un listing de /var/log/"
            print_hint "ls -la /var/log/ > /home/etudiant/liste-logs.txt"
        fi
    else
        print_fail "Fichier /home/etudiant/liste-logs.txt non trouvé"
        print_hint "ls -la /var/log/ > /home/etudiant/liste-logs.txt"
    fi

    # 23.2
    echo -e "  ${BOLD}Exercice 23.2${NC} - Fichier de log simulé"
    if [ -f "/var/log/app-test.log" ]; then
        local total_lines errors warnings
        total_lines=$(wc -l < /var/log/app-test.log)
        errors=$(grep -c "ERROR" /var/log/app-test.log 2>/dev/null)
        warnings=$(grep -c "WARNING" /var/log/app-test.log 2>/dev/null)
        if [ "$total_lines" -ge 10 ] && [ "$errors" -ge 2 ] && [ "$warnings" -ge 2 ]; then
            if grep -qE "^[0-9]{4}-[0-9]{2}-[0-9]{2}" /var/log/app-test.log 2>/dev/null; then
                print_success "Log simulé créé ($total_lines lignes, $errors erreurs, $warnings warnings)"
                add_score "23.2" 3
            else
                print_fail "Les lignes ne sont pas horodatées (format: 2026-03-30 10:00:00)"
            fi
        else
            [ "$total_lines" -lt 10 ] && print_fail "Le fichier doit contenir au moins 10 lignes ($total_lines actuellement)"
            [ "$errors" -lt 2 ] && print_fail "Le fichier doit contenir au moins 2 lignes ERROR ($errors actuellement)"
            [ "$warnings" -lt 2 ] && print_fail "Le fichier doit contenir au moins 2 lignes WARNING ($warnings actuellement)"
        fi
    else
        print_fail "Fichier /var/log/app-test.log non trouvé"
    fi

    # 23.3
    echo -e "  ${BOLD}Exercice 23.3${NC} - Extraction des erreurs"
    local ex3_ok=true
    if [ -f "/home/etudiant/errors.txt" ]; then
        if grep -q "ERROR" /home/etudiant/errors.txt 2>/dev/null; then
            # Vérifier qu'il n'y a que des lignes ERROR
            local non_error
            non_error=$(grep -cv "ERROR" /home/etudiant/errors.txt 2>/dev/null)
            if [ "$non_error" -gt 0 ]; then
                print_fail "errors.txt contient des lignes sans ERROR"
                ex3_ok=false
            fi
        else
            print_fail "errors.txt ne contient pas de lignes ERROR"
            ex3_ok=false
        fi
    else
        print_fail "Fichier /home/etudiant/errors.txt non trouvé"
        ex3_ok=false
    fi
    if [ -f "/home/etudiant/error-count.txt" ]; then
        if [ -s "/home/etudiant/error-count.txt" ]; then
            local count
            count=$(cat /home/etudiant/error-count.txt | tr -d '[:space:]')
            if [[ "$count" =~ ^[0-9]+$ ]] && [ "$count" -ge 2 ]; then
                :  # ok
            else
                print_fail "error-count.txt ne contient pas un nombre valide (>= 2)"
                ex3_ok=false
            fi
        else
            print_fail "error-count.txt est vide"
            ex3_ok=false
        fi
    else
        print_fail "Fichier /home/etudiant/error-count.txt non trouvé"
        ex3_ok=false
    fi
    if $ex3_ok; then
        print_success "Erreurs extraites et comptées"
        add_score "23.3" 3
    else
        print_hint "grep ERROR /var/log/app-test.log > errors.txt && grep -c ERROR /var/log/app-test.log > error-count.txt"
    fi

    # 23.4
    echo -e "  ${BOLD}Exercice 23.4${NC} - Script d'analyse de logs"
    if [ -f "/home/etudiant/log-analyzer.sh" ] && [ -x "/home/etudiant/log-analyzer.sh" ]; then
        if [ -f "/home/etudiant/log-summary.txt" ]; then
            local has_info has_warn has_err
            has_info=$(grep -ci "INFO" /home/etudiant/log-summary.txt 2>/dev/null)
            has_warn=$(grep -ci "WARNING" /home/etudiant/log-summary.txt 2>/dev/null)
            has_err=$(grep -ci "ERROR" /home/etudiant/log-summary.txt 2>/dev/null)
            if [ "$has_info" -ge 1 ] && [ "$has_warn" -ge 1 ] && [ "$has_err" -ge 1 ]; then
                print_success "Script d'analyse fonctionnel — résumé avec INFO/WARNING/ERROR"
                add_score "23.4" 3
            else
                print_fail "Le résumé ne contient pas les 3 niveaux (INFO, WARNING, ERROR)"
                print_hint "Le script doit compter et afficher les lignes INFO, WARNING et ERROR"
            fi
        else
            print_fail "Fichier /home/etudiant/log-summary.txt non trouvé"
            print_hint "Exécutez votre script : ./log-analyzer.sh"
        fi
    else
        [ ! -f "/home/etudiant/log-analyzer.sh" ] && print_fail "Script log-analyzer.sh non trouvé"
        [ -f "/home/etudiant/log-analyzer.sh" ] && [ ! -x "/home/etudiant/log-analyzer.sh" ] && print_fail "Le script n'est pas exécutable"
    fi
}
