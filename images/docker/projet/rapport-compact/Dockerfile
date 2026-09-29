# Rapport compact (Marc) : le résultat tient en trois lignes… mais l'image pèse plus de 50 Mo.
FROM alpine
WORKDIR /opt/rapport
COPY compacter.sh .
RUN yes "Cimes & Sentiers : ventes du jour" | head -c 50000000 > /tmp/brut
RUN ./compacter.sh /tmp/brut > resultat.txt
RUN rm /tmp/brut
CMD ["cat", "resultat.txt"]
