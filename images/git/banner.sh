# Message d'accueil, uniquement dans un vrai terminal
if [ -t 1 ] && [ "$(id -un)" = "etudiant" ] && [ -z "$LAB_BANNER_SHOWN" ]; then
    export LAB_BANNER_SHOWN=1
    printf '\n  \033[1;36mParcours Git\033[0m — vous êtes connecté en tant que \033[1metudiant\033[0m.\n'
    printf '  Le dépôt partagé de l'"'"'équipe est sur ce serveur : \033[1m/srv/git\033[0m.\n\n'
fi
