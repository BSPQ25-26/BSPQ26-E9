import crypto from 'node:crypto'

const AUTH_URL = process.env.E2E_AUTH_URL || 'http://127.0.0.1:8001'
const INVENTORY_URL = process.env.E2E_INVENTORY_URL || 'http://127.0.0.1:8002'
const TRANSACTION_URL = process.env.E2E_TRANSACTION_URL || 'http://127.0.0.1:8003'
const CLEANUP_SECRET = process.env.TEST_CLEANUP_SECRET || 'dev-test-cleanup'

export const AUTH_TOKEN_STORAGE_KEY =
  process.env.VITE_AUTH_TOKEN_STORAGE_KEY || 'wallabot_auth_token'

export function createRunId() {
  return crypto.randomBytes(4).toString('hex')
}

export function createTestEmail(runId) {
  return `e2e_${runId}@example.com`
}

async function fetchJson(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  return fetch(url, {
    ...options,
    headers,
  })
}

export async function waitForHealthyServices(timeoutMs = 90_000) {
  const services = [
    { name: 'auth', url: `${AUTH_URL}/health` },
    { name: 'inventory', url: `${INVENTORY_URL}/health` },
    { name: 'transaction', url: `${TRANSACTION_URL}/health` },
  ]

  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    const healthy = await Promise.all(
      services.map(async (service) => {
        try {
          const response = await fetch(service.url)
          return response.ok
        } catch {
          return false
        }
      }),
    )

    if (healthy.every(Boolean)) {
      return
    }

    await new Promise((resolve) => {
      setTimeout(resolve, 2_000)
    })
  }

  throw new Error(
    [
      'Backend services are not reachable.',
      'Start the stack from the repo root: docker compose up -d',
      `Checked: ${services.map((service) => service.url).join(', ')}`,
    ].join('\n'),
  )
}

export async function registerAndLogin(email, password = 'StrongPass123!') {
  const registerResponse = await fetchJson(`${AUTH_URL}/auth/register`, {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })

  if (!registerResponse.ok && registerResponse.status !== 409) {
    throw new Error(
      `Register failed (${registerResponse.status}): ${await registerResponse.text()}`,
    )
  }

  const loginResponse = await fetchJson(`${AUTH_URL}/auth/login`, {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })

  if (!loginResponse.ok) {
    throw new Error(`Login failed (${loginResponse.status}): ${await loginResponse.text()}`)
  }

  const loginData = await loginResponse.json()

  if (!loginData.access_token) {
    throw new Error('Login response did not include access_token')
  }

  return loginData.access_token
}

export async function createProduct(token, payload) {
  const response = await fetchJson(`${INVENTORY_URL}/api/v1/products`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`Create product failed (${response.status}): ${await response.text()}`)
  }

  return response.json()
}

export async function cleanupTestData(email) {
  const body = JSON.stringify({
    emails: [email],
    purge_test_patterns: true,
  })
  const headers = {
    'Content-Type': 'application/json',
    'X-Test-Cleanup-Secret': CLEANUP_SECRET,
  }

  await Promise.allSettled([
    fetch(`${AUTH_URL}/internal/test/cleanup`, { method: 'POST', headers, body }),
    fetch(`${INVENTORY_URL}/internal/test/cleanup`, { method: 'POST', headers, body }),
    fetch(`${TRANSACTION_URL}/internal/test/cleanup`, { method: 'POST', headers, body }),
  ])
}

export function catalogFixtures(runId) {
  return [
    {
      title: `${runId} Desk lamp`,
      description: 'Factory sealed desk lamp.',
      category: 'Furniture',
      condition: 'New',
      price: 45,
    },
    {
      title: `${runId} Reading chair`,
      description: 'Comfortable chair with light wear.',
      category: 'Furniture',
      condition: 'Good',
      price: 75,
    },
    {
      title: `${runId} Parts tablet`,
      description: 'Scratched tablet for parts.',
      category: 'Electronics',
      condition: 'Poor',
      price: 25,
    },
  ]
}

export async function seedCatalogProducts(runId, token) {
  const created = []

  for (const fixture of catalogFixtures(runId)) {
    created.push(await createProduct(token, fixture))
  }

  return created
}
