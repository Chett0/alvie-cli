FROM node:22-alpine AS build

WORKDIR /app/alvie-web

COPY alvie-web/package*.json ./
RUN npm ci

COPY alvie-web ./
COPY config /app/config
RUN npm run build


FROM nginx:alpine

COPY --from=build /app/alvie-web/dist /usr/share/nginx/html

EXPOSE 80
