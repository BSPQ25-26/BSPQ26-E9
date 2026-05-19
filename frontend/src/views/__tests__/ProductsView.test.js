import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { i18n } from '@/i18n'
import {
  BaseButtonStub,
  BaseCardStub,
  BaseInputStub,
  deferred,
  flushPromises,
} from '@/test/stubs'
import ProductsView from '@/views/ProductsView.vue'

const routerState = vi.hoisted(() => ({
  route: {
    name: 'products',
    query: {},
  },
  router: {
    replace: vi.fn(({ query }) => {
      routerState.route.query = query || {}
    }),
  },
}))

const productState = vi.hoisted(() => ({
  listProducts: vi.fn(),
  resolveProductImageUrl: vi.fn((imageUrl) => imageUrl),
}))

vi.mock('vue-router', () => ({
  useRoute: () => routerState.route,
  useRouter: () => routerState.router,
}))

vi.mock('@/services/product.service', () => ({
  listProducts: productState.listProducts,
  resolveProductImageUrl: productState.resolveProductImageUrl,
}))

const catalogProduct = {
  category: 'Electronics',
  condition: 'Good',
  description: 'Clean screen and charger included.',
  id: 1,
  price: 199,
  seller_id: 'seller@example.com',
  state: 'Available',
  title: 'Tablet',
}

const conditionProducts = [
  {
    category: 'Furniture',
    condition: 'New',
    description: 'Factory sealed desk lamp.',
    id: 10,
    price: 45,
    state: 'Available',
    title: 'Desk lamp',
  },
  {
    category: 'Furniture',
    condition: 'Good',
    description: 'Comfortable chair with light wear.',
    id: 11,
    price: 75,
    state: 'Available',
    title: 'Reading chair',
  },
  {
    category: 'Electronics',
    condition: 'Poor',
    description: 'Scratched tablet for parts.',
    id: 12,
    price: 25,
    state: 'Reserved',
    title: 'Parts tablet',
  },
]

const makeProducts = (count) =>
  Array.from({ length: count }, (_, index) => {
    const id = index + 1
    const states = ['Available', 'Reserved', 'Sold']

    return {
      category: 'Furniture',
      condition: id % 2 === 0 ? 'Good' : 'Like New',
      description: `Catalog item ${id}`,
      id,
      images: [`/uploads/product-${id}.jpg`],
      price: 10 + id,
      seller_id: 'seller@example.com',
      state: states[index % states.length],
      title: `Product ${id}`,
    }
  })

const mountView = () =>
  mount(ProductsView, {
    global: {
      plugins: [i18n],
      stubs: {
        BaseButton: BaseButtonStub,
        BaseCard: BaseCardStub,
        BaseInput: BaseInputStub,
      },
    },
  })

