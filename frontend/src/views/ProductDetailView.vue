<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import RatingSubmissionModal from '@/components/profile/RatingSubmissionModal.vue'
import StarRating from '@/components/profile/StarRating.vue'
import { useAuth } from '@/composables/useAuth'
import {
  buyProduct,
  cancelReservation,
  getProductById,
  reserveProduct,
  resolveProductImageUrl,
} from '@/services/product.service'
import {
  createUserRating,
  resolveUserProfile,
} from '@/services/user.service'
import { useToastStore } from '@/stores/toast'
import { useWalletStore } from '@/stores/wallet'
import {
  getConditionBadgeClass,
  getProductCondition,
} from '@/utils/product-condition'

const { t } = useI18n()
const route = useRoute()
const { token, user } = useAuth()
const toastStore = useToastStore()
const walletStore = useWalletStore()

const stateLabelByKey = {
  available: 'Available',
  reserved: 'Reserved',
  sold: 'Sold',
}

const product = ref(null)
const sellerProfile = ref(null)
const selectedImageIndex = ref(0)
const failedImageUrls = ref({})
const isLoading = ref(true)
const isUpdating = ref(false)
const isBuyDialogOpen = ref(false)
const isRatingDialogOpen = ref(false)
const isSubmittingRating = ref(false)
const loadError = ref('')
const actionError = ref('')
const ratingError = ref('')
const completedPurchase = ref(null)

const currencyFormatter = new Intl.NumberFormat('en-US', {
  currency: 'USD',
  style: 'currency',
})

const productId = computed(() => route.params.id)
const productImages = computed(() =>
  (product.value?.images || [])
    .map((image) => resolveProductImageUrl(image))
    .filter(Boolean)
    .filter((image) => !failedImageUrls.value[image]),
)
const selectedImage = computed(() => {
  const fallbackIndex = Math.min(selectedImageIndex.value, productImages.value.length - 1)

  return productImages.value[fallbackIndex] || ''
})
const sellerEmail = computed(() => product.value?.seller_id || '')
const normalizeSellerIdentifier = (value) => String(value ?? '').trim()
const isNumericSellerIdentifier = (value) => /^\d+$/.test(normalizeSellerIdentifier(value))
const sellerProfileLookupId = computed(() => {
  const sellerUserId = normalizeSellerIdentifier(product.value?.seller_user_id)

  if (sellerUserId) {
    return sellerUserId
  }

  return normalizeSellerIdentifier(sellerEmail.value)
})
const sellerProfileId = computed(() => {
  const sellerUserId = normalizeSellerIdentifier(product.value?.seller_user_id)

  if (isNumericSellerIdentifier(sellerUserId)) {
    return sellerUserId
  }

  if (sellerProfile.value?.id !== null && sellerProfile.value?.id !== undefined) {
    return String(sellerProfile.value.id)
  }

  const sellerId = normalizeSellerIdentifier(sellerEmail.value)

  return isNumericSellerIdentifier(sellerId) ? sellerId : ''
})
const sellerProfileHref = computed(() => {
  const identifier = sellerProfileId.value || sellerProfileLookupId.value

  if (!identifier) {
    return ''
  }

  return `#/users/${encodeURIComponent(identifier)}/profile`
})
const sellerInitial = computed(() => sellerEmail.value.trim().charAt(0).toUpperCase() || 'S')
const normalizeProductState = (value) => {
  const key = String(value || 'Available').trim().toLowerCase()

  return stateLabelByKey[key] || String(value || 'Available').trim() || 'Available'
}
const decodeTokenSubject = (jwt) => {
  const [, payload] = String(jwt || '').split('.')

  if (!payload || typeof window === 'undefined' || typeof window.atob !== 'function') {
    return ''
  }

  try {
    const normalizedPayload = payload.replace(/-/g, '+').replace(/_/g, '/')
    const paddedPayload = normalizedPayload.padEnd(
      Math.ceil(normalizedPayload.length / 4) * 4,
      '=',
    )
    const parsedPayload = JSON.parse(window.atob(paddedPayload))
    return parsedPayload.sub || parsedPayload.email || parsedPayload.user || ''
  } catch {
    return ''
  }
}
const currentUserId = computed(() => user.value?.email || decodeTokenSubject(token.value))
const isSeller = computed(() => Boolean(sellerEmail.value && currentUserId.value === sellerEmail.value))
const hasCheckoutProduct = computed(() => Boolean(product.value?.transaction_product_id))
const productState = computed(() => normalizeProductState(product.value?.state))
const normalizedState = computed(() => productState.value.toLowerCase())
const canReserve = computed(() =>
  Boolean(product.value && hasCheckoutProduct.value && !isSeller.value && normalizedState.value === 'available'),
)
const canBuy = computed(() =>
  Boolean(
    product.value &&
      hasCheckoutProduct.value &&
      !isSeller.value &&
      normalizedState.value === 'reserved' &&
      product.value.reserved_by === currentUserId.value,
  ),
)
const canCancelReservation = computed(() =>
  Boolean(
    product.value &&
      hasCheckoutProduct.value &&
      !isSeller.value &&
      normalizedState.value === 'reserved' &&
      product.value.reserved_by === currentUserId.value,
  ),
)
const inactiveActionLabel = computed(() => {
  if (!hasCheckoutProduct.value && !isSeller.value && normalizedState.value !== 'sold') {
    return t('detail.checkoutUnavailable')
  }

  return normalizedState.value === 'sold' ? t('detail.sold') : t('detail.unavailable')
})
const formattedProductPrice = computed(() => currencyFormatter.format(product.value?.price || 0))
const productCondition = computed(() => getProductCondition(product.value))
const productConditionClass = computed(() => getConditionBadgeClass(productCondition.value))
const sellerRating = computed(() =>
  product.value?.seller_avg_rating ?? sellerProfile.value?.avg_rating ?? null
)
const sellerDisplayName = computed(() =>
  sellerProfile.value?.username || sellerEmail.value || t('detail.unknownSeller')
)
const editRoute = computed(() => ({
  name: 'product-edit',
  params: {
    id: product.value?.id || productId.value,
  },
}))

