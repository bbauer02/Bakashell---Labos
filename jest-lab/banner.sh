# Message d'accueil, uniquement dans un vrai terminal
if [ -t 1 ] && [ "$(id -un)" = "etudiant" ] && [ -z "$LAB_BANNER_SHOWN" ]; then
    export LAB_BANNER_SHOWN=1
    printf '\n  \033[1;36mParcours Jest\033[0m — le projet est dans \033[1m~/boutique\033[0m.\n'
    printf '  Lancez les tests avec \033[1mnpx jest\033[0m (ou \033[1mnpm test\033[0m une fois le script configuré).\n\n'
    cd ~/boutique 2>/dev/null || true
fi
