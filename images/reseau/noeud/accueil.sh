# Message d'accueil sur une machine du réseau, uniquement dans un vrai terminal
if [ -t 1 ] && [ -z "$LAB_ACCUEIL" ]; then
    export LAB_ACCUEIL=1
    printf '\n  Vous êtes sur \033[1;31m%s\033[0m (compte root). Tapez \033[1mexit\033[0m pour revenir à la console.\n\n' "$(hostname)"
fi