const resolveSellerProfileForProduct = async () => {
  const identifier = sellerProfileLookupId.value

  sellerProfile.value = null

  if (!identifier) {
    return
  }

  try {
    sellerProfile.value = await resolveUserProfile(identifier)
  } catch {
    sellerProfile.value = null
  }
}

const loadProduct = async () => {
  isLoading.value = true
  loadError.value = ''
  actionError.value = ''
  selectedImageIndex.value = 0
  failedImageUrls.value = {}

  try {
    product.value = await getProductById(productId.value)
    void resolveSellerProfileForProduct()
  } catch {
    product.value = null
    loadError.value = t('detail.errorLoad')
  } finally {
    isLoading.value = false
  }
}

const handleReserve = async () => {
  if (!product.value) {
    return
  }

  isUpdating.value = true
  actionError.value = ''

  try {
    const result = await reserveProduct(product.value)
    product.value = {
      ...product.value,
      state: normalizeProductState(result?.state || 'Reserved'),
      reserved_by: result?.reserved_by ?? currentUserId.value ?? product.value.reserved_by ?? null,
    }
    toastStore.success(t('detail.reserved'))
  } catch (error) {
    actionError.value =
      error?.response?.data?.detail || t('detail.errorReserve')
  } finally {
    isUpdating.value = false
  }
}

const handleCancelReservation = async () => {
  if (!product.value) {
    return
  }

  isUpdating.value = true
  actionError.value = ''

  try {
    const result = await cancelReservation(product.value)
    product.value = {
      ...product.value,
      state: normalizeProductState(result?.state || 'Available'),
      reserved_by: null,
    }
    isBuyDialogOpen.value = false
    toastStore.success(t('detail.reservationCancelled'))
  } catch (error) {
    actionError.value =
      error?.response?.data?.detail || t('detail.errorCancelReservation')
  } finally {
    isUpdating.value = false
  }
}

