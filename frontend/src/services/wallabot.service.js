import { wallabotApiClient } from '@/services/api'

export const DEFAULT_WALLABOT_CATEGORIES = [
  'Electronics',
  'Clothing & Accessories',
  'Home & Garden',
  'Sports & Outdoors',
  'Vehicles',
  'Books & Media',
  'Toys & Games',
  'Health & Beauty',
  'Collectibles & Art',
  'Other',
]

export const isWallabotPriceRecommendationEnabled = () =>
  String(import.meta.env.VITE_WALLABOT_PRICE_ENABLED ?? 'true').trim().toLowerCase() !== 'false'

export const suggestProductCategory = async ({
  availableCategories = DEFAULT_WALLABOT_CATEGORIES,
  description,
  title,
}) => {
  const { data } = await wallabotApiClient.post('/category', {
    available_categories: availableCategories,
    description,
    title,
  })

  return {
    confidence: typeof data?.confidence === 'number' ? data.confidence : Number(data?.confidence) || 0,
    isNewCategory: Boolean(data?.is_new_category),
    suggestedCategory: data?.suggested_category || '',
  }
}

export const recommendProductPrice = async ({
  condition,
  description,
  title,
}) => {
  if (!isWallabotPriceRecommendationEnabled()) {
    return null
  }

  const { data } = await wallabotApiClient.post('/price', {
    condition,
    description,
    title,
  })

  return {
    dataSource: data?.data_source || '',
    priceRangeMax: Number(data?.price_range_max),
    priceRangeMin: Number(data?.price_range_min),
    recommendedPrice: Number(data?.recommended_price),
  }
}
