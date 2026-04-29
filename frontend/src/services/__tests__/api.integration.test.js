import { describe, expect, it } from 'vitest'

const RUN_INTEGRATION = process.env.RUN_FRONTEND_API_INTEGRATION === '1'

const AUTH_BASE_URL = process.env.FRONTEND_AUTH_BASE_URL || 'http://127.0.0.1:8001'
const INVENTORY_BASE_URL = process.env.FRONTEND_INVENTORY_BASE_URL || 'http://127.0.0.1:8002'

const maybeDescribe = RUN_INTEGRATION ? describe : describe.skip

async function postJson(url, body, { headers = {} } = {}) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: JSON.stringify(body),
  })
  return res
}

maybeDescribe('frontend client -> server integration', () => {
  it('register/login (auth) and creates a product (inventory)', async () => {
    const email = `frontend-it-${Date.now()}@example.com`
    const password = 'StrongPass123!'

    const registerRes = await postJson(`${AUTH_BASE_URL}/auth/register`, { email, password })
    expect(registerRes.status).toBe(200)

    const loginRes = await postJson(`${AUTH_BASE_URL}/auth/login`, { email, password })
    expect(loginRes.status).toBe(200)
    const loginJson = await loginRes.json()
    expect(loginJson).toHaveProperty('access_token')
    const token = loginJson.access_token

    const payload = {
      title: 'Frontend IT product',
      description: 'Created by an integration test (client side).',
      category: 'electronics',
      price: 25.0,
      condition: 'New',
    }

    const createRes = await postJson(`${INVENTORY_BASE_URL}/api/v1/products`, payload, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    const createBody = await createRes.json()
    expect(createRes.status).toBe(201)
    expect(createBody).toHaveProperty('id')
    expect(createBody).toHaveProperty('seller_id')
  })
})