const openBuyDialog = () => {
  if (!product.value) {
    return
  }

  actionError.value = ''
  isBuyDialogOpen.value = true
}

const closeBuyDialog = () => {
  if (isUpdating.value) {
    return
  }

  isBuyDialogOpen.value = false
}

const confirmBuy = async () => {
  if (!product.value) {
    return
  }

  isUpdating.value = true
  actionError.value = ''

  try {
    const transaction = await buyProduct(product.value)
    await walletStore.fetchBalance().catch(() => {})
    product.value = {
      ...product.value,
      state: 'Sold',
    }
    completedPurchase.value = transaction
    isBuyDialogOpen.value = false
    isRatingDialogOpen.value = true
    toastStore.success(t('detail.purchaseCompleted'))
  } catch (error) {
    actionError.value =
      error?.response?.data?.detail || t('detail.errorBuy')
  } finally {
    isUpdating.value = false
  }
}

const closeRatingDialog = () => {
  if (isSubmittingRating.value) {
    return
  }

  isRatingDialogOpen.value = false
  ratingError.value = ''
}

const submitRating = async ({ reviewText, stars }) => {
  const toUserId = Number(sellerProfileId.value)
  const transactionId = Number(completedPurchase.value?.id)

  if (!Number.isFinite(toUserId) || !Number.isFinite(transactionId)) {
    ratingError.value = t('detail.errorRatingMissingSeller')
    return
  }

  isSubmittingRating.value = true
  ratingError.value = ''

  try {
    await createUserRating({
      reviewText,
      stars,
      toUserId,
      transactionId,
    })
    isRatingDialogOpen.value = false
    toastStore.success(t('detail.ratingSubmitted'))
    await resolveSellerProfileForProduct()
  } catch (error) {
    ratingError.value =
      error?.response?.data?.detail || t('detail.errorRating')
  } finally {
    isSubmittingRating.value = false
  }
}

const selectImage = (index) => {
  selectedImageIndex.value = index
}

const handleImageError = (image) => {
  if (!image) {
    return
  }

  failedImageUrls.value = {
    ...failedImageUrls.value,
    [image]: true,
  }
}

loadProduct()
</script>

