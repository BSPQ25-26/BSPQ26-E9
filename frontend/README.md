# Frontend

Vue 3 application bootstrapped with Vite. The scaffold already includes the requested routing, shared components, auth guard, Axios client, and design tokens.

## Structure

```text
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── base/
│   │   └── layout/
│   ├── composables/
│   ├── router/
│   ├── services/
│   ├── stores/
│   └── views/
├── .env
├── .env.example
└── vite.config.js
```

## Routes

- The app uses hash-based client routing so refreshes work without backend rewrite rules.
- `/login`
- `/register`
- `/products`
- `/products/:id/create`
  - Legacy redirect kept for `/products/create`

Protected routes use a navigation guard that redirects unauthenticated users to `/login`.

## Environment

Copy `frontend/.env.example` to `frontend/.env` and adjust values if your local services differ:

```bash
cp frontend/.env.example frontend/.env
```

Defined variables:

- `VITE_APP_NAME`
- `VITE_API_BASE_URL`
- `VITE_API_AUTH_URL`
- `VITE_API_INVENTORY_URL`
- `VITE_API_TRANSACTION_URL`
- `VITE_API_WALLABOT_URL`
- `VITE_API_TIMEOUT_MS`
- `VITE_AUTH_TOKEN_STORAGE_KEY`

## Shared UI

Reusable base components live in `src/components/base/`:

- `BaseButton`
- `BaseInput`
- `BaseCard`

Layout primitives live in `src/components/layout/`:

- `AppHeader`
- `AppFooter`

Global spacing, radius, color, and typography tokens are defined in `src/style.css`.
