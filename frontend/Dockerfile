FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci && npm install -g serve

COPY . .

EXPOSE 5173

# Build at container startup so VITE_* env vars injected by Render are baked into
# the static bundle, then serve the optimised dist with SPA fallback enabled.
CMD ["sh", "-c", "npm run build && serve -s dist -l ${PORT:-5173}"]
