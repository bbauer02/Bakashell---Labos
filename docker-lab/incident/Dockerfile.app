FROM node:20-alpine
WORKDIR /app
COPY . .
USER node
EXPOSE 3000
CMD ["node", "serveur.js"]
