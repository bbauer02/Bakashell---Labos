# Message d'accueil, uniquement dans un vrai terminal
if [ -t 1 ] && [ "$(id -un)" = "etudiant" ] && [ -z "$LAB_BANNER_SHOWN" ]; then
    export LAB_BANNER_SHOWN=1
    printf '\n  \033[1;36mProjet final\033[0m — épreuve notée, sur le poste de contrôle \033[1mcontrole\033[0m.\n'
    if [ ! -f /run/lab-ready ]; then
        printf '  \033[33mLes serveurs démarrent (premier lancement : environ 30 s)…\033[0m\n'
    fi
    printf '  Tickets : \033[1m~/tickets\033[0m · API : \033[1m~/boutique\033[0m · dépôt partagé : \033[1m/srv/git/boutique.git\033[0m · Ansible : \033[1m~/infra\033[0m\n'
    printf '  Serveurs : \033[1mci1\033[0m (Docker, déjà configuré), \033[1mweb1\033[0m, \033[1mweb2\033[0m, \033[1mweb3\033[0m (SSH, compte admin).\n\n'
fi

if [ -n "$BASH_VERSION" ]; then
    PS1='\[\e[1;32m\]\u@controle\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\$ '
fi
