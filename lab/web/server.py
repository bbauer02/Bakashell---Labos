#!/usr/bin/env python3
"""Linux Lab - Web server with WebSocket terminal and validation API."""

import asyncio
import fcntl
import json
import os
import pty
import select
import signal
import struct
import subprocess
import termios

from aiohttp import web, WSMsgType

PROGRESS_FILE = "/opt/linux-lab/data/progress.json"
EXERCISES_DIR = "/opt/linux-lab/exercises"

# ─── Exercise definitions (mirroring the bash scripts) ─────────────────────

STEPS = {
    1: {
        "title": "Premiers pas : navigation dans le système",
        "description": "Découvrez le terminal Linux, naviguez dans l'arborescence et listez les fichiers.",
        "lesson": """
<h3>Bienvenue en console !</h3>
<p>Vous allez apprendre à utiliser l'interface en ligne de commande (CLI) de Linux. Quand vous ouvrez un terminal, vous voyez une ligne comme :</p>
<pre>user@machine:~$</pre>
<p>Cette ligne vous indique <strong>qui vous êtes</strong>, <strong>sur quelle machine</strong> et <strong>où vous vous situez</strong>.</p>

<div class="tip">Le symbole <code>~</code> est un raccourci vers votre dossier personnel <code>/home/user</code>.</div>

<h3>Commandes essentielles</h3>
<ul>
<li><code>whoami</code> — affiche votre nom d'utilisateur</li>
<li><code>pwd</code> — affiche le dossier courant (<em>Print Working Directory</em>)</li>
<li><code>cd &lt;dossier&gt;</code> — se déplacer (<em>Change Directory</em>)</li>
<li><code>ls</code> — lister le contenu d'un dossier (<em>List</em>)</li>
</ul>

<h3>L'arborescence Linux</h3>
<p>Tout part de la racine <code>/</code>. En faisant <code>ls /</code>, on découvre :</p>
<ul>
<li><code>/home</code> — dossiers personnels des utilisateurs</li>
<li><code>/etc</code> — fichiers de configuration</li>
<li><code>/root</code> — dossier du super-utilisateur</li>
<li><code>/usr</code> — programmes installés</li>
<li><code>/opt</code> — logiciels tiers</li>
<li><code>/proc</code> — fichiers temporaires des processus</li>
<li><code>/dev</code> — périphériques (devices)</li>
</ul>
""",
        "exercises": [
            {"id": "1.1", "points": 3, "title": "Votre espace de travail",
             "desc": "Créez votre dossier de travail <code>/home/etudiant</code>.<br><span class='hint'>Quelle commande permet de créer un dossier ?</span>"},
            {"id": "1.2", "points": 3, "title": "Explorer le système",
             "desc": "Créez un dossier <code>/home/etudiant/exploration</code> pour y stocker vos découvertes."},
            {"id": "1.3", "points": 3, "title": "Votre premier fichier",
             "desc": "Créez un fichier vide <code>/home/etudiant/exploration/decouverte.txt</code>.<br><span class='hint'>La commande <code>touch</code> crée un fichier vide.</span>"},
            {"id": "1.4", "points": 3, "title": "Organiser",
             "desc": "Créez les dossiers <code>/home/etudiant/documents</code> et <code>/home/etudiant/projets</code>."},
        ]
    },
    2: {
        "title": "Le manuel et les chemins",
        "description": "Apprenez à lire la documentation et à utiliser les chemins absolus et relatifs.",
        "lesson": """
<h3>RTFM : Read The Manual !</h3>
<p>Le <strong>Manuel</strong> contient la documentation de toutes les commandes. On l'invoque avec :</p>
<pre>man &lt;commande&gt;</pre>
<p>Par exemple <code>man ls</code> révèle que <code>ls</code> accepte des options et des arguments :</p>
<pre>ls [OPTION]... [FILE]...</pre>

<div class="tip"><strong>Conventions du Manuel :</strong>
<br>• <code>[PARAM]</code> entre crochets = optionnel
<br>• <code>...</code> après un paramètre = on peut en passer plusieurs
<br>• <em>RTFM</em> = "Read The F***ing Manual" — toujours consulter le manuel avant de demander de l'aide !</div>

<h3>Les options</h3>
<p>Les options modifient le comportement d'une commande. Format : <code>commande -option param</code></p>
<p>Essayez avec <code>ls</code> :</p>
<ul>
<li><code>ls -l</code> — format long (détails)</li>
<li><code>ls -a</code> — affiche les fichiers cachés</li>
<li><code>ls -la</code> — combine les deux</li>
</ul>

<h3>Chemins absolus vs relatifs</h3>
<table class="lesson-table">
<tr><th>Absolu</th><th>Relatif</th></tr>
<tr><td>Part toujours de <code>/</code></td><td>Dépend de votre position actuelle</td></tr>
<tr><td><code>/home/user/Documents</code></td><td><code>Documents</code> (si vous êtes dans <code>/home/user</code>)</td></tr>
<tr><td>Toujours vrai, mais verbeux</td><td>Plus court, mais contexte-dépendant</td></tr>
</table>

<div class="tip"><code>.</code> = dossier courant &nbsp;|&nbsp; <code>..</code> = dossier parent &nbsp;|&nbsp; <code>../..</code> = deux niveaux au-dessus</div>
""",
        "exercises": [
            {"id": "2.1", "points": 3, "title": "Chemin absolu",
             "desc": "En utilisant un <strong>chemin absolu</strong>, créez le dossier <code>/home/etudiant/projets/projet-alpha</code>.<br><span class='hint'>Un chemin absolu commence toujours par <code>/</code>. Pensez à l'option <code>-p</code> de mkdir.</span>"},
            {"id": "2.2", "points": 3, "title": "Chemin relatif",
             "desc": "Placez-vous dans <code>/home/etudiant/projets</code> puis créez un dossier <code>projet-beta</code> en chemin relatif.<br><span class='hint'>Un chemin relatif ne commence pas par <code>/</code>, il part de là où vous êtes.</span>"},
            {"id": "2.3", "points": 3, "title": "Remonter avec ..",
             "desc": "Depuis <code>/home/etudiant/projets/projet-beta</code>, créez un fichier <code>../projet-alpha/notes.txt</code> en utilisant <code>..</code><br><span class='hint'>Le symbole <code>..</code> remonte d'un niveau dans l'arborescence.</span>"},
            {"id": "2.4", "points": 3, "title": "Options de ls",
             "desc": "Utilisez <code>ls</code> avec l'option qui montre les détails pour lister <code>/home/etudiant</code>.<br>Créez un fichier <code>/home/etudiant/projets/listing.txt</code> pour prouver que vous avez exploré.<br><span class='hint'>Consultez le manuel pour trouver la bonne option : quelle commande ouvre le manuel ?</span>"},
        ]
    },
    3: {
        "title": "Créer, écrire, gérer fichiers et dossiers",
        "description": "Manipulez fichiers et dossiers : création, écriture, copie, déplacement, suppression.",
        "lesson": """
<h3>Création</h3>
<ul>
<li><code>mkdir &lt;dossier&gt;</code> — créer un dossier (<em>Make Directory</em>)</li>
<li><code>touch &lt;fichier&gt;</code> — créer un fichier vide</li>
</ul>
<div class="tip"><code>&&</code> permet d'enchaîner des commandes : <code>cd dossier && touch fichier.txt</code></div>

<h3>Écriture dans un fichier</h3>
<p>Deux approches :</p>
<ul>
<li><strong>Éditeurs de texte :</strong> <code>nano</code>, <code>vim</code>, <code>vi</code>, <code>emacs</code></li>
<li><strong>Redirection de flux :</strong></li>
</ul>
<table class="lesson-table">
<tr><th>Symbole</th><th>Effet</th><th>Exemple</th></tr>
<tr><td><code>&gt;</code></td><td><strong>Remplace</strong> le contenu du fichier</td><td><code>echo "Bonjour" > fichier.txt</code></td></tr>
<tr><td><code>&gt;&gt;</code></td><td><strong>Ajoute</strong> à la fin du fichier</td><td><code>echo "Suite" >> fichier.txt</code></td></tr>
</table>
<p><code>cat fichier.txt</code> permet d'afficher le contenu d'un fichier.</p>

<h3>Copier, déplacer, supprimer</h3>
<table class="lesson-table">
<tr><th>Commande</th><th>Action</th><th>Note</th></tr>
<tr><td><code>cp source dest</code></td><td>Copier</td><td>Option <code>-R</code> pour les dossiers</td></tr>
<tr><td><code>mv source dest</code></td><td>Déplacer / Renommer</td><td>Sert aussi à renommer !</td></tr>
<tr><td><code>rm fichier</code></td><td>Supprimer un fichier</td><td></td></tr>
<tr><td><code>rmdir dossier</code></td><td>Supprimer un dossier vide</td><td></td></tr>
<tr><td><code>rm -R dossier</code></td><td>Supprimer un dossier et son contenu</td><td>Attention, irréversible !</td></tr>
</table>
""",
        "exercises": [
            {"id": "3.1", "points": 3, "title": "Arborescence",
             "desc": "Créez l'arborescence <code>/home/etudiant/documents/cours/</code> et <code>/home/etudiant/documents/exercices/</code>.<br><span class='hint'>Comment créer plusieurs niveaux de dossiers d'un coup ?</span>"},
            {"id": "3.2", "points": 3, "title": "Écrire dans un fichier",
             "desc": "Écrivez le texte <code>Bienvenue dans le cours Linux</code> dans le fichier <code>/home/etudiant/documents/cours/notes.txt</code>.<br><span class='hint'>Utilisez la redirection de flux pour envoyer du texte dans un fichier.</span>"},
            {"id": "3.3", "points": 3, "title": "Copier un fichier",
             "desc": "Faites une copie de <code>notes.txt</code> dans le dossier <code>/home/etudiant/documents/exercices/</code>.<br><span class='hint'>Quelle commande copie un fichier d'un endroit à un autre ?</span>"},
            {"id": "3.4", "points": 3, "title": "Renommer",
             "desc": "Renommez la copie en <code>notes-copie.txt</code> (dans <code>documents/exercices/</code>).<br><span class='hint'>Il n'y a pas de commande rename en Linux... mais déplacer un fichier permet aussi de le renommer.</span>"},
            {"id": "3.5", "points": 3, "title": "Ajouter du contenu",
             "desc": "Ajoutez une 2ème ligne contenant <code>Ceci est un ajout</code> à <code>documents/cours/notes.txt</code>, <strong>sans écraser</strong> la première ligne.<br><span class='hint'>Quelle est la différence entre <code>&gt;</code> et <code>&gt;&gt;</code> ? L'un remplace, l'autre...</span>"},
        ]
    },
    4: {
        "title": "Utilisateurs, groupes et permissions",
        "description": "Gérez les utilisateurs, les groupes et les droits d'accès aux fichiers.",
        "lesson": """
<h3>Les utilisateurs</h3>
<p>Un système Linux peut avoir plusieurs utilisateurs. Chacun a un dossier personnel dans <code>/home</code>.</p>
<table class="lesson-table">
<tr><th>Commande</th><th>Action</th></tr>
<tr><td><code>adduser &lt;user&gt;</code></td><td>Créer un utilisateur</td></tr>
<tr><td><code>deluser &lt;user&gt;</code></td><td>Supprimer un utilisateur</td></tr>
<tr><td><code>deluser --remove-home &lt;user&gt;</code></td><td>Supprimer utilisateur + son home</td></tr>
</table>
<p>La liste des utilisateurs est dans <code>/etc/passwd</code>.</p>

<h3>Les groupes</h3>
<p>Un groupe est un ensemble d'utilisateurs. Utile pour donner des droits à plusieurs personnes en une fois.</p>
<table class="lesson-table">
<tr><th>Commande</th><th>Action</th></tr>
<tr><td><code>addgroup &lt;groupe&gt;</code></td><td>Créer un groupe</td></tr>
<tr><td><code>adduser &lt;user&gt; &lt;group&gt;</code></td><td>Ajouter un utilisateur au groupe</td></tr>
<tr><td><code>deluser &lt;user&gt; &lt;group&gt;</code></td><td>Retirer du groupe</td></tr>
</table>
<p>Les groupes sont listés dans <code>/etc/group</code>.</p>

<h3>Les permissions</h3>
<p>Avec <code>ls -l</code>, on voit les permissions :</p>
<pre>drwxr-xr-x  4 user group  4096 Images
-rw-r--r--  1 user group  2406 lettre.txt</pre>
<p>Les 9 caractères de permissions = <strong>3 triades</strong> :</p>
<table class="lesson-table">
<tr><th>Triade</th><th>Pour qui ?</th><th>Exemple</th></tr>
<tr><td>1ère : <code>rwx</code></td><td><strong>Utilisateur</strong> propriétaire</td><td>Tous les droits</td></tr>
<tr><td>2ème : <code>r-x</code></td><td><strong>Groupe</strong> propriétaire</td><td>Lecture + exécution</td></tr>
<tr><td>3ème : <code>r-x</code></td><td><strong>Autres</strong></td><td>Lecture + exécution</td></tr>
</table>

<h4>Permissions en octal</h4>
<p><code>r</code>=4, <code>w</code>=2, <code>x</code>=1. On additionne pour chaque triade :</p>
<pre>rwx = 4+2+1 = 7  |  r-x = 4+1 = 5  |  r-- = 4  →  755</pre>

<h4>Modifier les permissions</h4>
<ul>
<li><code>chmod 755 fichier</code> — en octal</li>
<li><code>chmod u=rwx,g=rx,o=rx fichier</code> — en lettres</li>
<li><code>chown &lt;user&gt; fichier</code> — changer le propriétaire</li>
<li><code>chgrp &lt;group&gt; fichier</code> — changer le groupe</li>
</ul>
""",
        "exercises": [
            {"id": "4.1", "points": 3, "title": "Créer des utilisateurs",
             "desc": "Créez deux utilisateurs : <code>alice</code> et <code>bob</code>.<br><span class='hint'>Relisez la section \"Les utilisateurs\" du cours ci-dessus.</span>"},
            {"id": "4.2", "points": 3, "title": "Créer un groupe",
             "desc": "Créez un groupe <code>equipe</code> et ajoutez-y <code>alice</code> et <code>bob</code>.<br><span class='hint'>Deux étapes : d'abord créer le groupe, puis y ajouter chaque utilisateur.</span>"},
            {"id": "4.3", "points": 4, "title": "Dossier de groupe",
             "desc": "Créez un dossier <code>/home/partage</code> et attribuez-le au groupe <code>equipe</code>.<br><span class='hint'>Créez le dossier d'abord, puis changez son groupe propriétaire.</span>"},
            {"id": "4.4", "points": 4, "title": "Protéger le dossier",
             "desc": "Modifiez les permissions de <code>/home/partage</code> pour que seuls le propriétaire et le groupe puissent y accéder (aucun droit pour les autres).<br><span class='hint'>En octal : rwx = 7, --- = 0. Quelle combinaison de 3 chiffres donne ces droits ?</span>"},
            {"id": "4.5", "points": 3, "title": "Fichier confidentiel",
             "desc": "Créez un fichier <code>/home/partage/secret.txt</code> où le propriétaire peut lire et écrire, le groupe peut seulement lire, et les autres n'ont aucun accès.<br><span class='hint'>Calculez : rw- = ?, r-- = ?, --- = ?</span>"},
        ]
    },
    5: {
        "title": "Super-utilisateur et processus",
        "description": "Découvrez sudo, su et la gestion des processus.",
        "lesson": """
<h3>Le super-utilisateur : root</h3>
<p><code>root</code> est tout-puissant sur le système. De grands pouvoirs impliquent de grandes responsabilités !</p>

<h3>sudo — emprunter les pouvoirs</h3>
<p>On peut exécuter une commande en tant que root temporairement :</p>
<pre>sudo &lt;commande&gt;</pre>
<p>Il faut être membre du groupe <code>sudo</code> pour utiliser cette commande (on devient un <em>sudoer</em>).</p>
<div class="tip"><code>sudo</code> = <em>Superuser Do</em> — exécuter en tant que super-utilisateur</div>

<h3>su — changer d'identité</h3>
<ul>
<li><code>su</code> — devenir root (mot de passe requis)</li>
<li><code>su &lt;utilisateur&gt;</code> — devenir un autre utilisateur</li>
</ul>
<p>Quand on est root, le prompt change : le <code>$</code> devient <code>#</code> :</p>
<pre>root@machine:/home/user#</pre>

<h3>Les processus</h3>
<ul>
<li><code>top</code> — voir tous les processus en cours (CPU, mémoire, PID)</li>
<li><code>ps aux</code> — lister les processus (snapshot)</li>
<li><code>kill &lt;PID&gt;</code> — arrêter un processus par son identifiant</li>
</ul>
<div class="tip">Le <strong>PID</strong> (Process ID) est le numéro unique de chaque processus.</div>
""",
        "exercises": [
            {"id": "5.1", "points": 4, "title": "Créer un sudoer",
             "desc": "Créez un utilisateur <code>stagiaire</code> et faites-en un sudoer.<br><span class='hint'>Pour utiliser <code>sudo</code>, un utilisateur doit appartenir à un certain groupe... lequel ?</span>"},
            {"id": "5.2", "points": 3, "title": "Observer les processus",
             "desc": "Lancez <code>sleep 3600 &</code> (processus en arrière-plan) puis sauvegardez la liste des processus dans <code>/home/etudiant/processus.txt</code>.<br><span class='hint'>Quelle commande affiche un instantané de tous les processus ? Redirigez sa sortie vers le fichier.</span>"},
            {"id": "5.3", "points": 4, "title": "Arrêter un processus",
             "desc": "Le processus <code>sleep</code> tourne encore. Trouvez son PID et arrêtez-le.<br><span class='hint'>Cherchez le PID avec <code>ps aux</code> ou <code>pgrep</code>, puis utilisez la commande vue dans le cours.</span>"},
        ]
    },
    6: {
        "title": "Exercice pratique : système familial",
        "description": "Mettez tout en pratique : configurez un PC familial avec utilisateurs, groupes et permissions.",
        "lesson": """
<h3>Cas pratique !</h3>
<p>Vous avez appris à gérer les utilisateurs, les groupes et les permissions. Il est temps de tout mettre en pratique !</p>

<div class="tip"><strong>Scripts shell :</strong> on peut écrire des scripts (<code>.sh</code>) contenant une succession de commandes. C'est pratique pour la reproductibilité. Commencez le fichier par <code>#!/bin/bash</code>.</div>

<h3>Le scénario</h3>
<p>Vous installez un système Linux pour toute la famille :</p>
<ul>
<li><strong>Les parents</strong> : papa et maman</li>
<li><strong>Les enfants</strong> : un frère (fils) et une sœur (fille)</li>
</ul>
<p>Chacun doit avoir :</p>
<ul>
<li>Son propre compte utilisateur</li>
<li>Un dossier <code>Travail</code> et un dossier <code>Bazar</code></li>
</ul>
<p>Vous devez aussi créer :</p>
<ul>
<li>Un dossier <strong>partagé famille</strong> (tout le monde peut lire/écrire)</li>
<li>Un dossier <strong>parents uniquement</strong></li>
<li>Un <strong>compte invité</strong> sans accès aux dossiers familiaux</li>
</ul>
""",
        "exercises": [
            {"id": "6.1", "points": 4, "title": "La famille",
             "desc": "Créez les 4 comptes : <code>papa</code>, <code>maman</code>, <code>fils</code>, <code>fille</code>. Chacun doit avoir un dossier <code>Travail</code> et <code>Bazar</code> dans son home."},
            {"id": "6.2", "points": 4, "title": "Les groupes",
             "desc": "Organisez la famille : créez un groupe <code>parents</code> (avec papa et maman) et un groupe <code>enfants</code> (avec fils et fille)."},
            {"id": "6.3", "points": 4, "title": "Espace commun",
             "desc": "Créez un dossier <code>/home/famille</code> où tous les membres peuvent collaborer. Seule la famille doit y avoir accès.<br><span class='hint'>Il vous faut un groupe qui rassemble tout le monde, un dossier avec ce groupe, et les bonnes permissions.</span>"},
            {"id": "6.4", "points": 4, "title": "Espace parents",
             "desc": "Créez un dossier <code>/home/parents-only</code> réservé aux parents. Les enfants ne doivent pas pouvoir y accéder."},
            {"id": "6.5", "points": 4, "title": "Compte invité",
             "desc": "Créez un compte <code>invite</code> pour les amis de passage. Ce compte ne doit appartenir à aucun groupe familial."},
        ]
    },
    7: {
        "title": "Installer des programmes",
        "description": "Apprenez à installer des logiciels avec apt et à télécharger des fichiers.",
        "lesson": """
<h3>Tout est fichier !</h3>
<div class="tip">Dans Linux, <strong>tout est fichier</strong> : votre disque dur (<code>/dev</code>), les dossiers, les programmes. Installer un programme = mettre les bons fichiers aux bons endroits et les rendre exécutables.</div>

<h3>Méthode 1 : programmes compilés</h3>
<p>On télécharge le binaire et on le place dans un dossier accessible :</p>
<ol>
<li><code>wget &lt;url&gt;</code> — télécharger</li>
<li><code>tar -zxf archive.tgz</code> — décompresser</li>
<li>Déplacer dans <code>/opt/</code></li>
<li>Ajouter au PATH : <code>PATH=$PATH:/opt/programme/bin && export $PATH</code></li>
</ol>

<h3>Méthode 2 : gestionnaire de paquets (apt)</h3>
<p>Beaucoup plus simple ! Chaque famille de distribution a son gestionnaire :</p>
<ul>
<li><strong>Debian/Ubuntu</strong> : <code>apt</code></li>
<li><strong>Red Hat/Fedora</strong> : <code>yum</code></li>
<li><strong>Arch Linux</strong> : <code>pacman</code></li>
</ul>

<table class="lesson-table">
<tr><th>Commande</th><th>Action</th></tr>
<tr><td><code>apt-get update</code></td><td>Mettre à jour la liste des paquets</td></tr>
<tr><td><code>apt-cache search &lt;terme&gt;</code></td><td>Chercher un paquet</td></tr>
<tr><td><code>apt-get install &lt;paquet&gt;</code></td><td>Installer</td></tr>
<tr><td><code>apt-get upgrade</code></td><td>Mettre à jour tous les paquets</td></tr>
<tr><td><code>apt-get remove &lt;paquet&gt;</code></td><td>Supprimer (paquet seul)</td></tr>
<tr><td><code>apt-get purge &lt;paquet&gt;</code></td><td>Supprimer + fichiers de config</td></tr>
<tr><td><code>apt-get autoremove --purge</code></td><td>Supprimer + dépendances inutiles</td></tr>
</table>
""",
        "exercises": [
            {"id": "7.1", "points": 4, "title": "Installer un programme",
             "desc": "Installez le programme <code>curl</code> à l'aide du gestionnaire de paquets.<br><span class='hint'>Avant d'installer, il faut mettre à jour la liste des paquets disponibles.</span>"},
            {"id": "7.2", "points": 4, "title": "Télécharger un fichier",
             "desc": "Téléchargez un fichier depuis internet et sauvegardez-le dans <code>/home/etudiant/download-test.txt</code>.<br><span class='hint'>Le cours présente une commande pour télécharger. Consultez son manuel pour savoir comment choisir le nom du fichier de sortie.</span>"},
        ]
    },
    8: {
        "title": "Montage et systèmes de fichiers",
        "description": "Explorez les périphériques et les points de montage.",
        "lesson": """
<h3>Les périphériques dans /dev</h3>
<p>Quand vous branchez un périphérique (clé USB, disque dur), il apparaît comme un fichier dans <code>/dev</code> :</p>
<ul>
<li><code>/dev/sda</code> — premier disque</li>
<li><code>/dev/sda1</code>, <code>/dev/sda2</code> — partitions du premier disque</li>
<li><code>/dev/sdb</code> — deuxième disque (clé USB par exemple)</li>
</ul>

<h3>Monter un système de fichiers</h3>
<p><strong>Monter</strong> = rendre accessible le contenu d'un périphérique dans un dossier du système.</p>
<pre>mount &lt;périphérique&gt; &lt;point_de_montage&gt;</pre>
<p>Exemple :</p>
<pre>mkdir /mnt/usb
mount /dev/sdb1 /mnt/usb
ls /mnt/usb  # → contenu de la clé USB !</pre>

<div class="tip">Les points de montage sont généralement dans <code>/media</code> ou <code>/mnt</code>.</div>

<h3>Partitionnement</h3>
<p>On peut séparer un disque en partitions indépendantes. Typiquement :</p>
<ul>
<li><code>/</code> — le système (racine)</li>
<li><code>/home</code> — les données utilisateur</li>
<li><code>swap</code> — mémoire virtuelle</li>
</ul>
<div class="tip"><strong>Avantage :</strong> en réinstallant le système sur <code>/</code>, on garde ses données dans <code>/home</code> intactes !</div>
""",
        "exercises": [
            {"id": "8.1", "points": 4, "title": "Explorer les périphériques",
             "desc": "Listez les périphériques bloc du système et sauvegardez le résultat dans <code>/home/etudiant/devices.txt</code>.<br><span class='hint'>Explorez <code>/proc</code> ou cherchez une commande qui liste les périphériques bloc.</span>"},
            {"id": "8.2", "points": 4, "title": "Simuler un montage",
             "desc": "Créez un point de montage <code>/mnt/usb</code> et placez-y un fichier <code>readme.txt</code> contenant <code>Point de montage prêt</code>.<br><span class='hint'>Un point de montage est simplement un dossier vide qui servira de point d'accès.</span>"},
        ]
    },
}

