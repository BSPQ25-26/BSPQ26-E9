import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  BaseButtonStub,
  BaseCardStub,
  BaseInputStub,
  deferred,
  flushPromises,
} from '@/test/stubs'
import ProductCreateView from '@/views/ProductCreateView.vue'

const routerState = vi.hoisted(() => ({
  push: vi.fn(),
  route: {
    fullPath: '/products/new/create',
    name: 'product-create',
    params: {
      id: 'new',
    },
  },
}))

const productState = vi.hoisted(() => ({
  createProduct: vi.fn(),
  deleteProduct: vi.fn(),
  getProductById: vi.fn(),
  updateProduct: vi.fn(),
  uploadProductImage: vi.fn(),
}))

const wallabotState = vi.hoisted(() => ({
  recommendProductPrice: vi.fn(),
  suggestProductCategory: vi.fn(),
}))

const toastState = vi.hoisted(() => ({
  error: vi.fn(),
  success: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => routerState.route,
  useRouter: () => ({
    push: routerState.push,
  }),
}))

vi.mock('@/services/product.service', () => ({
  createProduct: productState.createProduct,
  deleteProduct: productState.deleteProduct,
  getProductById: productState.getProductById,
  updateProduct: productState.updateProduct,
  uploadProductImage: productState.uploadProductImage,
}))

vi.mock('@/services/wallabot.service', () => ({
  recommendProductPrice: wallabotState.recommendProductPrice,
  suggestProductCategory: wallabotState.suggestProductCategory,
}))

vi.mock('@/stores/toast', () => ({
  useToastStore: () => toastState,
}))

const mountView = () =>
  mount(ProductCreateView, {
    global: {
      stubs: {
        BaseButton: BaseButtonStub,
        BaseCard: BaseCardStub,
        BaseInput: BaseInputStub,
      },
    },
  })

const fillRequiredFields = async (wrapper, overrides = {}) => {
  await wrapper.find('input[name="title"]').setValue(overrides.title || 'Wooden side table')
  await wrapper
    .find('textarea[name="description"]')
    .setValue(overrides.description || 'Solid oak table with a few light marks on top.')
  await wrapper.find('select[name="category"]').setValue(overrides.category || 'Furniture')
  await wrapper.find('select[name="condition"]').setValue(overrides.condition || 'Good')
  await wrapper.find('input[name="price"]').setValue(overrides.price || '149.99')
}

const findButtonByText = (wrapper, text) =>
  wrapper.findAll('button').find((button) => button.text() === text)

