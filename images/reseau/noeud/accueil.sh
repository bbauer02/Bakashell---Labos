# Message d'accueil sur une machine du réseau, uniquement dans un vrai terminal (nom dans la couleur de la machine)
if [ -t 1 ] && [ -z "$LAB_ACCUEIL" ]; then
    export LAB_ACCUEIL=1
    printf '\n  Vous êtes sur \033[1;38;2;%sm%s\033[0m (compte root). Tapez \033[1mexit\033[0m pour revenir à la console.\n\n' \
        "${LAB_COULEUR:-248;113;113}" "$(hostname)"
fi
