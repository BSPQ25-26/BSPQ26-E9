<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import StarRating from '@/components/profile/StarRating.vue'
import { resolveProductImageUrl } from '@/services/product.service'
import {
  listUserProducts,
  listUserReviews,
  resolveUserProfile,
} from '@/services/user.service'
import {
  getConditionBadgeClass,
  getProductCondition,
} from '@/utils/product-condition'

const { t } = useI18n()
const route = useRoute()

const REVIEWS_PER_PAGE = 5

const profile = ref(null)
const profileProducts = ref([])
const reviews = ref([])
const failedProductImages = ref({})
const isLoadingProfile = ref(true)
const isLoadingProducts = ref(false)
const isLoadingReviews = ref(false)
const profileError = ref('')
const productsError = ref('')
const reviewsError = ref('')
const currentPage = ref(1)
let activeProfileRequestId = 0
let activeProductRequestId = 0
let activeReviewRequestId = 0

const profileIdentifier = computed(() => String(route.params.id || '').trim())
const profileUserId = computed(() => profile.value?.id ?? null)
const hasProfileUserId = computed(() => profileUserId.value !== null && profileUserId.value !== undefined)
const canGoPrevious = computed(() => currentPage.value > 1)
const canGoNext = computed(() => reviews.value.length === REVIEWS_PER_PAGE)
const displayName = computed(() => profile.value?.username || profileIdentifier.value || t('profile.unknownUser'))
const currencyFormatter = new Intl.NumberFormat('en-US', {
  currency: 'USD',
  style: 'currency',
})
const avatarInitials = computed(() => {
  const source = displayName.value.split('@')[0] || displayName.value
  const parts = source
    .split(/[\s._-]+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 2)

  return parts.map((part) => part.charAt(0).toUpperCase()).join('') || '?'
})
const formattedMemberSince = computed(() => {
  if (!profile.value?.member_since) {
    return t('profile.unknownDate')
  }

  const date = new Date(profile.value.member_since)

  if (Number.isNaN(date.getTime())) {
    return t('profile.unknownDate')
  }

  return date.toLocaleDateString()
})
const activeListingsLabel = computed(() => {
  const count = profile.value?.active_listing_count

  if (count === null || count === undefined) {
    return t('profile.unknownCount')
  }

  return t('profile.activeListingsCount', { count })
})

const formatReviewDate = (value) => {
  if (!value) {
    return t('profile.unknownDate')
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return t('profile.unknownDate')
  }

  return date.toLocaleDateString()
}

const getProductInitial = (product) => (product.title || product.category || '?').trim().charAt(0) || '?'
const getProductImage = (product) => {
  return (product.images || [])
    .map((image) => resolveProductImageUrl(image))
    .filter(Boolean)
    .find((image) => !failedProductImages.value[image]) || ''
}
const handleProductImageError = (image) => {
  if (!image) {
    return
  }

  failedProductImages.value = {
    ...failedProductImages.value,
    [image]: true,
  }
}
const getConditionClass = (product) => getConditionBadgeClass(getProductCondition(product))
const getProductDetailRoute = (product) => ({
  name: 'product-detail',
  params: {
    id: product.id,
  },
})

const loadProducts = async () => {
  const requestId = ++activeProductRequestId

  profileProducts.value = []
  productsError.value = ''

  if (!hasProfileUserId.value) {
    return
  }

  isLoadingProducts.value = true

  try {
    const nextProducts = await listUserProducts(profileUserId.value)

    if (requestId === activeProductRequestId) {
      profileProducts.value = nextProducts
    }
  } catch {
    if (requestId === activeProductRequestId) {
      productsError.value = t('profile.errorProducts')
    }
  } finally {
    if (requestId === activeProductRequestId) {
      isLoadingProducts.value = false
    }
  }
}

const loadReviews = async () => {
  const requestId = ++activeReviewRequestId

  reviews.value = []
  reviewsError.value = ''

  if (!hasProfileUserId.value) {
    return
  }

  isLoadingReviews.value = true

  try {
    const nextReviews = await listUserReviews(profileUserId.value, {
      page: currentPage.value,
      perPage: REVIEWS_PER_PAGE,
    })

    if (requestId === activeReviewRequestId) {
      reviews.value = nextReviews
    }
  } catch {
    if (requestId === activeReviewRequestId) {
      reviewsError.value = t('profile.errorReviews')
    }
  } finally {
    if (requestId === activeReviewRequestId) {
      isLoadingReviews.value = false
    }
  }
}

