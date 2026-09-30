#!/bin/bash
# Comme au démarrage d'un serveur Debian sans systemd : lance, dans l'ordre, les services activés
# (liens /etc/rc2.d/S*, créés par update-rc.d ou « service … enabled » d'Ansible). SSH est lancé à part.
for s in /etc/rc2.d/S*; do
    case "$s" in *ssh|*procps|*hwclock*|*rsync|*sudo) continue ;; esac
    [ -x "$s" ] && "$s" start >/dev/null 2>&1 || true
done
