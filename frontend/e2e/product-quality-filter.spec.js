import { expect, test } from '@playwright/test'
import {
  AUTH_TOKEN_STORAGE_KEY,
  catalogFixtures,
  cleanupTestData,
  createRunId,
  createTestEmail,
  registerAndLogin,
  seedCatalogProducts,
} from './helpers/backend.js'

const parseProductListRequest = (requestUrl) => {
  const url = new URL(requestUrl)

  return {
    category: url.searchParams.get('category') || '',
    conditions: url.searchParams.getAll('condition'),
  }
}

const waitForCatalogRefresh = (page) =>
  page.waitForResponse(
    (response) =>
      response.request().method() === 'GET' &&
      response.url().includes('/api/v1/products') &&
      response.ok(),
  )

test.describe('catalog filters against live backend', () => {
  let runId
  let email
  let token
  let titles

  test.beforeAll(async () => {
    runId = createRunId()
    email = createTestEmail(runId)
    token = await registerAndLogin(email)
    await seedCatalogProducts(runId, token)
    titles = catalogFixtures(runId).map((product) => product.title)
  })

  test.afterAll(async () => {
    if (email) {
      await cleanupTestData(email)
    }
  })

  test('filters catalog by product quality, combines filters, and persists URL state', async ({
    page,
  }) => {
    const productRequests = []

    page.on('request', (request) => {
      if (request.method() !== 'GET') {
        return
      }

      const requestUrl = request.url()

      if (!requestUrl.includes('/api/v1/products')) {
        return
      }

      productRequests.push(parseProductListRequest(requestUrl))
    })

    await page.addInitScript(
      ([storageKey, authToken]) => {
        window.localStorage.setItem(storageKey, authToken)
      },
      [AUTH_TOKEN_STORAGE_KEY, token],
    )

    const ourProductCards = () => page.locator('.product-card').filter({ hasText: runId })
    const ourTitles = () => ourProductCards().locator('.product-card__title')
    const expectOurTitles = async (expectedTitles) => {
      await expect
        .poll(async () => ourTitles().allTextContents())
        .toEqual(expectedTitles)
    }

    await page.goto('/#/products')

    await expect(page).toHaveURL(/\/products/)
    await page.getByText(/^Filters/).click()
    await page.locator('input[name="q"]').fill(runId)
    await expect.poll(async () => ourProductCards().count()).toBe(3)
    await expectOurTitles(titles)
    await expect(page.locator('.condition-badge--good').first()).toHaveText('Good')

    await Promise.all([
      waitForCatalogRefresh(page),
      page.locator('input[name="condition"][value="Good"]').check(),
    ])

    await expect.poll(() => productRequests.at(-1)?.conditions).toEqual(['Good'])
    await expectOurTitles([titles[1]])

    await Promise.all([
      waitForCatalogRefresh(page),
      page.locator('input[name="condition"][value="Poor"]').check(),
    ])

    await expect.poll(() => productRequests.at(-1)?.conditions).toEqual(['Good', 'Poor'])
    await expectOurTitles([titles[1], titles[2]])

    await Promise.all([
      waitForCatalogRefresh(page),
      page.locator('select[name="category"]').selectOption('Furniture'),
    ])

    await expect.poll(() => productRequests.at(-1)).toMatchObject({
      category: 'Furniture',
      conditions: ['Good', 'Poor'],
    })
    await expectOurTitles([titles[1]])

    const scopedSearch = `${runId} reading`
    await page.locator('input[name="q"]').fill(scopedSearch)

    await expect(page).toHaveURL(/condition=Good/)
    await expect(page).toHaveURL(/condition=Poor/)
    await expect(page).toHaveURL(/category=Furniture/)
    await expect(page).toHaveURL(new RegExp(`q=.*${runId}.*reading`))
    await expectOurTitles([titles[1]])

    await page.reload()
    await waitForCatalogRefresh(page)

    await expect(page.locator('input[name="condition"][value="Good"]')).toBeChecked()
    await expect(page.locator('input[name="condition"][value="Poor"]')).toBeChecked()
    await expect(page.locator('select[name="category"]')).toHaveValue('Furniture')
    await expect(page.locator('input[name="q"]')).toHaveValue(scopedSearch)
    await expectOurTitles([titles[1]])
  })
})
