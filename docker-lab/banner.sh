# Message d'accueil, uniquement dans un vrai terminal
if [ -t 1 ] && [ "$(id -un)" = "etudiant" ] && [ -z "$LAB_BANNER_SHOWN" ]; then
    export LAB_BANNER_SHOWN=1
    printf '\n  \033[1;36mParcours Docker\033[0m — vous disposez de votre propre moteur Docker.\n'
    if [ ! -f /run/lab-ready ]; then
        printf '  \033[33mLe moteur démarre (premier lancement : environ 30 s)…\033[0m\n'
    fi
    printf '  Le projet de la boutique est dans \033[1m~/projet\033[0m.\n\n'
fi

# Invite colorée, comme dans les autres parcours
if [ -n "$BASH_VERSION" ]; then
    PS1='\[\e[1;32m\]\u@\h\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\$ '
fi
