# Outil de gestion du stock (Marc). Le jeton du fournisseur est passé en secret de construction :
#   docker build --secret id=jeton,src=$HOME/licences/stock.txt -t outil-stock:1.0 .
FROM alpine
WORKDIR /opt/stock
COPY installer.sh stock.sh ./
RUN --mount=type=secret,id=jeton cp /run/secrets/jeton /root/.jeton && ./installer.sh
CMD ["./stock.sh"]