describe('ProductCreateView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routerState.route = {
      fullPath: '/products/new/create',
      name: 'product-create',
      params: {
        id: 'new',
      },
    }
    wallabotState.recommendProductPrice.mockResolvedValue({
      dataSource: 'test',
      priceRangeMax: 120,
      priceRangeMin: 80,
      recommendedPrice: 100,
    })
  })

  it('renders the create form with responsive grouped fields', () => {
    const wrapper = mountView()
    const form = wrapper.find('form')
    const fields = wrapper.findAll('label')

    expect(form.classes()).toContain('responsive-form')
    expect(form.classes()).toContain('responsive-form--desktop-two')
    expect(fields[0].classes()).toContain('form-field--full')
    expect(fields[1].classes()).toContain('form-field--full')
    expect(wrapper.find('.image-dropzone').exists()).toBe(true)
    expect(wrapper.find('input[name="category"]').exists()).toBe(false)
    expect(wrapper.findAll('select[name="category"] option').map((option) => option.text())).toContain(
      'Furniture',
    )
    expect(wrapper.findAll('select[name="condition"] option').map((option) => option.text())).toEqual([
      'Select condition',
      'New',
      'Like New',
      'Good',
      'Fair',
      'Poor',
    ])
  })

  it('shows inline validation errors when required fields are missing', async () => {
    const wrapper = mountView()

    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.text()).toContain('Enter the item name.')
    expect(wrapper.text()).toContain('Enter the details.')
    expect(wrapper.text()).toContain('Enter the category.')
    expect(wrapper.text()).toContain('Enter the condition.')
    expect(wrapper.text()).toContain('Enter a price.')
    expect(productState.createProduct).not.toHaveBeenCalled()
  })

  it('asks Wallabot for a category, then shows the recommended price range', async () => {
    const categoryRequest = deferred()
    const priceRequest = deferred()
    wallabotState.suggestProductCategory.mockReturnValueOnce(categoryRequest.promise)
    wallabotState.recommendProductPrice.mockReturnValueOnce(priceRequest.promise)

    const wrapper = mountView()

    await wrapper.find('input[name="title"]').setValue('Wooden side table')
    await wrapper
      .find('textarea[name="description"]')
      .setValue('Solid oak table with a few light marks on top.')
    await wrapper.find('select[name="condition"]').setValue('Good')
    await wrapper.find('.category-suggestion-button').trigger('click')

    expect(wallabotState.suggestProductCategory).toHaveBeenCalledWith({
      availableCategories: expect.arrayContaining(['Furniture']),
      title: 'Wooden side table',
      description: 'Solid oak table with a few light marks on top.',
    })
    expect(wrapper.find('.button-spinner').exists()).toBe(true)
    expect(wrapper.find('.category-suggestion-button').attributes('disabled')).toBeDefined()

    categoryRequest.resolve({
      confidence: 0.91,
      isNewCategory: false,
      suggestedCategory: 'Furniture',
    })
    await flushPromises()

    expect(wrapper.find('select[name="category"]').element.value).toBe('Furniture')
    expect(wrapper.find('.button-spinner').exists()).toBe(false)
    expect(wallabotState.recommendProductPrice).toHaveBeenCalledWith({
      condition: 'Good',
      description: 'Solid oak table with a few light marks on top.',
      title: 'Wooden side table',
    })
    expect(wrapper.find('[data-test="price-recommendation-helper"]').text()).toContain(
      'Checking recommended price range...',
    )

    priceRequest.resolve({
      dataSource: 'test',
      priceRangeMax: 120,
      priceRangeMin: 80,
      recommendedPrice: 100,
    })
    await flushPromises()

    const helperText = wrapper.find('[data-test="price-recommendation-helper"]').text()

    expect(helperText).toContain('Recommended range:')
    expect(helperText).toContain('80.00')
    expect(helperText).toContain('120.00')
  })

  it('submits the product, disables submit while pending, and redirects on success', async () => {
    const pendingRequest = deferred()
    productState.createProduct.mockReturnValueOnce(pendingRequest.promise)

    const wrapper = mountView()
    await fillRequiredFields(wrapper)

    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    expect(productState.createProduct).toHaveBeenCalledWith({
      title: 'Wooden side table',
      description: 'Solid oak table with a few light marks on top.',
      category: 'Furniture',
      price: 149.99,
      condition: 'Good',
    })

    pendingRequest.resolve()
    await flushPromises()

    expect(toastState.success).toHaveBeenCalledWith('Your item is live.')
    expect(routerState.push).toHaveBeenCalledWith('/products')
  })

  it('adds dropped images and uploads them after the product is created', async () => {
    const image = new File(['image'], 'table.png', { type: 'image/png' })
    productState.createProduct.mockResolvedValueOnce({ id: 42, images: [] })
    productState.uploadProductImage.mockResolvedValueOnce({ image_url: '/uploads/table.png' })

    const wrapper = mountView()

    await wrapper.find('.image-dropzone').trigger('drop', {
      dataTransfer: {
        files: [image],
      },
    })
    expect(wrapper.text()).toContain('table.png')

    await fillRequiredFields(wrapper)
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(productState.uploadProductImage).toHaveBeenCalledWith(42, image)
    expect(routerState.push).toHaveBeenCalledWith('/products')
  })

  it('shows a delete button in edit mode and deletes the product after confirmation', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValueOnce(true)
    productState.getProductById.mockResolvedValueOnce({
      id: 42,
      title: 'Oak side table',
      description: 'Solid oak with a drawer.',
      category: 'Furniture',
      condition: 'Good',
      price: 149.99,
      images: [],
    })
    productState.deleteProduct.mockResolvedValueOnce()
    routerState.route = {
      fullPath: '/products/42/edit',
      name: 'product-edit',
      params: {
        id: '42',
      },
    }

    const wrapper = mountView()
    await flushPromises()

    const deleteButton = findButtonByText(wrapper, 'Delete product')

    expect(deleteButton.exists()).toBe(true)

    await deleteButton.trigger('click')
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalledWith(
      'Delete this product? This action cannot be undone.',
    )
    expect(productState.deleteProduct).toHaveBeenCalledWith('42')
    expect(toastState.success).toHaveBeenCalledWith('Your item was deleted.')
    expect(routerState.push).toHaveBeenCalledWith('/products')

    confirmSpy.mockRestore()
  })
})