<template>
  <section class="page-shell detail-shell">
    <BaseButton to="/products" variant="ghost">
      {{ $t('detail.back') }}
    </BaseButton>

    <p v-if="isLoading" class="status-message">
      {{ $t('detail.loading') }}
    </p>

    <p v-else-if="loadError" class="status-message error">
      {{ loadError }}
    </p>

    <BaseCard v-else-if="product" class="detail-card">
      <div class="detail-layout">
        <div class="gallery-stack">
          <div class="gallery">
            <img
              v-if="selectedImage"
              :alt="`${product.title || $t('detail.untitled')} image ${selectedImageIndex + 1}`"
              :src="selectedImage"
              @error="handleImageError(selectedImage)"
            />
            <div v-else class="gallery-placeholder">
              {{ (product.title || '?').trim().charAt(0) || '?' }}
            </div>
          </div>

          <div v-if="productImages.length > 1" class="gallery-thumbnails">
            <button
              v-for="(image, index) in productImages"
              :key="image"
              class="gallery-thumbnail"
              :class="{ 'is-selected': selectedImageIndex === index }"
              type="button"
              :aria-label="$t('detail.showImageAria', { n: index + 1 })"
              @click="selectImage(index)"
            >
              <img
                :alt="`${product.title || $t('detail.untitled')} thumbnail ${index + 1}`"
                :src="image"
                @error="handleImageError(image)"
              />
            </button>
          </div>
        </div>

        <div class="detail-copy">
          <div class="detail-heading">
            <h1>{{ product.title || $t('detail.untitled') }}</h1>
            <p class="detail-price">
              {{ formattedProductPrice }}
            </p>
          </div>

          <p class="muted">
            {{ product.description }}
          </p>

          <dl class="detail-meta">
            <div>
              <dt>{{ $t('detail.category') }}</dt>
              <dd>{{ product.category || $t('detail.unspecified') }}</dd>
            </div>
            <div>
              <dt>{{ $t('detail.condition') }}</dt>
              <dd>
                <span class="condition-badge" :class="productConditionClass">
                  {{ productCondition }}
                </span>
              </dd>
            </div>
            <div>
              <dt>{{ $t('detail.state') }}</dt>
              <dd>{{ $t(`products.states.${normalizedState}`) }}</dd>
            </div>
            <div>
              <dt>{{ $t('detail.listed') }}</dt>
              <dd>{{ product.created_at ? new Date(product.created_at).toLocaleDateString() : $t('detail.unknownDate') }}</dd>
            </div>
          </dl>

          <component
            :is="sellerProfileHref ? 'a' : 'section'"
            class="seller-panel"
            :class="{ 'seller-panel--link': sellerProfileHref }"
            :href="sellerProfileHref || undefined"
            :aria-label="$t('detail.seller')"
          >
            <div class="seller-avatar" aria-hidden="true">
              {{ sellerInitial }}
            </div>
            <div class="seller-copy">
              <p class="seller-title">
                {{ sellerDisplayName }}
              </p>
              <StarRating
                :value="sellerRating"
                size="sm"
                :empty-label="$t('rating.noRatings')"
              />
              <p class="muted">
                {{ isSeller ? $t('detail.youAreSeller') : $t('detail.marketplaceSeller') }}
              </p>
            </div>
          </component>

          <div class="detail-actions">
            <BaseButton v-if="isSeller" :to="editRoute" variant="secondary">
              {{ $t('detail.editListing') }}
            </BaseButton>
            <template v-else>
              <BaseButton
                v-if="canReserve"
                :disabled="isUpdating"
                type="button"
                @click="handleReserve"
              >
                {{ $t('detail.reserve') }}
              </BaseButton>
              <BaseButton
                v-if="canBuy"
                :disabled="isUpdating"
                type="button"
                @click="openBuyDialog"
              >
                {{ $t('detail.buy') }}
              </BaseButton>
              <BaseButton
                v-if="canCancelReservation"
                :disabled="isUpdating"
                type="button"
                variant="secondary"
                @click="handleCancelReservation"
              >
                {{ $t('detail.cancelReservation') }}
              </BaseButton>
              <BaseButton
                v-if="!canReserve && !canBuy && !canCancelReservation"
                disabled
                type="button"
                variant="secondary"
              >
                {{ inactiveActionLabel }}
              </BaseButton>
            </template>
          </div>

          <p v-if="actionError" class="status-message error">
            {{ actionError }}
          </p>
        </div>
      </div>
    </BaseCard>

    <div
      v-if="isBuyDialogOpen"
      class="dialog-backdrop"
      @click.self="closeBuyDialog"
    >
      <section
        class="confirmation-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="buy-confirmation-title"
        aria-describedby="buy-confirmation-description"
      >
        <div class="dialog-copy">
          <p class="dialog-eyebrow">
            {{ $t('detail.dialogEyebrow') }}
          </p>
          <h2 id="buy-confirmation-title">
            {{ $t('detail.dialogTitle') }}
          </h2>
          <p id="buy-confirmation-description" class="muted">
            {{ $t('detail.dialogDesc', { price: formattedProductPrice }) }}
          </p>
        </div>

        <div class="wallet-deduction" :aria-label="$t('detail.walletDeduction')">
          <span>{{ $t('detail.walletDeduction') }}</span>
          <strong>{{ formattedProductPrice }}</strong>
        </div>

        <p v-if="actionError" class="status-message error">
          {{ actionError }}
        </p>

        <div class="dialog-actions">
          <BaseButton
            :disabled="isUpdating"
            type="button"
            variant="secondary"
            @click="closeBuyDialog"
          >
            {{ $t('detail.cancel') }}
          </BaseButton>
          <BaseButton
            :disabled="isUpdating"
            type="button"
            @click="confirmBuy"
          >
            {{ $t('detail.confirmPurchase') }}
          </BaseButton>
        </div>
      </section>
    </div>

    <RatingSubmissionModal
      v-if="isRatingDialogOpen"
      :error="ratingError"
      :is-submitting="isSubmittingRating"
      :seller-name="sellerDisplayName"
      @close="closeRatingDialog"
      @submit="submitRating"
    />
  </section>