const loadProfile = async () => {
  const requestId = ++activeProfileRequestId
  const identifier = profileIdentifier.value

  isLoadingProfile.value = true
  profileError.value = ''
  productsError.value = ''
  reviewsError.value = ''
  profile.value = null
  profileProducts.value = []
  reviews.value = []
  failedProductImages.value = {}
  currentPage.value = 1

  try {
    const resolvedProfile = await resolveUserProfile(identifier)

    if (requestId !== activeProfileRequestId) {
      return
    }

    if (resolvedProfile) {
      profile.value = resolvedProfile
    } else {
      profile.value = {
        id: null,
        username: identifier,
        member_since: null,
        avg_rating: null,
        active_listing_count: null,
      }
      profileError.value = t('profile.limitedProfile')
    }
  } catch {
    if (requestId === activeProfileRequestId) {
      profile.value = null
      profileError.value = t('profile.errorLoad')
    }
  } finally {
    if (requestId === activeProfileRequestId) {
      isLoadingProfile.value = false
      await Promise.all([loadProducts(), loadReviews()])
    }
  }
}

const goToPage = (page) => {
  const nextPage = Math.max(1, page)

  if (nextPage === currentPage.value) {
    return
  }

  currentPage.value = nextPage
  loadReviews()
}

watch(profileIdentifier, loadProfile, { immediate: true })
</script>

<template>
  <section class="page-shell profile-shell">
    <BaseButton to="/products" variant="ghost">
      {{ $t('profile.back') }}
    </BaseButton>

    <p v-if="isLoadingProfile" class="status-message">
      {{ $t('profile.loading') }}
    </p>

    <p v-else-if="!profile" class="status-message error">
      {{ profileError }}
    </p>

    <template v-else>
      <BaseCard class="profile-card">
        <div class="profile-summary">
          <div class="profile-avatar" aria-hidden="true">
            {{ avatarInitials }}
          </div>

          <div class="profile-heading">
            <h1>{{ displayName }}</h1>
          </div>
        </div>

        <dl class="profile-metrics">
          <div>
            <dt>{{ $t('profile.memberSince') }}</dt>
            <dd>{{ formattedMemberSince }}</dd>
          </div>
          <div>
            <dt>{{ $t('profile.activeListings') }}</dt>
            <dd>{{ activeListingsLabel }}</dd>
          </div>
          <div>
            <dt>{{ $t('profile.rating') }}</dt>
            <dd>
              <StarRating
                :value="profile.avg_rating"
                size="sm"
                :empty-label="$t('rating.noRatings')"
              />
            </dd>
          </div>
        </dl>
      </BaseCard>

      <p v-if="profileError" class="status-message">
        {{ profileError }}
      </p>

      <BaseCard
        class="listings-card"
        :title="$t('profile.listingsTitle')"
        :description="$t('profile.listingsDesc')"
      >
        <p v-if="isLoadingProducts" class="status-message">
          {{ $t('profile.loadingProducts') }}
        </p>

        <p v-else-if="productsError" class="status-message error">
          {{ productsError }}
        </p>

        <div v-else-if="profileProducts.length" class="profile-product-grid">
          <article
            v-for="product in profileProducts"
            :key="product.id"
            class="profile-product-card"
          >
            <div class="profile-product-card__image" aria-hidden="true">
              <img
                v-if="getProductImage(product)"
                :alt="`${product.title || $t('products.untitled')} thumbnail`"
                :src="getProductImage(product)"
                @error="handleProductImageError(getProductImage(product))"
              />
              <span v-else class="profile-product-card__placeholder">
                {{ getProductInitial(product) }}
              </span>
            </div>

            <div class="profile-product-card__body">
              <div class="profile-product-card__heading">
                <h3>{{ product.title || $t('products.untitled') }}</h3>
                <p>{{ currencyFormatter.format(product.price) }}</p>
              </div>

              <div class="profile-product-card__meta">
                <span class="condition-badge" :class="getConditionClass(product)">
                  {{ getProductCondition(product) }}
                </span>
              </div>

              <BaseButton
                class="profile-product-card__link"
                size="sm"
                :to="getProductDetailRoute(product)"
                variant="ghost"
              >
                {{ $t('products.viewDetails') }}
              </BaseButton>
            </div>
          </article>
        </div>

        <div v-else class="empty-state">
          <h3>{{ $t('profile.noListingsTitle') }}</h3>
          <p class="muted">
            {{ hasProfileUserId ? $t('profile.noListingsDesc') : $t('profile.unavailableListings') }}
          </p>
        </div>
      </BaseCard>

      <BaseCard
        class="reviews-card"
        :title="$t('profile.reviewsTitle')"
        :description="$t('profile.reviewsDesc')"
      >
        <p v-if="isLoadingReviews" class="status-message">
          {{ $t('profile.loadingReviews') }}
        </p>

        <p v-else-if="reviewsError" class="status-message error">
          {{ reviewsError }}
        </p>

        <div v-else-if="reviews.length" class="reviews-list">
          <article
            v-for="review in reviews"
            :key="`${review.reviewer_username}-${review.created_at}-${review.stars}`"
            class="review-item"
          >
            <div class="review-item__header">
              <div>
                <h3>{{ review.reviewer_username }}</h3>
                <p class="muted">
                  {{ formatReviewDate(review.created_at) }}
                </p>
              </div>
              <StarRating :value="review.stars" size="sm" :show-value="false" />
            </div>
            <p class="review-item__text">
              {{ review.review_text || $t('profile.emptyReviewText') }}
            </p>
          </article>
        </div>

        <div v-else class="empty-state">
          <h3>{{ $t('profile.noReviewsTitle') }}</h3>
          <p class="muted">
            {{ hasProfileUserId ? $t('profile.noReviewsDesc') : $t('profile.unavailableReviews') }}
          </p>
        </div>

        <nav
          v-if="canGoPrevious || canGoNext"
          class="profile-pagination"
          :aria-label="$t('profile.reviewsTitle')"
        >
          <button
            class="pagination-button"
            type="button"
            :disabled="!canGoPrevious"
            @click="goToPage(currentPage - 1)"
          >
            {{ $t('products.prevPage') }}
          </button>
          <span class="profile-pagination__page">
            {{ $t('profile.page', { page: currentPage }) }}
          </span>
          <button
            class="pagination-button"
            type="button"
            :disabled="!canGoNext"
            @click="goToPage(currentPage + 1)"
          >
            {{ $t('products.nextPage') }}
          </button>
        </nav>
      </BaseCard>
    </template>
  </section>
