import { inventoryApiClient, transactionApiClient } from '@/services/api'

const TRANSACTION_PRODUCT_MAP_STORAGE_KEY = 'wallabot_transaction_product_map'
const CHECKOUT_STATE_STORAGE_KEY = 'wallabot_checkout_state_map'

const stateLabelByKey = {
  available: 'Available',
  reserved: 'Reserved',
  sold: 'Sold',
}

const trimTrailingSlashes = (value = '') => value.replace(/\/+$/, '')

const hasStorage = () => typeof window !== 'undefined' && Boolean(window.localStorage)

const readStorageMap = (storageKey) => {
  if (!hasStorage()) {
    return {}
  }

  try {
    const parsed = JSON.parse(window.localStorage.getItem(storageKey) || '{}')
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

const writeStorageMap = (storageKey, mapping) => {
  if (!hasStorage()) {
    return
  }

  window.localStorage.setItem(storageKey, JSON.stringify(mapping))
}

const readTransactionProductMap = () => readStorageMap(TRANSACTION_PRODUCT_MAP_STORAGE_KEY)

const writeTransactionProductMap = (mapping) =>
  writeStorageMap(TRANSACTION_PRODUCT_MAP_STORAGE_KEY, mapping)

const readCheckoutStateMap = () => readStorageMap(CHECKOUT_STATE_STORAGE_KEY)

const writeCheckoutStateMap = (mapping) => writeStorageMap(CHECKOUT_STATE_STORAGE_KEY, mapping)

const getMappedTransactionProductId = (inventoryProductId) => {
  const normalizedId = String(inventoryProductId ?? '')

  if (!normalizedId) {
    return null
  }

  return readTransactionProductMap()[normalizedId] || null
}

const rememberTransactionProductId = (inventoryProductId, transactionProductId) => {
  const normalizedInventoryId = String(inventoryProductId ?? '')
  const normalizedTransactionId = transactionProductId ?? null

  if (!normalizedInventoryId || !normalizedTransactionId) {
    return
  }

  writeTransactionProductMap({
    ...readTransactionProductMap(),
    [normalizedInventoryId]: normalizedTransactionId,
  })
}

const getStoredCheckoutState = (inventoryProductId) => {
  const normalizedId = String(inventoryProductId ?? '')

  if (!normalizedId) {
    return null
  }

  const state = readCheckoutStateMap()[normalizedId]
  return state ? normalizeProductState(state) : null
}

const rememberCheckoutState = (inventoryProductId, state) => {
  const normalizedInventoryId = String(inventoryProductId ?? '')
  const normalizedState = normalizeProductState(state)

  if (!normalizedInventoryId || !normalizedState) {
    return
  }

  writeCheckoutStateMap({
    ...readCheckoutStateMap(),
    [normalizedInventoryId]: normalizedState,
  })
}

const isLocalDevApi = (baseURL) => {
  if (!import.meta.env.DEV || !baseURL) {
    return false
  }

  try {
    const url = new URL(baseURL)
    return ['localhost', '127.0.0.1'].includes(url.hostname)
  } catch {
    return false
  }
}

const normalizeImages = (images, fallbackImage) => {
  const normalizedImages = Array.isArray(images) ? images : []
  const nextImages = fallbackImage ? [...normalizedImages, fallbackImage] : normalizedImages

  return nextImages
    .map((image) => (typeof image === 'string' ? image.trim() : ''))
    .filter(Boolean)
}

export const normalizeProduct = (product) => {
  if (!product || typeof product !== 'object') {
    return null
  }

  const storedCheckoutState = getStoredCheckoutState(product.id)

  return {
    id: product.id ?? null,
    title: product.title ?? '',
    description: product.description ?? '',
    category: product.category ?? '',
    price: typeof product.price === 'number' ? product.price : Number(product.price) || 0,
    condition: product.condition ?? '',
    state: normalizeProductState(product.checkout_state ?? storedCheckoutState ?? product.state),
    seller_id: product.seller_id ?? product.owner_id ?? '',
    transaction_product_id:
      product.transaction_product_id ??
      product.transactionProductId ??
      getMappedTransactionProductId(product.id),
    created_at: product.created_at ?? null,
    updated_at: product.updated_at ?? null,
    images: normalizeImages(product.images, product.image_url || product.image),
  }
}

const normalizeProducts = (products) => {
  if (!Array.isArray(products)) {
    return []
  }

  return products.map(normalizeProduct).filter(Boolean)
}

export const normalizeProductState = (value) => {
  const key = String(value || 'Available').trim().toLowerCase()

  return stateLabelByKey[key] || String(value || 'Available').trim() || 'Available'
}

const addStringFilter = (params, key, value) => {
  const normalizedValue = typeof value === 'string' ? value.trim() : value

  if (normalizedValue !== '' && normalizedValue !== null && normalizedValue !== undefined) {
    params[key] = normalizedValue
  }
}

const addPriceFilter = (params, key, value) => {
  if (value === '' || value === null || value === undefined) {
    return
  }

  const normalizedValue = Number(value)

  if (!Number.isNaN(normalizedValue)) {
    params[key] = normalizedValue
  }
}

export const normalizeProductFilters = (filters = {}) => {
  const params = {}

  addStringFilter(params, 'state', filters.state)
  addStringFilter(params, 'category', filters.category)
  addStringFilter(params, 'condition', filters.condition)
  addPriceFilter(params, 'min_price', filters.min_price ?? filters.minPrice)
  addPriceFilter(params, 'max_price', filters.max_price ?? filters.maxPrice)

  return params
}

export const listProducts = async (filters = {}) => {
  const { data } = await inventoryApiClient.get('/products', {
    params: normalizeProductFilters(filters),
  })

  const products = normalizeProducts(data)
  return Promise.all(products.map(syncProductCheckoutState))
}

export const getProductById = async (productId) => {
  const products = await listProducts()
  const product = products.find((item) => String(item.id) === String(productId))

  if (product) {
    return product
  }

  try {
    const { data } = await inventoryApiClient.get(`/products/${productId}`)
    return syncProductCheckoutState(normalizeProduct(data))
  } catch (error) {
    if (error?.response?.status !== 403) {
      throw error
    }

    throw error
  }
}

export const resolveProductImageUrl = (imageUrl) => {
  const trimmedImageUrl = typeof imageUrl === 'string' ? imageUrl.trim() : ''

  if (!trimmedImageUrl) {
    return ''
  }

  if (/^(?:[a-z][a-z\d+\-.]*:|\/\/)/i.test(trimmedImageUrl)) {
    return trimmedImageUrl
  }

  const normalizedPath = trimmedImageUrl.startsWith('/') ? trimmedImageUrl : `/${trimmedImageUrl}`
  const inventoryBaseUrl = import.meta.env.VITE_API_INVENTORY_URL || import.meta.env.VITE_API_BASE_URL || ''

  if (inventoryBaseUrl && !isLocalDevApi(inventoryBaseUrl)) {
    return `${trimTrailingSlashes(inventoryBaseUrl)}${normalizedPath}`
  }

  return normalizedPath
}

export const createProduct = async (payload) => {
  const { data } = await inventoryApiClient.post('/products', payload)

  const { data: transactionProduct } = await transactionApiClient.post('/products/', {
    title: payload.title,
    description: payload.description,
    category: payload.category,
    price: payload.price,
  })

  rememberTransactionProductId(data?.id, transactionProduct?.id)
  rememberCheckoutState(data?.id, transactionProduct?.state || 'Available')

  return normalizeProduct({
    ...data,
    transaction_product_id: transactionProduct?.id,
  })
}

export const updateProduct = async (productId, payload) => {
  const { data } = await inventoryApiClient.put(`/products/${productId}`, payload)
  return data
}

export const deleteProduct = async (productId) => {
  await inventoryApiClient.delete(`/products/${productId}`)
}

export const uploadProductImage = async (productId, file) => {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await inventoryApiClient.post(`/products/${productId}/images`, formData)

  return data
}

const getTransactionProductId = (productOrId) => {
  if (productOrId && typeof productOrId === 'object') {
    return productOrId.transaction_product_id || getMappedTransactionProductId(productOrId.id)
  }

  return getMappedTransactionProductId(productOrId)
}

const getInventoryProductId = (productOrId) => {
  if (productOrId && typeof productOrId === 'object') {
    return productOrId.id
  }

  return productOrId
}

const requireTransactionProductId = (productOrId) => {
  const transactionProductId = getTransactionProductId(productOrId)

  if (!transactionProductId) {
    throw new Error('This listing is not connected to checkout yet.')
  }

  return transactionProductId
}

const isAlreadyReservedTransitionError = (error) => {
  const detail = String(error?.response?.data?.detail || '')

  return (
    error?.response?.status === 400 &&
    detail.includes('ProductState.RESERVED') &&
    detail.includes('to ProductState.RESERVED')
  )
}

const updateStoredCheckoutState = (productOrId, state) => {
  rememberCheckoutState(getInventoryProductId(productOrId), state)
}

export const syncProductCheckoutState = async (product) => {
  if (!product?.transaction_product_id) {
    return product
  }

  try {
    const { data } = await transactionApiClient.get(`/products/${product.transaction_product_id}`)
    const state = normalizeProductState(data?.state)

    rememberCheckoutState(product.id, state)

    return {
      ...product,
      state,
      transaction_product_id: data?.id ?? product.transaction_product_id,
    }
  } catch (error) {
    if ([401, 403].includes(error?.response?.status)) {
      throw error
    }

    return product
  }
}

export const reserveProduct = async (productOrId) => {
  const transactionProductId = requireTransactionProductId(productOrId)

  try {
    const { data } = await transactionApiClient.post(`/products/${transactionProductId}/reserve`)
    updateStoredCheckoutState(productOrId, data?.state || 'Reserved')
    return data
  } catch (error) {
    if (isAlreadyReservedTransitionError(error)) {
      updateStoredCheckoutState(productOrId, 'Reserved')
      return {
        product_id: transactionProductId,
        state: 'Reserved',
      }
    }

    throw error
  }
}

export const buyProduct = async (productOrId) => {
  const transactionProductId = requireTransactionProductId(productOrId)
  const { data } = await transactionApiClient.post(`/products/${transactionProductId}/buy`)
  updateStoredCheckoutState(productOrId, 'Sold')
  return data
}

export const cancelReservation = async (productOrId) => {
  const transactionProductId = requireTransactionProductId(productOrId)
  const { data } = await transactionApiClient.post(
    `/products/${transactionProductId}/cancel-reservation`,
  )
  updateStoredCheckoutState(productOrId, data?.state || 'Available')
  return data
}