</template>

<style scoped>
.detail-shell {
  align-items: start;
}

.detail-shell > :deep(.base-button) {
  justify-self: start;
}

.detail-card {
  width: 100%;
}

.detail-layout {
  display: grid;
  gap: var(--space-6);
  min-width: 0;
}

.gallery-stack {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
}

.gallery {
  display: grid;
  place-items: center;
  min-width: 0;
  overflow: hidden;
  border-radius: 0.5rem;
  background: #e8ece7;
  aspect-ratio: 4 / 3;
}

.gallery img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.gallery-thumbnails {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(4.5rem, 1fr));
  gap: var(--space-2);
}

.gallery-thumbnail {
  width: 100%;
  aspect-ratio: 1;
  padding: 0;
  overflow: hidden;
  border: 2px solid transparent;
  border-radius: 0.5rem;
  background: var(--color-surface-muted);
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    transform 0.2s ease;
}

.gallery-thumbnail:hover,
.gallery-thumbnail.is-selected {
  border-color: var(--color-primary);
  transform: translateY(-1px);
}

.gallery-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.gallery-placeholder {
  display: grid;
  place-items: center;
  width: 5rem;
  height: 5rem;
  border-radius: 0.5rem;
  background: rgba(17, 17, 17, 0.08);
  color: var(--color-text-muted);
  font-size: 1.6rem;
  font-weight: 800;
  text-transform: uppercase;
}

.detail-copy,
.detail-heading {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}

.detail-heading h1 {
  font-size: clamp(2.4rem, 6vw, 4.8rem);
  line-height: 0.92;
  letter-spacing: 0;
}

.detail-price {
  font-size: 1.4rem;
  font-weight: 800;
}

.detail-meta {
  display: grid;
  gap: var(--space-3);
  margin: 0;
}

.detail-meta div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 0.85rem 0;
  border-bottom: 1px solid rgba(17, 17, 17, 0.08);
}

.detail-meta dt,
.detail-meta dd {
  margin: 0;
}

.detail-meta dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.detail-meta dd {
  text-align: right;
  font-weight: 800;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: var(--space-4);
  background: rgba(17, 17, 17, 0.42);
}

.confirmation-dialog {
  display: grid;
  width: min(100%, 28rem);
  gap: var(--space-5);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background: var(--color-surface-strong);
  box-shadow: var(--shadow-lg);
}

.dialog-copy {
  display: grid;
  gap: var(--space-3);
}

.dialog-eyebrow {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: 800;
  text-transform: uppercase;
}

.confirmation-dialog h2 {
  font-size: 2rem;
  line-height: 1;
  letter-spacing: 0;
}

.wallet-deduction {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 0.5rem;
  background: var(--color-surface-muted);
}

.wallet-deduction span {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.wallet-deduction strong {
  font-size: 1.3rem;
  overflow-wrap: anywhere;
}

.dialog-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-3);
}

.seller-panel {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.68);
}

.seller-panel--link {
  color: inherit;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.seller-panel--link:hover {
  border-color: rgba(17, 17, 17, 0.22);
  box-shadow: 0 16px 34px rgba(17, 17, 17, 0.08);
  transform: translateY(-1px);
}

.seller-avatar {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 3.25rem;
  aspect-ratio: 1;
  border-radius: 0.5rem;
  background: #1a1a1a;
  color: #f7f6f2;
  font-weight: 800;
}

.seller-copy {
  display: grid;
  gap: 0.2rem;
  min-width: 0;
}

.seller-title {
  font-weight: 800;
  overflow-wrap: anywhere;
}

@media (min-width: 768px) {
  .detail-layout {
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
    align-items: start;
  }
}
</style>
