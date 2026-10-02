# Message d'accueil, uniquement dans un vrai terminal
if [ -t 1 ] && [ "$(id -un)" = "etudiant" ] && [ -z "$LAB_BANNER_SHOWN" ]; then
    export LAB_BANNER_SHOWN=1
    printf '\n  \033[1;36mParcours Réseau\033[0m — vous êtes sur la \033[1mconsole\033[0m du technicien.\n'
    if [ ! -f /run/lab-ready ]; then
        printf '  \033[33mLe réseau démarre (premier lancement : environ 30 s)…\033[0m\n'
    fi
    printf '  \033[1mplan\033[0m : le schéma du réseau · \033[1mconnexion <machine>\033[0m : travailler sur une machine (\033[1mexit\033[0m pour revenir)\n\n'
fi

if [ -n "$BASH_VERSION" ]; then
    PS1='\[\e[1;32m\]\u@console\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\$ '
fi