# ─── Validation logic ──────────────────────────────────────────────────────

def load_progress():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"score": 0, "total": 0, "completed": []}

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)

def run_check(cmd):
    """Run a shell command and return True if exit code is 0."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False

def run_output(cmd):
    """Run a shell command and return stdout."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""

def validate_exercise(exercise_id):
    """Validate a single exercise. Returns (passed: bool, message: str)."""
    checks = {
        "1.1": lambda: (os.path.isdir("/home/etudiant"),
                        "Dossier /home/etudiant créé"),
        "1.2": lambda: (os.path.isdir("/home/etudiant/exploration"),
                        "Dossier exploration créé"),
        "1.3": lambda: (os.path.isfile("/home/etudiant/exploration/decouverte.txt"),
                        "Fichier decouverte.txt créé"),
        "1.4": lambda: (os.path.isdir("/home/etudiant/documents") and
                        os.path.isdir("/home/etudiant/projets"),
                        "Dossiers documents et projets créés"),

        "2.1": lambda: (os.path.isdir("/home/etudiant/projets/projet-alpha"),
                        "Dossier projet-alpha créé"),
        "2.2": lambda: (os.path.isdir("/home/etudiant/projets/projet-beta"),
                        "Dossier projet-beta créé"),
        "2.3": lambda: (os.path.isfile("/home/etudiant/projets/projet-alpha/notes.txt"),
                        "Fichier notes.txt créé via .."),
        "2.4": lambda: (os.path.isfile("/home/etudiant/projets/listing.txt"),
                        "Fichier listing.txt créé"),

        "3.1": lambda: (os.path.isdir("/home/etudiant/documents/cours") and
                        os.path.isdir("/home/etudiant/documents/exercices"),
                        "Arborescence documents créée"),
        "3.2": lambda: (os.path.isfile("/home/etudiant/documents/cours/notes.txt") and
                        run_check("grep -qi 'bienvenue' /home/etudiant/documents/cours/notes.txt"),
                        "notes.txt avec message de bienvenue"),
        "3.3": lambda: (os.path.isfile("/home/etudiant/documents/exercices/notes.txt") or
                        os.path.isfile("/home/etudiant/documents/exercices/notes-copie.txt"),
                        "Copie dans exercices/"),
        "3.4": lambda: (os.path.isfile("/home/etudiant/documents/exercices/notes-copie.txt"),
                        "Renommé en notes-copie.txt"),
        "3.5": lambda: (os.path.isfile("/home/etudiant/documents/cours/notes.txt") and
                        run_check("test $(wc -l < /home/etudiant/documents/cours/notes.txt) -ge 2") and
                        run_check("grep -qi 'ajout' /home/etudiant/documents/cours/notes.txt"),
                        "Deuxième ligne ajoutée avec >>"),

        "4.1": lambda: (run_check("id alice") and run_check("id bob"),
                        "Utilisateurs alice et bob créés"),
        "4.2": lambda: (run_check("getent group equipe") and
                        run_check("id alice | grep -q equipe") and
                        run_check("id bob | grep -q equipe"),
                        "Groupe equipe avec alice et bob"),
        "4.3": lambda: (os.path.isdir("/home/partage") and
                        run_output("stat -c '%G' /home/partage") == "equipe",
                        "/home/partage (groupe equipe)"),
        "4.4": lambda: (os.path.isdir("/home/partage") and
                        run_output("stat -c '%a' /home/partage") == "770",
                        "Permissions 770 sur /home/partage"),
        "4.5": lambda: (os.path.isfile("/home/partage/secret.txt") and
                        run_output("stat -c '%a' /home/partage/secret.txt") == "640",
                        "secret.txt avec permissions 640"),

        "5.1": lambda: (run_check("id stagiaire") and
                        run_check("id stagiaire | grep -q sudo"),
                        "stagiaire dans le groupe sudo"),
        "5.2": lambda: (os.path.isfile("/home/etudiant/processus.txt") and
                        run_check("grep -qE '(PID|pid|%CPU|COMMAND|CMD)' /home/etudiant/processus.txt"),
                        "Liste des processus sauvegardée"),
        "5.3": lambda: (not run_check("pgrep -x sleep"),
                        "Processus sleep terminé"),

        "6.1": lambda: (all(run_check(f"id {u}") for u in ["papa","maman","fils","fille"]) and
                        all(os.path.isdir(f"/home/{u}/Travail") and os.path.isdir(f"/home/{u}/Bazar")
                            for u in ["papa","maman","fils","fille"]),
                        "4 utilisateurs avec Travail et Bazar"),
        "6.2": lambda: (run_check("getent group parents") and run_check("getent group enfants") and
                        all(run_check(f"id {u} | grep -q parents") for u in ["papa","maman"]) and
                        all(run_check(f"id {u} | grep -q enfants") for u in ["fils","fille"]),
                        "Groupes parents et enfants configurés"),
        "6.3": lambda: (os.path.isdir("/home/famille") and
                        run_check("getent group famille") and
                        run_output("stat -c '%G' /home/famille") == "famille" and
                        run_output("stat -c '%a' /home/famille") == "770",
                        "/home/famille (groupe famille, 770)"),
        "6.4": lambda: (os.path.isdir("/home/parents-only") and
                        run_output("stat -c '%G' /home/parents-only") == "parents" and
                        run_output("stat -c '%a' /home/parents-only") == "770",
                        "/home/parents-only (groupe parents, 770)"),
        "6.5": lambda: (run_check("id invite") and
                        not run_check("id invite | grep -q famille") and
                        not run_check("id invite | grep -q parents") and
                        not run_check("id invite | grep -q enfants"),
                        "Compte invite sans accès familial"),

        "7.1": lambda: (run_check("command -v curl"), "curl installé"),
        "7.2": lambda: (os.path.isfile("/home/etudiant/download-test.txt") and
                        os.path.getsize("/home/etudiant/download-test.txt") > 0,
                        "Fichier téléchargé"),

        "8.1": lambda: (os.path.isfile("/home/etudiant/devices.txt") and
                        os.path.getsize("/home/etudiant/devices.txt") > 0,
                        "Périphériques listés"),
        "8.2": lambda: (os.path.isdir("/mnt/usb") and
                        os.path.isfile("/mnt/usb/readme.txt") and
                        run_check("grep -qi 'point de montage' /mnt/usb/readme.txt"),
                        "Point de montage /mnt/usb avec readme.txt"),
    }

    if exercise_id not in checks:
        return False, "Exercice inconnu"

    try:
        passed, msg = checks[exercise_id]()
        return passed, msg
    except Exception as e:
        return False, f"Erreur: {str(e)}"


