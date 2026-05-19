import { expect, test } from '@playwright/test'

const productFixtures = [
  {
    id: 10,
    title: 'Desk lamp',
    description: 'Factory sealed desk lamp.',
    category: 'Furniture',
    condition: 'New',
    price: 45,
    state: 'Available',
    seller_id: 'seller@example.com',
    created_at: '2026-04-01T12:00:00Z',
    images: [],
  },
  {
    id: 11,
    title: 'Reading chair',
    description: 'Comfortable chair with light wear.',
    category: 'Furniture',
    condition: 'Good',
    price: 75,
    state: 'Available',
    seller_id: 'seller@example.com',
    created_at: '2026-04-02T12:00:00Z',
    images: [],
  },
  {
    id: 12,
    title: 'Parts tablet',
    description: 'Scratched tablet for parts.',
    category: 'Electronics',
    condition: 'Poor',
    price: 25,
    state: 'Reserved',
    seller_id: 'seller@example.com',
    created_at: '2026-04-03T12:00:00Z',
    images: [],
  },
]

const encodeJwtPart = (payload) => Buffer.from(JSON.stringify(payload)).toString('base64url')

const createUsableToken = () =>
  [
    encodeJwtPart({ alg: 'HS256', typ: 'JWT' }),
    encodeJwtPart({
      exp: Math.floor(Date.now() / 1000) + 3600,
      sub: 'e2e@example.com',
    }),
    'signature',
  ].join('.')

const filterProductsForRequest = (requestUrl) => {
  const url = new URL(requestUrl)
  const category = url.searchParams.get('category') || ''
  const conditions = url.searchParams.getAll('condition')
  const minPriceParam = url.searchParams.get('min_price')
  const maxPriceParam = url.searchParams.get('max_price')
  const minPrice = minPriceParam === null ? null : Number(minPriceParam)
  const maxPrice = maxPriceParam === null ? null : Number(maxPriceParam)

  return productFixtures.filter((product) => {
    if (category && product.category !== category) {
      return false
    }

    if (conditions.length && !conditions.includes(product.condition)) {
      return false
    }

    if (minPrice !== null && Number.isFinite(minPrice) && product.price < minPrice) {
      return false
    }

    if (maxPrice !== null && Number.isFinite(maxPrice) && product.price > maxPrice) {
      return false
    }

    return true
  })
}

test('filters catalog by product quality, combines filters, and persists URL state', async ({
  page,
}) => {
  const productRequests = []

  await page.addInitScript((token) => {
    window.localStorage.setItem('wallabot_auth_token', token)
  }, createUsableToken())

  await page.route('**/wallet/balance', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        balance: 100,
        user_id: 'e2e@example.com',
      }),
    })
  })

  await page.route('**/auth/protected', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        message: 'acceso permitido',
        user: 'e2e@example.com',
      }),
    })
  })

  await page.route('**/api/v1/products**', async (route) => {
    const url = new URL(route.request().url())

    productRequests.push({
      category: url.searchParams.get('category') || '',
      conditions: url.searchParams.getAll('condition'),
    })

    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify(filterProductsForRequest(route.request().url())),
    })
  })

  await page.route('**/users/resolve**', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        id: 7,
        username: 'seller@example.com',
        avg_rating: 4.5,
        active_listing_count: 2,
        member_since: '2026-04-01T00:00:00Z',
      }),
    })
  })

  await page.goto('/#/products')

  await expect(page.locator('.product-card__title')).toHaveText([
    'Desk lamp',
    'Reading chair',
    'Parts tablet',
  ])
  await expect(page.locator('.condition-badge--good')).toHaveText('Good')

  await page.getByText(/^Filters/).click()
  await page.locator('input[name="condition"][value="Good"]').check()

  await expect
    .poll(() => productRequests.at(-1)?.conditions)
    .toEqual(['Good'])
  await expect(page.locator('.product-card__title')).toHaveText(['Reading chair'])

  await page.locator('input[name="condition"][value="Poor"]').check()

  await expect
    .poll(() => productRequests.at(-1)?.conditions)
    .toEqual(['Good', 'Poor'])
  await expect(page.locator('.product-card__title')).toHaveText([
    'Reading chair',
    'Parts tablet',
  ])

  await page.locator('select[name="category"]').selectOption('Furniture')

  await expect
    .poll(() => productRequests.at(-1))
    .toMatchObject({
      category: 'Furniture',
      conditions: ['Good', 'Poor'],
    })
  await expect(page.locator('.product-card__title')).toHaveText(['Reading chair'])

  await page.locator('input[name="q"]').fill('chair')

  await expect(page).toHaveURL(/condition=Good/)
  await expect(page).toHaveURL(/condition=Poor/)
  await expect(page).toHaveURL(/category=Furniture/)
  await expect(page).toHaveURL(/q=chair/)
  await expect(page.locator('.product-card__title')).toHaveText(['Reading chair'])

  await page.reload()

  await expect(page.locator('input[name="condition"][value="Good"]')).toBeChecked()
  await expect(page.locator('input[name="condition"][value="Poor"]')).toBeChecked()
  await expect(page.locator('select[name="category"]')).toHaveValue('Furniture')
  await expect(page.locator('input[name="q"]')).toHaveValue('chair')
  await expect(page.locator('.product-card__title')).toHaveText(['Reading chair'])
})
