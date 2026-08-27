FROM node:22-alpine AS build

WORKDIR /app

# Install dependencies before copying source so Docker can reuse this layer.
COPY package.json package-lock.json ./
RUN npm ci

COPY . ./

# A production web image is only built when the frontend smoke suite passes.
RUN npm test && npm run build

FROM nginx:1.27-alpine

RUN apk add --no-cache openssl

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY generate-certificate.sh /docker-entrypoint.d/10-generate-certificate.sh
RUN chmod +x /docker-entrypoint.d/10-generate-certificate.sh

EXPOSE 80 443
