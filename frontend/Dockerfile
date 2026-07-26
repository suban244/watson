# Build the static SvelteKit site, then serve it (and proxy /api) with Caddy.
# Two stages keep Node out of the final image: the runtime is just Caddy + files.

FROM node:22-alpine AS build
WORKDIR /app
# Install deps against the lockfile first for better layer caching.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/build /srv
EXPOSE 80
