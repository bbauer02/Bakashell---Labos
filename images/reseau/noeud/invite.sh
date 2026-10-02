# Invite de la machine dans sa couleur : LAB_COULEUR (« r;g;b ») est transmise par la console à la connexion, et
# c'est aussi la couleur de l'onglet de la machine dans la page du labo. Rouge à défaut.
_c=${LAB_COULEUR:-248;113;113}
PS1="\[\e[1;38;2;${_c}m\]root@\h\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]# "
unset _c
