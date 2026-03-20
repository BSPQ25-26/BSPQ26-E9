import { inventoryApiClient } from '@/services/api'

const RECENT_PRODUCTS_LIMIT = 6
const RECENT_PRODUCTS_STORAGE_KEY = 'wallabot_recent_products'

const hasStorage = () => typeof window !== 'undefined' && Boolean(window.localStorage)

const normalizeProduct = (product) => {
  if (!product || typeof product !== 'object') {
    return null
  }

  return {
    id: product.id ?? null,
    title: product.title ?? '',
    description: product.description ?? '',
    category: product.category ?? '',
    price: typeof product.price === 'number' ? product.price : Number(product.price) || 0,
    condition: product.condition ?? '',
    state: product.state ?? 'Available',
    created_at: product.created_at ?? null,
  }
}

const readRecentProducts = () => {
  if (!hasStorage()) {
    return []
  }

  try {
    const parsed = JSON.parse(window.localStorage.getItem(RECENT_PRODUCTS_STORAGE_KEY) || '[]')

    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed.map(normalizeProduct).filter(Boolean)
  } catch {
    return []
  }
}

const writeRecentProducts = (products) => {
  if (!hasStorage()) {
    return
  }

  window.localStorage.setItem(RECENT_PRODUCTS_STORAGE_KEY, JSON.stringify(products))
}

export const getRecentProducts = () => readRecentProducts()

export const rememberRecentProduct = (product) => {
  const normalized = normalizeProduct(product)

  if (!normalized) {
    return readRecentProducts()
  }

  const nextProducts = [
    normalized,
    ...readRecentProducts().filter((entry) => entry.id !== normalized.id),
  ].slice(0, RECENT_PRODUCTS_LIMIT)

  writeRecentProducts(nextProducts)
  return nextProducts
}

export const createProduct = async (payload) => {
  const { data } = await inventoryApiClient.post('/products', payload)
  rememberRecentProduct(data)
  return data
}
