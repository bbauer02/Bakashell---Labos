#!/bin/sh
# Page d'accueil de l'intranet de Cimes & Sentiers, générée à chaque visite.
# Chaque réponse porte une référence unique ; son empreinte est notée dans /var/lib/depot-intranet/visites.

if [ "${REQUEST_URI%%\?*}" != "/" ]; then
    printf 'HTTP/1.0 404 Not Found\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nPage introuvable.\n'
    exit 0
fi

ref=$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')
t=$(mktemp) || exit 1
cat > "$t" <<EOF
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Intranet — Cimes &amp; Sentiers</title>
</head>
<body>
<h1>Intranet de Cimes &amp; Sentiers</h1>
<p>Bienvenue sur l'intranet de l'équipe. Matériel de randonnée, bonne humeur et serveurs bien rangés.</p>
<h2>Services internes</h2>
<ul>
<li>Miroir des paquets Ubuntu : <a href="http://depot.cimes.lan/ubuntu/">depot.cimes.lan</a></li>
<li>Boutique en ligne (préproduction) : demander l'accès à Thomas</li>
<li>Astreinte de la semaine : voir le planning affiché au bureau</li>
</ul>
<p>Page générée le $(date '+%d/%m/%Y à %H:%M:%S'), référence $ref.</p>
</body>
</html>
EOF
echo "$(date '+%F %T') $(sha256sum < "$t" | cut -d' ' -f1) ${HTTP_USER_AGENT:-?}" >> /var/lib/depot-intranet/visites
printf 'Content-Type: text/html; charset=utf-8\r\n\r\n'
cat "$t"
rm -f "$t"
