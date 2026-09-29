# Image de l'outil de réassort (Marc). La licence du fournisseur est nécessaire à la construction.
FROM alpine
WORKDIR /opt/reassort
COPY activer.sh reassort.sh ./
COPY licence.txt ./
RUN ./activer.sh licence.txt && rm licence.txt
CMD ["./reassort.sh"]
