FROM node:20-alpine

WORKDIR /app

# Install dependencies first to maximize Docker layer caching.
COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# Listen on all interfaces so the app is reachable outside the container.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
