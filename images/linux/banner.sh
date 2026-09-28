# Message d'accueil, uniquement dans un vrai terminal
if [ -t 1 ] && [ "$(id -un)" = "etudiant" ] && [ -z "$LAB_BANNER_SHOWN" ]; then
    export LAB_BANNER_SHOWN=1
    printf '\n  \033[1;36mLinux CLI Lab\033[0m — vous êtes connecté en tant que \033[1metudiant\033[0m.\n'
    printf '  Les commandes d'"'"'administration passent par \033[1msudo\033[0m (mot de passe : etudiant).\n\n'
fi
