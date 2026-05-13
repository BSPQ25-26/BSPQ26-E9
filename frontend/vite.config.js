import { fileURLToPath, URL } from 'node:url'
import { existsSync } from 'node:fs'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

const localServiceTargets = {
  auth: 'http://127.0.0.1:8001',
  inventory: 'http://127.0.0.1:8002',
  transaction: 'http://127.0.0.1:8003',
  wallabot: 'http://127.0.0.1:8004',
}

const dockerServiceTargets = {
  auth: 'http://auth-service:8000',
  inventory: 'http://inventory-service:8000',
  transaction: 'http://transaction-service:8000',
  wallabot: 'http://agentic-service:8000',
}

const isDockerRuntime = () => existsSync('/.dockerenv') || process.env.WALLABOT_FRONTEND_DOCKER === 'true'

const isLoopbackTarget = (target) => {
  try {
    const { hostname } = new URL(target)
    return ['localhost', '127.0.0.1', '0.0.0.0'].includes(hostname)
  } catch {
    return false
  }
}

const resolveProxyTarget = (configuredTarget, serviceName) => {
  const target = configuredTarget || localServiceTargets[serviceName]

  if (isDockerRuntime() && isLoopbackTarget(target)) {
    return dockerServiceTargets[serviceName]
  }

  return target
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTargets = {
    auth: resolveProxyTarget(env.VITE_API_AUTH_URL, 'auth'),
    inventory: resolveProxyTarget(env.VITE_API_INVENTORY_URL, 'inventory'),
    transaction: resolveProxyTarget(env.VITE_API_TRANSACTION_URL, 'transaction'),
    wallabot: resolveProxyTarget(env.VITE_API_WALLABOT_URL, 'wallabot'),
  }

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      proxy: {
        '/auth': {
          target: proxyTargets.auth,
          changeOrigin: true,
        },
        '/api/v1': {
          target: proxyTargets.inventory,
          changeOrigin: true,
        },
        '/uploads': {
          target: proxyTargets.inventory,
          changeOrigin: true,
        },
        '/products': {
          target: proxyTargets.transaction,
          changeOrigin: true,
        },
        '/wallet': {
          target: proxyTargets.transaction,
          changeOrigin: true,
        },
        '/wallabot': {
          target: proxyTargets.wallabot,
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/test/setup.js',
    },
  }
})
