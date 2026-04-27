import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  BaseButtonStub,
  BaseCardStub,
  BaseInputStub,
  deferred,
  flushPromises,
} from '@/test/stubs'
import ProductsView from '@/views/ProductsView.vue'

const productState = vi.hoisted(() => ({
  listProducts: vi.fn(),
  resolveProductImageUrl: vi.fn((imageUrl) => imageUrl),
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
  state: 'Available',
  title: 'Tablet',
}

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
      state: states[index % states.length],
      title: `Product ${id}`,
    }
  })

const mountView = () =>
  mount(ProductsView, {
    global: {
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
    productState.listProducts
      .mockResolvedValueOnce(makeProducts(3))
      .mockResolvedValueOnce(makeProducts(3))

    const wrapper = mountView()
    await flushPromises()

    const stateFilters = wrapper.findAll('input[type="checkbox"]')
    await stateFilters[0].setChecked(true)
    await stateFilters[1].setChecked(true)

    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    const visibleProductTitles = wrapper
      .findAll('.product-card__title')
      .map((title) => title.text())

    expect(productState.listProducts).toHaveBeenLastCalledWith({
      category: '',
      condition: '',
      maxPrice: '',
      minPrice: '',
      state: '',
    })
    expect(visibleProductTitles).toEqual(['Product 1', 'Product 2'])
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
