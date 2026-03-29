#!/bin/bash
# === ÉTAPE 3 : Créer, écrire, gérer fichiers et dossiers ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 5; }
get_step_exercise_ids() { echo "3.1 3.2 3.3 3.4 3.5"; }

show_step_exercises() {
    print_step_header 3 "Créer, écrire, gérer fichiers et dossiers"

    print_exercise "3.1" 3 "Créez l'arborescence suivante dans /home/etudiant :\n     ${BOLD}documents/cours/${NC} et ${BOLD}documents/exercices/${NC}"
    print_exercise "3.2" 3 "Créez un fichier ${BOLD}documents/cours/notes.txt${NC} contenant\n     le texte ${BOLD}\"Bienvenue dans le cours Linux\"${NC}"
    print_exercise "3.3" 3 "Copiez ${BOLD}notes.txt${NC} dans ${BOLD}documents/exercices/${NC}"
    print_exercise "3.4" 3 "Renommez la copie en ${BOLD}documents/exercices/notes-copie.txt${NC}"
    print_exercise "3.5" 3 "Ajoutez une 2ème ligne ${BOLD}\"Ceci est un ajout\"${NC} à\n     ${BOLD}documents/cours/notes.txt${NC} (sans écraser la 1ère ligne)"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 3${NC}"
}

run_validations() {
    print_step_header 3 "Validation - Fichiers et dossiers"

    # 3.1
    echo -e "  ${BOLD}Exercice 3.1${NC} - Arborescence documents"
    if [ -d "/home/etudiant/documents/cours" ] && [ -d "/home/etudiant/documents/exercices" ]; then
        print_success "Arborescence documents/cours et documents/exercices créée"
        add_score "3.1" 3
    else
        print_fail "Arborescence incomplète"
        print_hint "mkdir -p /home/etudiant/documents/cours /home/etudiant/documents/exercices"
    fi

    # 3.2
    echo -e "  ${BOLD}Exercice 3.2${NC} - Fichier notes.txt avec contenu"
    if [ -f "/home/etudiant/documents/cours/notes.txt" ]; then
        if grep -qi "bienvenue" "/home/etudiant/documents/cours/notes.txt" 2>/dev/null; then
            print_success "notes.txt contient le message de bienvenue"
            add_score "3.2" 3
        else
            print_fail "notes.txt ne contient pas le bon texte"
            print_hint "echo \"Bienvenue dans le cours Linux\" > /home/etudiant/documents/cours/notes.txt"
        fi
    else
        print_fail "Fichier notes.txt non trouvé"
    fi

    # 3.3
    echo -e "  ${BOLD}Exercice 3.3${NC} - Copie de notes.txt"
    if [ -f "/home/etudiant/documents/exercices/notes.txt" ] || [ -f "/home/etudiant/documents/exercices/notes-copie.txt" ]; then
        print_success "Copie trouvée dans documents/exercices/"
        add_score "3.3" 3
    else
        print_fail "Aucune copie dans documents/exercices/"
        print_hint "cp /home/etudiant/documents/cours/notes.txt /home/etudiant/documents/exercices/"
    fi

    # 3.4
    echo -e "  ${BOLD}Exercice 3.4${NC} - Renommage en notes-copie.txt"
    if [ -f "/home/etudiant/documents/exercices/notes-copie.txt" ]; then
        print_success "Fichier renommé en notes-copie.txt"
        add_score "3.4" 3
    else
        print_fail "Fichier notes-copie.txt non trouvé"
        print_hint "mv /home/etudiant/documents/exercices/notes.txt /home/etudiant/documents/exercices/notes-copie.txt"
    fi

    # 3.5
    echo -e "  ${BOLD}Exercice 3.5${NC} - Ajout d'une ligne (>>)"
    if [ -f "/home/etudiant/documents/cours/notes.txt" ]; then
        local lines
        lines=$(wc -l < "/home/etudiant/documents/cours/notes.txt")
        if [ "$lines" -ge 2 ] && grep -qi "ajout" "/home/etudiant/documents/cours/notes.txt" 2>/dev/null; then
            print_success "Deuxième ligne ajoutée avec >> correctement"
            add_score "3.5" 3
        else
            print_fail "Le fichier ne contient pas 2 lignes ou manque 'ajout'"
            print_hint "echo \"Ceci est un ajout\" >> /home/etudiant/documents/cours/notes.txt"
        fi
    else
        print_fail "Fichier notes.txt non trouvé"
    fi
}
