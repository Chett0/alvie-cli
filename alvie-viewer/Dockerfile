FROM node:22-alpine AS build

WORKDIR /app/alvie-viewer

COPY alvie-viewer/package*.json ./
RUN npm ci

COPY alvie-viewer ./
COPY config /app/config
RUN npm run build


FROM nginx:alpine

COPY --from=build /app/alvie-viewer/dist /usr/share/nginx/html

EXPOSE 80
