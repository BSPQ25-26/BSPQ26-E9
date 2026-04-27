import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BaseButtonStub, BaseCardStub, flushPromises } from '@/test/stubs'
import ProductDetailView from '@/views/ProductDetailView.vue'

const routerState = vi.hoisted(() => ({
  route: {
    params: {
      id: '42',
    },
  },
}))

const authState = vi.hoisted(() => ({
  token: {
    value: '',
  },
  user: {
    value: {
      email: 'buyer@example.com',
    },
  },
}))

const productState = vi.hoisted(() => ({
  buyProduct: vi.fn(),
  cancelReservation: vi.fn(),
  getProductById: vi.fn(),
  reserveProduct: vi.fn(),
  resolveProductImageUrl: vi.fn((image) => image),
}))

const toastState = vi.hoisted(() => ({
  success: vi.fn(),
}))

const walletState = vi.hoisted(() => ({
  fetchBalance: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => routerState.route,
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => authState,
}))

vi.mock('@/stores/toast', () => ({
  useToastStore: () => toastState,
}))

vi.mock('@/stores/wallet', () => ({
  useWalletStore: () => walletState,
}))

vi.mock('@/services/product.service', () => ({
  buyProduct: productState.buyProduct,
  cancelReservation: productState.cancelReservation,
  getProductById: productState.getProductById,
  reserveProduct: productState.reserveProduct,
  resolveProductImageUrl: productState.resolveProductImageUrl,
}))

const productFactory = (overrides = {}) => ({
  id: 42,
  title: 'Oak side table',
  description: 'Solid oak with a drawer and light wear on the top.',
  category: 'Furniture',
  condition: 'Good',
  price: 149.99,
  state: 'Available',
  seller_id: 'seller@example.com',
  transaction_product_id: 4242,
  created_at: '2026-04-01T12:00:00Z',
  images: ['/uploads/table-front.png', '/uploads/table-detail.png'],
  ...overrides,
})

const mountView = () =>
  mount(ProductDetailView, {
    global: {
      stubs: {
        BaseButton: BaseButtonStub,
        BaseCard: BaseCardStub,
      },
    },
  })

const findButtonByText = (wrapper, text) =>
  wrapper.findAll('button').find((button) => button.text() === text)

describe('ProductDetailView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routerState.route = {
      params: {
        id: '42',
      },
    }
    authState.token.value = ''
    authState.user.value = {
      email: 'buyer@example.com',
    }
    walletState.fetchBalance.mockResolvedValue({})
  })

  it('renders product details, gallery images, and seller info', async () => {
    productState.getProductById.mockResolvedValueOnce(productFactory())

    const wrapper = mountView()
    await flushPromises()

    expect(productState.getProductById).toHaveBeenCalledWith('42')
    expect(wrapper.text()).toContain('Oak side table')
    expect(wrapper.text()).toContain('$149.99')
    expect(wrapper.text()).toContain('Solid oak with a drawer')
    expect(wrapper.text()).toContain('seller@example.com')
    expect(wrapper.text()).toContain('Product ID')
    expect(wrapper.find('img').attributes('src')).toBe('/uploads/table-front.png')
  })

  it('falls back to the gallery placeholder when a product image is missing', async () => {
    productState.getProductById.mockResolvedValueOnce(
      productFactory({
        images: ['/uploads/missing.png'],
      }),
    )

    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('img').trigger('error')
    await flushPromises()

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('.gallery-placeholder').text()).toBe('O')
  })

  it('shows Edit when the current user is the seller', async () => {
    authState.user.value = {
      email: 'seller@example.com',
    }
    productState.getProductById.mockResolvedValueOnce(productFactory())

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Edit')
    expect(wrapper.text()).not.toContain('Reserve')
    expect(wrapper.text()).not.toContain('Buy')
  })

  it('reserves an available product for non-sellers and switches to Buy', async () => {
    productState.getProductById.mockResolvedValueOnce(productFactory())
    productState.reserveProduct.mockResolvedValueOnce({
      state: 'Reserved',
    })

    const wrapper = mountView()
    await flushPromises()

    await findButtonByText(wrapper, 'Reserve').trigger('click')
    await flushPromises()

    expect(productState.reserveProduct).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 42,
        transaction_product_id: 4242,
      }),
    )
    expect(toastState.success).toHaveBeenCalledWith('Item reserved.')
    expect(wrapper.text()).toContain('Buy')
    expect(wrapper.text()).toContain('Cancel reservation')
  })

  it('shows buy and cancellation actions for a reserved product', async () => {
    productState.getProductById.mockResolvedValueOnce(
      productFactory({
        state: 'Reserved',
      }),
    )
    productState.buyProduct.mockResolvedValueOnce({})

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Buy')
    expect(wrapper.text()).toContain('Cancel reservation')

    await findButtonByText(wrapper, 'Buy').trigger('click')
    await flushPromises()

    const dialog = wrapper.find('[role="dialog"]')

    expect(productState.buyProduct).not.toHaveBeenCalled()
    expect(dialog.exists()).toBe(true)
    expect(dialog.text()).toContain('Confirm purchase')
    expect(dialog.text()).toContain('deduct')
    expect(dialog.text()).toContain('$149.99')

    await findButtonByText(wrapper, 'Confirm purchase').trigger('click')
    await flushPromises()

    expect(productState.buyProduct).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 42,
        transaction_product_id: 4242,
      }),
    )
    expect(walletState.fetchBalance).toHaveBeenCalled()
    expect(toastState.success).toHaveBeenCalledWith('Purchase completed.')
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Sold')
  })

  it('cancels an active reservation and switches back to Reserve', async () => {
    productState.getProductById.mockResolvedValueOnce(
      productFactory({
        state: 'Reserved',
      }),
    )
    productState.cancelReservation.mockResolvedValueOnce({
      state: 'Available',
    })

    const wrapper = mountView()
    await flushPromises()

    await findButtonByText(wrapper, 'Cancel reservation').trigger('click')
    await flushPromises()

    expect(productState.cancelReservation).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 42,
        transaction_product_id: 4242,
      }),
    )
    expect(toastState.success).toHaveBeenCalledWith('Reservation cancelled.')
    expect(wrapper.text()).toContain('Reserve')
    expect(wrapper.text()).not.toContain('Buy')
  })

  it('cancels the buy confirmation without purchasing', async () => {
    productState.getProductById.mockResolvedValueOnce(
      productFactory({
        state: 'Reserved',
      }),
    )

    const wrapper = mountView()
    await flushPromises()

    await findButtonByText(wrapper, 'Buy').trigger('click')
    await flushPromises()

    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)

    await findButtonByText(wrapper, 'Cancel').trigger('click')
    await flushPromises()

    expect(productState.buyProduct).not.toHaveBeenCalled()
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('does not offer checkout actions for listings without transaction backing', async () => {
    productState.getProductById.mockResolvedValueOnce(
      productFactory({
        transaction_product_id: null,
      }),
    )

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Checkout unavailable')
    expect(wrapper.text()).not.toContain('Reserve')
    expect(wrapper.text()).not.toContain('Buy')
  })
})
