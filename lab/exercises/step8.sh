#!/bin/bash
# === ÉTAPE 8 : Montage et systèmes de fichiers ===
source /opt/linux-lab/utils.sh

get_step_total() { echo 2; }
get_step_exercise_ids() { echo "8.1 8.2"; }

show_step_exercises() {
    print_step_header 8 "Montage et systèmes de fichiers"

    print_exercise "8.1" 4 "Listez les périphériques bloc disponibles et sauvegardez\n     le résultat dans ${BOLD}/home/etudiant/devices.txt${NC}\n     ${DIM}(utilisez : lsblk ou ls -l /dev/sd* ou cat /proc/partitions)${NC}"
    print_exercise "8.2" 4 "Créez un point de montage ${BOLD}/mnt/usb${NC} et créez-y un fichier\n     ${BOLD}/mnt/usb/readme.txt${NC} contenant ${BOLD}\"Point de montage prêt\"${NC}.\n     ${DIM}(Simulation : pas de vrai USB dans un container)${NC}"

    print_info "Quand vous avez terminé, tapez : ${BOLD}check 8${NC}"
}

run_validations() {
    print_step_header 8 "Validation - Montage et systèmes de fichiers"

    # 8.1
    echo -e "  ${BOLD}Exercice 8.1${NC} - Liste des périphériques"
    if [ -f "/home/etudiant/devices.txt" ]; then
        if [ -s "/home/etudiant/devices.txt" ]; then
            print_success "Liste des périphériques sauvegardée"
            add_score "8.1" 4
        else
            print_fail "Le fichier devices.txt est vide"
        fi
    else
        print_fail "Fichier /home/etudiant/devices.txt non trouvé"
        print_hint "lsblk > /home/etudiant/devices.txt ou cat /proc/partitions > /home/etudiant/devices.txt"
    fi

    # 8.2
    echo -e "  ${BOLD}Exercice 8.2${NC} - Point de montage /mnt/usb"
    if [ -d "/mnt/usb" ]; then
        if [ -f "/mnt/usb/readme.txt" ]; then
            if grep -qi "point de montage" "/mnt/usb/readme.txt" 2>/dev/null; then
                print_success "Point de montage créé avec readme.txt"
                add_score "8.2" 4
            else
                print_fail "readme.txt ne contient pas le bon texte"
                print_hint "echo \"Point de montage prêt\" > /mnt/usb/readme.txt"
            fi
        else
            print_fail "Fichier /mnt/usb/readme.txt non trouvé"
        fi
    else
        print_fail "Dossier /mnt/usb non trouvé"
        print_hint "mkdir -p /mnt/usb"
    fi
}
