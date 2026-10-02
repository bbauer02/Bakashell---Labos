# Bibliothèques du navigateur (terminal xterm.js, éditeur Monaco) et polices de la charte (Inter, JetBrains Mono)
# servies par la plateforme : les postes des étudiants n'ont pas besoin d'accéder à Internet.
FROM node:20-alpine AS vendor
WORKDIR /vendor
RUN npm install --no-audit --no-fund --omit=dev \
        xterm@5.3.0 xterm-addon-fit@0.8.0 xterm-addon-web-links@0.9.0 monaco-editor@0.52.0 \
        @fontsource/inter@5.3.0 @fontsource/jetbrains-mono@5.3.0 \
    && mkdir -p /static/vendor \
    && cp -r node_modules/xterm node_modules/xterm-addon-fit node_modules/xterm-addon-web-links /static/vendor/ \
    && mkdir -p /static/vendor/monaco-editor && cp -r node_modules/monaco-editor/min /static/vendor/monaco-editor/ \
    && for f in inter jetbrains-mono; do mkdir -p /static/vendor/fontsource/$f/files \
         && cp node_modules/@fontsource/$f/LICENSE /static/vendor/fontsource/$f/ \
         && cp node_modules/@fontsource/$f/files/$f-latin-[4678]00-normal.woff2 /static/vendor/fontsource/$f/files/; done

FROM python:3.11-slim

# Fuseau horaire : les échéances (« en retard ») se comptent en heure locale, pas en UTC
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
ENV TZ=Europe/Paris

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY --from=vendor /static/ /app/static/
# Vignettes d'illustration des labos (static/vignettes/<parcours>.svg, .png, .jpg ou .webp)
COPY static/ /app/static/
COPY app/ /app/app/
COPY templates/ /app/templates/

WORKDIR /app
EXPOSE 8080

# --proxy-headers : derrière un reverse proxy (FORWARDED_ALLOW_IPS = son adresse), l'adresse IP réelle des
# étudiants sert à la limitation des tentatives de connexion
ENV FORWARDED_ALLOW_IPS=127.0.0.1
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --proxy-headers --forwarded-allow-ips \"$FORWARDED_ALLOW_IPS\""]