</template>

<style scoped>
.profile-shell {
  align-items: start;
}

.profile-shell > :deep(.base-button) {
  justify-self: start;
}

.profile-card,
.listings-card,
.reviews-card {
  width: 100%;
}

.profile-summary {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-5);
}

.profile-avatar {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: clamp(4.5rem, 18vw, 7rem);
  aspect-ratio: 1;
  border-radius: 0.5rem;
  background: #1a1a1a;
  color: #f7f6f2;
  font-size: clamp(1.4rem, 5vw, 2.1rem);
  font-weight: 800;
}

.profile-heading {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
}

.profile-heading h1 {
  font-size: clamp(2.25rem, 8vw, 4.8rem);
  line-height: 0.95;
  letter-spacing: 0;
}

.profile-metrics {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 13rem), 1fr));
  margin: var(--space-6) 0 0;
}

.profile-metrics div {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4);
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 0.5rem;
  background: var(--color-surface-muted);
}

.profile-metrics dt,
.profile-metrics dd {
  margin: 0;
}

.profile-metrics dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: 800;
  text-transform: uppercase;
}

.profile-metrics dd {
  font-weight: 800;
  overflow-wrap: anywhere;
}

.profile-product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 15rem), 1fr));
  gap: var(--space-4);
}

.profile-product-card {
  display: grid;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background: var(--color-surface-strong);
  box-shadow: 0 14px 32px rgba(18, 18, 18, 0.07);
}

.profile-product-card__image {
  display: grid;
  place-items: center;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: #e8ece7;
}

.profile-product-card__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-product-card__placeholder {
  display: grid;
  place-items: center;
  width: 4rem;
  height: 4rem;
  border-radius: 0.5rem;
  background: rgba(17, 17, 17, 0.08);
  color: var(--color-text-muted);
  font-size: 1.35rem;
  font-weight: 800;
  text-transform: uppercase;
}

.profile-product-card__body,
.profile-product-card__heading {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
}

.profile-product-card__body {
  padding: var(--space-4);
}

.profile-product-card__heading h3 {
  color: var(--color-text);
  font-family: var(--font-body);
  font-size: 1.05rem;
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1.25;
}

.profile-product-card__heading p {
  color: var(--color-text);
  font-weight: 800;
}

.profile-product-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.profile-product-card__link {
  width: 100%;
}

.reviews-list {
  display: grid;
  gap: var(--space-4);
}

.review-item {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.68);
}

.review-item__header {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.review-item h3 {
  color: var(--color-text);
  font-family: var(--font-body);
  font-size: 1rem;
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1.3;
}

.review-item__text {
  color: var(--color-text);
  line-height: 1.65;
}

.profile-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.pagination-button {
  min-width: var(--tap-target-size);
  min-height: var(--tap-target-size);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background: var(--color-surface-strong);
  color: var(--color-text);
  font-weight: 800;
  cursor: pointer;
}

.pagination-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.profile-pagination__page {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-weight: 800;
}

.empty-state {
  display: grid;
  justify-items: start;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.62);
}

.empty-state h3 {
  color: var(--color-text);
  font-family: var(--font-body);
  font-size: 1.1rem;
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1.25;
}

@media (max-width: 640px) {
  .profile-summary,
  .review-item__header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