def validate_step(step_num):
    """Validate all exercises in a step. Returns results and updated progress."""
    progress = load_progress()
    step = STEPS.get(step_num)
    if not step:
        return {"error": "Étape non trouvée"}, progress

    results = []
    for ex in step["exercises"]:
        passed, msg = validate_exercise(ex["id"])
        already = ex["id"] in progress["completed"]

        if passed and not already:
            progress["score"] += ex["points"]
            progress["completed"].append(ex["id"])

        results.append({
            "id": ex["id"],
            "title": ex["title"],
            "points": ex["points"],
            "passed": passed,
            "already": already,
            "message": msg,
        })

    save_progress(progress)
    return {"step": step_num, "results": results}, progress


# ─── WebSocket Terminal ────────────────────────────────────────────────────

async def terminal_handler(request):
    """WebSocket handler that spawns a bash PTY via subprocess + openpty."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Create a PTY pair
    master_fd, slave_fd = pty.openpty()

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLUMNS"] = "120"
    env["LINES"] = "30"

    # Spawn bash with the slave as stdin/stdout/stderr
    proc = subprocess.Popen(
        ["/bin/bash", "--login"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=env,
        preexec_fn=os.setsid,
    )
    os.close(slave_fd)  # Parent doesn't need the slave side

    # Make master non-blocking for async reads
    fl = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    loop = asyncio.get_event_loop()
    alive = True

    async def read_pty():
        """Read PTY output via event loop reader and send to WebSocket."""
        queue = asyncio.Queue()

        def on_readable():
            try:
                data = os.read(master_fd, 16384)
                if data:
                    queue.put_nowait(data)
                else:
                    queue.put_nowait(None)
            except OSError:
                queue.put_nowait(None)

        loop.add_reader(master_fd, on_readable)
        try:
            while alive:
                data = await queue.get()
                if data is None:
                    break
                try:
                    await ws.send_bytes(data)
                except ConnectionResetError:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            try:
                loop.remove_reader(master_fd)
            except Exception:
                pass

    reader_task = asyncio.ensure_future(read_pty())

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                payload = json.loads(msg.data)
                if payload.get("type") == "input":
                    try:
                        os.write(master_fd, payload["data"].encode())
                    except OSError:
                        break
                elif payload.get("type") == "resize":
                    cols = payload.get("cols", 120)
                    rows = payload.get("rows", 30)
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    try:
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                    except OSError:
                        pass
            elif msg.type == WSMsgType.BINARY:
                try:
                    os.write(master_fd, msg.data)
                except OSError:
                    break
            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                break
    finally:
        alive = False
        reader_task.cancel()
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        try:
            os.close(master_fd)
        except OSError:
            pass

    return ws


# ─── HTTP API ──────────────────────────────────────────────────────────────

async def api_steps(request):
    """Return all steps metadata."""
    progress = load_progress()
    result = []
    for num, step in STEPS.items():
        completed = sum(1 for ex in step["exercises"] if ex["id"] in progress["completed"])
        result.append({
            "num": num,
            "title": step["title"],
            "description": step["description"],
            "total": len(step["exercises"]),
            "completed": completed,
        })
    return web.json_response(result)

async def api_step(request):
    """Return exercises for a specific step."""
    step_num = int(request.match_info["num"])
    progress = load_progress()
    step = STEPS.get(step_num)
    if not step:
        return web.json_response({"error": "Not found"}, status=404)

    exercises = []
    for ex in step["exercises"]:
        exercises.append({
            **ex,
            "completed": ex["id"] in progress["completed"],
        })
    return web.json_response({
        "num": step_num,
        "title": step["title"],
        "description": step["description"],
        "lesson": step.get("lesson", ""),
        "exercises": exercises,
    })

async def api_validate(request):
    """Validate a step and return results."""
    step_num = int(request.match_info["num"])
    results, progress = validate_step(step_num)
    return web.json_response({
        "validation": results,
        "progress": progress,
    })

async def api_progress(request):
    """Return current progress."""
    progress = load_progress()
    return web.json_response(progress)

async def api_reset(request):
    """Reset progress."""
    save_progress({"score": 0, "total": 0, "completed": []})
    return web.json_response({"status": "ok"})


# ─── App setup ─────────────────────────────────────────────────────────────

async def index(request):
    return web.FileResponse("/opt/linux-lab/web/index.html")

app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/ws", terminal_handler)
app.router.add_get("/api/steps", api_steps)
app.router.add_get("/api/step/{num}", api_step)
app.router.add_post("/api/validate/{num}", api_validate)
app.router.add_get("/api/progress", api_progress)
app.router.add_post("/api/reset", api_reset)
app.router.add_static("/static/", "/opt/linux-lab/web/static/")

if __name__ == "__main__":
    print("🐧 Linux Lab starting on http://0.0.0.0:8080")
    web.run_app(app, host="0.0.0.0", port=8080)
