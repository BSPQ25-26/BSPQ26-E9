import { authRootApiClient } from '@/services/api'
import { normalizeProduct } from '@/services/product.service'

const profileCacheById = new Map()
const profileIdByUsername = new Map()
const pendingProfilesById = new Map()
const pendingProfilesByUsername = new Map()

const normalizeIdentifier = (value) => String(value ?? '').trim()
const normalizeLookupKey = (value) => normalizeIdentifier(value).toLowerCase()
const isNumericIdentifier = (value) => /^\d+$/.test(normalizeIdentifier(value))
const toNumberOrNull = (value) => {
  const numberValue = Number(value)

  return Number.isFinite(numberValue) ? numberValue : null
}
const toRatingOrNull = (value) => {
  if (value === null || value === undefined || value === '') {
    return null
  }

  const numberValue = Number(value)

  if (!Number.isFinite(numberValue)) {
    return null
  }

  return Math.min(Math.max(numberValue, 0), 5)
}

export const normalizeUserProfile = (profile, fallbackId = '') => {
  if (!profile || typeof profile !== 'object') {
    return null
  }

  const id = profile.id ?? profile.user_id ?? profile.userId ?? (
    isNumericIdentifier(fallbackId) ? Number(fallbackId) : null
  )
  const username = normalizeIdentifier(
    profile.username ?? profile.email ?? profile.name ?? fallbackId,
  )

  return {
    id,
    username,
    member_since:
      profile.member_since ??
      profile.memberSince ??
      profile.created_at ??
      profile.createdAt ??
      null,
    avg_rating: toRatingOrNull(
      profile.avg_rating ??
      profile.average_rating ??
      profile.averageRating ??
      profile.rating,
    ),
    active_listing_count: toNumberOrNull(
      profile.active_listing_count ??
      profile.activeListingCount ??
      profile.active_listings ??
      profile.activeListings,
    ),
  }
}

export const normalizeUserReview = (review) => {
  if (!review || typeof review !== 'object') {
    return null
  }

  return {
    reviewer_username:
      normalizeIdentifier(
        review.reviewer_username ??
        review.reviewerUsername ??
        review.from_username ??
        review.fromUser ??
        review.username,
      ) || 'Anonymous',
    stars: toRatingOrNull(review.stars) ?? 0,
    review_text:
      review.review_text ??
      review.reviewText ??
      review.text ??
      '',
    created_at:
      review.created_at ??
      review.createdAt ??
      review.date ??
      null,
  }
}

const rememberProfile = (profile) => {
  if (!profile) {
    return profile
  }

  if (profile.id !== null && profile.id !== undefined) {
    profileCacheById.set(String(profile.id), profile)
  }

  const usernameKey = normalizeLookupKey(profile.username)

  if (usernameKey && profile.id !== null && profile.id !== undefined) {
    profileIdByUsername.set(usernameKey, String(profile.id))
  }

  return profile
}

export const getUserProfile = async (userId) => {
  const normalizedUserId = normalizeIdentifier(userId)

  if (!normalizedUserId) {
    throw new Error('User id is required.')
  }

  if (profileCacheById.has(normalizedUserId)) {
    return profileCacheById.get(normalizedUserId)
  }

  if (pendingProfilesById.has(normalizedUserId)) {
    return pendingProfilesById.get(normalizedUserId)
  }

  const request = authRootApiClient
    .get(`/users/${encodeURIComponent(normalizedUserId)}/profile`, {
      skipAuth: true,
    })
    .then(({ data }) => rememberProfile(normalizeUserProfile(data, normalizedUserId)))
    .finally(() => {
      pendingProfilesById.delete(normalizedUserId)
    })

  pendingProfilesById.set(normalizedUserId, request)

  return request
}

export const getUserProfileByUsername = async (username) => {
  const normalizedUsername = normalizeIdentifier(username)
  const usernameKey = normalizeLookupKey(normalizedUsername)

  if (!usernameKey) {
    throw new Error('Username is required.')
  }

  const cachedId = profileIdByUsername.get(usernameKey)

  if (cachedId) {
    return getUserProfile(cachedId)
  }

  if (pendingProfilesByUsername.has(usernameKey)) {
    return pendingProfilesByUsername.get(usernameKey)
  }

  const request = authRootApiClient
    .get('/users/resolve', {
      params: {
        username: normalizedUsername,
      },
      skipAuth: true,
    })
    .then(({ data }) => rememberProfile(normalizeUserProfile(data, normalizedUsername)))
    .catch((error) => {
      if (error?.response?.status === 404) {
        return null
      }

      throw error
    })
    .finally(() => {
      pendingProfilesByUsername.delete(usernameKey)
    })

  pendingProfilesByUsername.set(usernameKey, request)

  return request
}

export const listUserReviews = async (userId, { page = 1, perPage = 5 } = {}) => {
  const normalizedUserId = normalizeIdentifier(userId)
  const normalizedPage = Math.max(Number(page) || 1, 1)
  const normalizedPerPage = Math.max(Number(perPage) || 5, 1)
  const { data } = await authRootApiClient.get(
    `/users/${encodeURIComponent(normalizedUserId)}/ratings`,
    {
      params: {
        skip: (normalizedPage - 1) * normalizedPerPage,
        limit: normalizedPerPage,
      },
      skipAuth: true,
    },
  )

  return (Array.isArray(data) ? data : [])
    .map(normalizeUserReview)
    .filter(Boolean)
}

export const listUserProducts = async (userId) => {
  const normalizedUserId = normalizeIdentifier(userId)

  if (!normalizedUserId) {
    return []
  }

  const { data } = await authRootApiClient.get(
    `/users/${encodeURIComponent(normalizedUserId)}/products`,
    {
      skipAuth: true,
    },
  )

  return (Array.isArray(data) ? data : [])
    .map(normalizeProduct)
    .filter(Boolean)
}

export const createUserRating = async ({
  reviewText = '',
  stars,
  toUserId,
  transactionId,
}) => {
  const { data } = await authRootApiClient.post('/ratings', {
    to_user_id: Number(toUserId),
    transaction_id: Number(transactionId),
    stars: Number(stars),
    review_text: normalizeIdentifier(reviewText) || null,
  })

  return data
}

export const resolveUserProfile = async (identifier) => {
  const normalizedIdentifier = normalizeIdentifier(identifier)

  if (!normalizedIdentifier) {
    return null
  }

  if (isNumericIdentifier(normalizedIdentifier)) {
    return getUserProfile(normalizedIdentifier)
  }

  const usernameKey = normalizeLookupKey(normalizedIdentifier)
  const cachedId = profileIdByUsername.get(usernameKey)

  if (cachedId) {
    return getUserProfile(cachedId)
  }

  return getUserProfileByUsername(normalizedIdentifier)
}

export const clearUserProfileCache = () => {
  profileCacheById.clear()
  profileIdByUsername.clear()
  pendingProfilesById.clear()
  pendingProfilesByUsername.clear()
}
