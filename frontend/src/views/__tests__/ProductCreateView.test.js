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
  },
}))

const productState = vi.hoisted(() => ({
  createProduct: vi.fn(),
}))

const toastState = vi.hoisted(() => ({
  success: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: routerState.push,
  }),
}))

vi.mock('@/services/product.service', () => ({
  createProduct: productState.createProduct,
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

describe('ProductCreateView', () => {
  beforeEach(() => {
    routerState.route = {
      fullPath: '/products/new/create',
    }
  })

  it('renders the create form with responsive grouped fields', () => {
    const wrapper = mountView()
    const form = wrapper.find('form')
    const fields = wrapper.findAll('label')

    expect(form.classes()).toContain('responsive-form')
    expect(form.classes()).toContain('responsive-form--desktop-two')
    expect(fields[0].classes()).toContain('form-field--full')
    expect(fields[1].classes()).toContain('form-field--full')
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

  it('submits the product, disables submit while pending, and redirects on success', async () => {
    const pendingRequest = deferred()
    productState.createProduct.mockReturnValueOnce(pendingRequest.promise)

    const wrapper = mountView()
    const inputs = wrapper.findAll('input')
    const textarea = wrapper.find('textarea')

    await inputs[0].setValue('Wooden side table')
    await textarea.setValue('Solid oak table with a few light marks on top.')
    await inputs[1].setValue('Furniture')
    await inputs[2].setValue('Used, good condition')
    await inputs[3].setValue('149.99')

    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.find('button[type=\"submit\"]').attributes('disabled')).toBeDefined()
    expect(productState.createProduct).toHaveBeenCalledWith({
      title: 'Wooden side table',
      description: 'Solid oak table with a few light marks on top.',
      category: 'Furniture',
      price: 149.99,
      condition: 'Used, good condition',
    })

    pendingRequest.resolve()
    await flushPromises()

    expect(toastState.success).toHaveBeenCalledWith('Your item is live.')
    expect(routerState.push).toHaveBeenCalledWith('/products')
  })
})