describe('ProductsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routerState.route = {
      name: 'products',
      query: {},
    }
    i18n.global.locale.value = 'en'
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows product skeleton rows while the catalog is fetching', () => {
    const pendingRequest = deferred()
    productState.listProducts.mockReturnValueOnce(pendingRequest.promise)

    const wrapper = mountView()

    expect(wrapper.findAll('.product-item--skeleton')).toHaveLength(4)
    expect(wrapper.text()).toContain('Refreshing catalog...')
  })

  it('shows an empty state when active filters return no products', async () => {
    vi.useFakeTimers()
    productState.listProducts
      .mockResolvedValueOnce([catalogProduct])
      .mockResolvedValueOnce([])

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Tablet')

    await wrapper.find('select[name="category"]').setValue('Furniture')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    expect(productState.listProducts).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('No products found')
    expect(wrapper.text()).toContain('Try changing or clearing the current filters.')
  })

  it('supports selecting multiple product states without sending unsupported API state filters', async () => {
    vi.useFakeTimers()
    productState.listProducts.mockResolvedValueOnce(makeProducts(3))

    const wrapper = mountView()
    await flushPromises()

    const stateFilters = wrapper.findAll('input[name="state"]')
    await stateFilters[0].setChecked(true)
    await stateFilters[1].setChecked(true)

    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    const visibleProductTitles = wrapper
      .findAll('.product-card__title')
      .map((title) => title.text())

    expect(productState.listProducts).toHaveBeenCalledTimes(1)
    expect(productState.listProducts).toHaveBeenLastCalledWith({
      category: '',
      condition: [],
      maxPrice: '',
      minPrice: '',
      state: '',
    })
    expect(visibleProductTitles).toEqual(['Product 1', 'Product 2'])
  })

  it('hydrates filters from the URL and normalizes unsupported values', async () => {
    routerState.route.query = {
      category: 'Furniture',
      condition: ['Good', 'Broken', 'Poor'],
      max_price: '100',
      min_price: '10',
      q: 'chair',
      state: ['Available', 'Archived'],
    }
    productState.listProducts.mockResolvedValueOnce(conditionProducts)

    const wrapper = mountView()
    await flushPromises()

    expect(productState.listProducts).toHaveBeenCalledWith({
      category: 'Furniture',
      condition: ['Good', 'Poor'],
      maxPrice: '100',
      minPrice: '10',
      state: '',
    })
    expect(wrapper.find('input[name="condition"][value="Good"]').element.checked).toBe(true)
    expect(wrapper.find('input[name="condition"][value="Poor"]').element.checked).toBe(true)
    expect(wrapper.find('input[name="state"][value="Available"]').element.checked).toBe(true)
    expect(wrapper.find('input[name="q"]').element.value).toBe('chair')
    expect(wrapper.findAll('.product-card__title').map((title) => title.text())).toEqual([
      'Reading chair',
    ])
  })

  it('sends a single selected condition to the catalog API', async () => {
    vi.useFakeTimers()
    productState.listProducts
      .mockResolvedValueOnce(conditionProducts)
      .mockResolvedValueOnce([conditionProducts[1]])

    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('input[name="condition"][value="Good"]').setChecked(true)
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    expect(productState.listProducts).toHaveBeenLastCalledWith({
      category: '',
      condition: ['Good'],
      maxPrice: '',
      minPrice: '',
      state: '',
    })
    expect(routerState.router.replace).toHaveBeenLastCalledWith({
      name: 'products',
      query: {
        condition: ['Good'],
      },
    })
  })

  it('sends multiple selected conditions to the catalog API and filters the response', async () => {
    vi.useFakeTimers()
    productState.listProducts
      .mockResolvedValueOnce(conditionProducts)
      .mockResolvedValueOnce(conditionProducts)

    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('input[name="condition"][value="Good"]').setChecked(true)
    await wrapper.find('input[name="condition"][value="Poor"]').setChecked(true)
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    expect(productState.listProducts).toHaveBeenLastCalledWith({
      category: '',
      condition: ['Good', 'Poor'],
      maxPrice: '',
      minPrice: '',
      state: '',
    })
    expect(wrapper.findAll('.product-card__title').map((title) => title.text())).toEqual([
      'Reading chair',
      'Parts tablet',
    ])
  })

  it('filters search text in the client and persists q in the URL', async () => {
    vi.useFakeTimers()
    productState.listProducts.mockResolvedValueOnce(conditionProducts)

    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('input[name="q"]').setValue('chair')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    expect(productState.listProducts).toHaveBeenCalledTimes(1)
    expect(productState.listProducts).toHaveBeenLastCalledWith({
      category: '',
      condition: [],
      maxPrice: '',
      minPrice: '',
      state: '',
    })
    expect(routerState.router.replace).toHaveBeenLastCalledWith({
      name: 'products',
      query: {
        q: 'chair',
      },
    })
    expect(wrapper.findAll('.product-card__title').map((title) => title.text())).toEqual([
      'Reading chair',
    ])
  })

  it('renders paginated product cards with catalog details', async () => {
    productState.listProducts.mockResolvedValueOnce(makeProducts(10))
    const wrapper = mountView()

    await flushPromises()

    expect(productState.listProducts).toHaveBeenCalledTimes(1)
    expect(wrapper.findAll('.product-card')).toHaveLength(8)
    expect(wrapper.text()).toContain('Product 1')
    expect(wrapper.text()).toContain('$11.00')
    expect(wrapper.text()).toContain('Available')
    expect(wrapper.find('.condition-badge').text()).toBe('Like New')
    expect(wrapper.find('.condition-badge').classes()).toContain('condition-badge--like-new')
    expect(wrapper.text()).not.toContain('No ratings yet')
    expect(wrapper.text()).toContain('Showing 1-8 of 10')
    expect(productState.resolveProductImageUrl).toHaveBeenCalledWith('/uploads/product-1.jpg')
    expect(wrapper.find('img').attributes('src')).toBe('/uploads/product-1.jpg')
  })

  it('falls back to the product initial when a catalog image is missing', async () => {
    productState.listProducts.mockResolvedValueOnce([
      {
        ...catalogProduct,
        images: ['/uploads/missing.png'],
      },
    ])

    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('img').trigger('error')
    await flushPromises()

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('.product-card__placeholder').text()).toBe('T')
  })

  it('moves through catalog pages with the pagination controls', async () => {
    productState.listProducts.mockResolvedValueOnce(makeProducts(10))
    const wrapper = mountView()

    await flushPromises()
    await wrapper.find('[aria-label="Go to next products page"]').trigger('click')

    expect(wrapper.text()).toContain('Product 9')
    expect(wrapper.text()).toContain('Product 10')
    expect(wrapper.text()).toContain('Showing 9-10 of 10')
    expect(wrapper.findAll('.product-card')).toHaveLength(2)
  })
})
