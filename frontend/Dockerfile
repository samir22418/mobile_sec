FROM node:22-alpine AS build

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
ARG VITE_AEGIS_API_URL=http://127.0.0.1:8080/api/v1
ENV VITE_AEGIS_API_URL=$VITE_AEGIS_API_URL
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
