<script setup>
import { computed, reactive, ref } from 'vue'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import { useDebouncedWatch } from '@/composables/useDebouncedWatch'
import * as productService from '@/services/product.service'

const FILTER_DEBOUNCE_MS = 300
const PRODUCTS_PER_PAGE = 8
const SKELETON_PRODUCT_COUNT = 4

const stateOptions = ['Available', 'Reserved', 'Sold']
const stateLabelByKey = {
  available: 'Available',
  reserved: 'Reserved',
  sold: 'Sold',
}
const conditionOptions = ['New', 'Like New', 'Good', 'Fair', 'Poor']
const categoryFallbackOptions = ['Books', 'Collectibles', 'Electronics', 'Furniture', 'Home']

const initialFilters = () => ({
  category: '',
  condition: '',
  maxPrice: '',
  minPrice: '',
  states: [],
})

const productFilters = reactive(initialFilters())
const products = ref([])
const failedProductImages = ref({})
const productListError = ref('')
const isLoadingProducts = ref(false)
const currentPage = ref(1)
let activeRequestId = 0

const createProductRoute = {
  name: 'product-create',
  params: {
    id: 'new',
  },
}

const currencyFormatter = new Intl.NumberFormat('en-US', {
  currency: 'USD',
  style: 'currency',
})

const normalizeFilterValue = (value) => String(value ?? '').trim().toLowerCase()
const normalizeProductState = (value) => {
  const key = normalizeFilterValue(value || 'Available')

  return stateLabelByKey[key] || String(value || 'Available').trim() || 'Available'
}
const buildOptionList = (values, fallbackValues = []) => {
  const options = new Map()

  ;[...values, ...fallbackValues].forEach((value) => {
    const label = String(value ?? '').trim()

    if (!label) {
      return
    }

    const key = normalizeFilterValue(label)

    if (!options.has(key)) {
      options.set(key, label)
    }
  })

  return Array.from(options.values()).sort((first, second) => first.localeCompare(second))
}

const getProductState = (product) => normalizeProductState(product.state)
const getProductInitial = (product) => (product.title || product.category || '?').trim().charAt(0) || '?'
const getProductKey = (product, index) => product.id ?? `${product.title}-${index}`
const getProductDetailRoute = (product) => ({
  name: 'product-detail',
  params: {
    id: product.id,
  },
})

const visibleProducts = computed(() => {
  if (productFilters.states.length === 0) {
    return products.value
  }

  return products.value.filter((product) => productFilters.states.includes(getProductState(product)))
})

const hasProducts = computed(() => visibleProducts.value.length > 0)
const hasActiveFilters = computed(() =>
  Object.values(productFilters).some((value) =>
    Array.isArray(value) ? value.length > 0 : String(value).trim() !== '',
  ),
)
const activeFilterCount = computed(() =>
  Object.values(productFilters).reduce((count, value) => {
    if (Array.isArray(value)) {
      return count + value.length
    }

    return count + (String(value).trim() ? 1 : 0)
  }, 0),
)
const categoryOptions = computed(() =>
  buildOptionList(
    products.value.map((product) => product.category),
    [...categoryFallbackOptions, productFilters.category],
  ),
)
const totalPages = computed(() =>
  Math.max(1, Math.ceil(visibleProducts.value.length / PRODUCTS_PER_PAGE)),
)
const pageStartIndex = computed(() => (currentPage.value - 1) * PRODUCTS_PER_PAGE)
const pageEndIndex = computed(() =>
  Math.min(pageStartIndex.value + PRODUCTS_PER_PAGE, visibleProducts.value.length),
)
const paginatedProducts = computed(() =>
  visibleProducts.value.slice(pageStartIndex.value, pageEndIndex.value),
)
const pageNumbers = computed(() =>
  Array.from({ length: totalPages.value }, (_, index) => index + 1),
)
const productsLabel = computed(() =>
  `${visibleProducts.value.length} ${visibleProducts.value.length === 1 ? 'listing' : 'listings'}`,
)
const paginationSummary = computed(() => {
  if (!hasProducts.value) {
    return productsLabel.value
  }

  if (hasActiveFilters.value) {
    return `Showing ${pageStartIndex.value + 1}-${pageEndIndex.value} of ${visibleProducts.value.length} matching ${visibleProducts.value.length === 1 ? 'listing' : 'listings'}`
  }

  return `Showing ${pageStartIndex.value + 1}-${pageEndIndex.value} of ${visibleProducts.value.length}`
})
const emptyStateTitle = computed(() => (hasActiveFilters.value ? 'No products found' : 'No products yet'))
const emptyStateDescription = computed(() =>
  hasActiveFilters.value
    ? 'Try changing or clearing the current filters.'
    : 'Published products will appear here.',
)
const filterDropdownLabel = computed(() =>
  activeFilterCount.value > 0 ? `Filters (${activeFilterCount.value})` : 'Filters',
)
const primaryActionCard = {
  title: 'Create a new listing',
  description: 'Add the basic details and publish your item in one short form.',
  buttonLabel: 'New item',
  toneClass: 'action-card',
}

const resolveProductListError = (error) =>
  error?.response?.data?.detail || 'We could not load products. Please try again.'

const getProductImage = (product) => {
  return (product.images || [])
    .map((image) => productService.resolveProductImageUrl(image))
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

const getStateClass = (product) => {
  const state = getProductState(product).toLowerCase()

  return {
    'state-label--available': state === 'available',
    'state-label--reserved': state === 'reserved',
    'state-label--sold': state === 'sold',
  }
}

const goToPage = (page) => {
  currentPage.value = Math.min(Math.max(page, 1), totalPages.value)
}

const buildProductQueryFilters = () => ({
  category: productFilters.category,
  condition: productFilters.condition,
  maxPrice: productFilters.maxPrice,
  minPrice: productFilters.minPrice,
  state: '',
})

const fetchProducts = async () => {
  const requestId = ++activeRequestId

  isLoadingProducts.value = true
  productListError.value = ''

  try {
    const nextProducts = await productService.listProducts(buildProductQueryFilters())

    if (requestId === activeRequestId) {
      products.value = nextProducts
      currentPage.value = 1
    }
  } catch (error) {
    if (requestId === activeRequestId) {
      products.value = []
      productListError.value = resolveProductListError(error)
    }
  } finally {
    if (requestId === activeRequestId) {
      isLoadingProducts.value = false
    }
  }
}

const resetFilters = () => {
  Object.assign(productFilters, initialFilters())
  currentPage.value = 1
}

fetchProducts()

useDebouncedWatch(
  () => [
    productFilters.states.join('|'),
    productFilters.category,
    productFilters.condition,
    productFilters.minPrice,
    productFilters.maxPrice,
  ],
  () => {
    currentPage.value = 1
    fetchProducts()
  },
  {
    debounce: FILTER_DEBOUNCE_MS,
  },
)
</script>

<template>
  <section class="page-shell">
    <div class="page-hero">
      <h1>Sell without the noise.</h1>
      <p class="muted">
        Create a listing, browse the catalog, and skip the demo content.
      </p>
    </div>

    <div class="card-grid intro-grid">
      <BaseCard
        :class="['primary-action-card', primaryActionCard.toneClass]"
        :title="primaryActionCard.title"
        :description="primaryActionCard.description"
      >
        <BaseButton :to="createProductRoute" variant="secondary">
          {{ primaryActionCard.buttonLabel }}
        </BaseButton>
      </BaseCard>
    </div>

    <section class="catalog-layout" aria-label="Product catalog">
      <BaseCard
        class="catalog-card"
        title="Catalog"
        description="Listings that match your current filters."
      >
        <div class="catalog-toolbar">
          <p class="muted">
            {{ isLoadingProducts ? 'Refreshing catalog...' : paginationSummary }}
          </p>

          <details class="filter-dropdown">
            <summary class="filter-dropdown__summary">
              <span>{{ filterDropdownLabel }}</span>
              <span class="filter-dropdown__chevron" aria-hidden="true" />
            </summary>

            <form class="filter-form filter-dropdown__content" role="search" aria-label="Product filters" @submit.prevent>
              <fieldset class="filter-field filter-field--state">
                <legend class="filter-label">
                  State
                </legend>

                <div class="state-filter-options">
                  <label
                    v-for="state in stateOptions"
                    :key="state"
                    class="state-filter-option"
                    :class="{ 'is-selected': productFilters.states.includes(state) }"
                  >
                    <input
                      v-model="productFilters.states"
                      class="state-filter-option__input"
                      type="checkbox"
                      :value="state"
                    />
                    <span>{{ state }}</span>
                  </label>
                </div>
              </fieldset>

              <label class="filter-field">
                <span class="filter-label">Category</span>
                <select v-model="productFilters.category" class="filter-control" name="category">
                  <option value="">
                    Any category
                  </option>
                  <option v-for="category in categoryOptions" :key="category" :value="category">
                    {{ category }}
                  </option>
                </select>
              </label>

              <fieldset class="filter-field">
                <legend class="filter-label">
                  Price range
                </legend>

                <div class="price-range-fields">
                  <BaseInput
                    v-model="productFilters.minPrice"
                    class="filter-field"
                    label="Min"
                    min="0"
                    name="min_price"
                    placeholder="0"
                    step="0.01"
                    type="number"
                  />

                  <BaseInput
                    v-model="productFilters.maxPrice"
                    class="filter-field"
                    label="Max"
                    min="0"
                    name="max_price"
                    placeholder="500"
                    step="0.01"
                    type="number"
                  />
                </div>
              </fieldset>

              <label class="filter-field">
                <span class="filter-label">Condition</span>
                <select v-model="productFilters.condition" class="filter-control" name="condition">
                  <option value="">
                    Any condition
                  </option>
                  <option v-for="condition in conditionOptions" :key="condition" :value="condition">
                    {{ condition }}
                  </option>
                </select>
              </label>

              <BaseButton
                v-if="hasActiveFilters"
                size="sm"
                type="button"
                variant="ghost"
                @click="resetFilters"
              >
                Clear filters
              </BaseButton>
            </form>
          </details>
        </div>

        <p v-if="productListError" class="status-message error">
          {{ productListError }}
        </p>

        <ul
          v-else-if="isLoadingProducts"
          class="product-list skeleton-list"
          aria-label="Loading products"
        >
          <li
            v-for="index in SKELETON_PRODUCT_COUNT"
            :key="index"
            class="product-item product-item--skeleton"
            aria-hidden="true"
          >
            <div class="product-item__copy">
              <span class="skeleton-line skeleton-line--title" />
              <span class="skeleton-line skeleton-line--meta" />
              <span class="skeleton-line skeleton-line--description" />
            </div>

            <div class="product-item__meta">
              <span class="skeleton-line skeleton-line--price" />
              <span class="skeleton-pill" />
            </div>
          </li>
        </ul>

        <div v-else-if="hasProducts" class="catalog-results">
          <div class="product-card-grid">
            <article
              v-for="(product, index) in paginatedProducts"
              :key="getProductKey(product, index)"
              class="product-card"
            >
              <div class="product-card__image" aria-hidden="true">
                <img
                  v-if="getProductImage(product)"
                  :alt="`${product.title || 'Product'} thumbnail`"
                  :src="getProductImage(product)"
                  @error="handleProductImageError(getProductImage(product))"
                />
                <span v-else class="product-card__placeholder">
                  {{ getProductInitial(product) }}
                </span>
              </div>

              <div class="product-card__body">
                <div class="product-card__heading">
                  <h3 class="product-card__title">
                    {{ product.title || 'Untitled product' }}
                  </h3>
                  <p class="product-card__price">
                    {{ currencyFormatter.format(product.price) }}
                  </p>
                </div>

                <div class="product-card__meta">
                  <span class="state-label" :class="getStateClass(product)">
                    {{ getProductState(product) }}
                  </span>
                </div>

                <BaseButton
                  class="product-card__detail-link"
                  size="sm"
                  :to="getProductDetailRoute(product)"
                  variant="ghost"
                >
                  View details
                </BaseButton>
              </div>
            </article>
          </div>

          <nav v-if="totalPages > 1" class="pagination" aria-label="Product pages">
            <button
              class="pagination-button"
              type="button"
              :disabled="currentPage === 1"
              aria-label="Go to previous products page"
              @click="goToPage(currentPage - 1)"
            >
              Previous
            </button>

            <div class="pagination-pages">
              <button
                v-for="page in pageNumbers"
                :key="page"
                class="pagination-page"
                :class="{ 'is-current': currentPage === page }"
                type="button"
                :aria-current="currentPage === page ? 'page' : undefined"
                @click="goToPage(page)"
              >
                {{ page }}
              </button>
            </div>

            <button
              class="pagination-button"
              type="button"
              :disabled="currentPage === totalPages"
              aria-label="Go to next products page"
              @click="goToPage(currentPage + 1)"
            >
              Next
            </button>
          </nav>
        </div>

        <div v-else class="empty-state">
          <h3>{{ emptyStateTitle }}</h3>
          <p class="muted">
            {{ emptyStateDescription }}
          </p>
          <BaseButton
            v-if="hasActiveFilters"
            size="sm"
            type="button"
            variant="secondary"
            @click="resetFilters"
          >
            Clear filters
          </BaseButton>
        </div>
      </BaseCard>
    </section>
  </section>
</template>

<style scoped>
.intro-grid {
  align-items: stretch;
}

.primary-action-card,
.action-card,
.catalog-card,
.empty-card {
  min-height: 100%;
}

.primary-action-card :deep(.card-title),
.catalog-card :deep(.card-title) {
  min-width: 0;
  text-wrap: pretty;
}

.primary-action-card :deep(.base-button),
.filter-form :deep(.base-button) {
  width: 100%;
}

.action-card {
  background: linear-gradient(180deg, rgba(26, 26, 26, 0.96), rgba(42, 42, 42, 0.93));
  border-color: rgba(17, 17, 17, 0.9);
  color: #f7f6f2;
}

.action-card :deep(.card-title),
.action-card :deep(.muted) {
  color: #f7f6f2;
}

.action-card :deep(.muted) {
  font-size: 0.98rem;
  line-height: 1.55;
}

.catalog-layout {
  display: grid;
  gap: var(--space-5);
  align-items: start;
  min-width: 0;
}

.catalog-card {
  min-width: 0;
  overflow: visible;
}

.filter-form {
  display: grid;
  gap: var(--space-4);
}

.filter-dropdown {
  position: relative;
  z-index: 3;
  width: min(100%, 16rem);
  justify-self: end;
}

.filter-dropdown__summary {
  display: flex;
  min-width: 0;
  min-height: var(--tap-target-size);
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 0 1rem;
  border: 1px solid rgba(17, 17, 17, 0.12);
  border-radius: var(--radius-md);
  background: var(--color-surface-strong);
  color: var(--color-text);
  font-weight: 800;
  line-height: 1.2;
  list-style: none;
  cursor: pointer;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.75),
    0 12px 30px rgba(17, 17, 17, 0.06);
}

.filter-dropdown__summary::-webkit-details-marker {
  display: none;
}

.filter-dropdown__summary:focus-visible {
  border-color: rgba(17, 17, 17, 0.3);
  box-shadow:
    0 0 0 4px rgba(17, 17, 17, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.75),
    0 12px 30px rgba(17, 17, 17, 0.06);
}

.filter-dropdown__chevron {
  flex: 0 0 auto;
  width: 0.55rem;
  height: 0.55rem;
  margin-top: -0.25rem;
  border-right: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(45deg);
  transition:
    margin-top 0.2s ease,
    transform 0.2s ease;
}

.filter-dropdown[open] .filter-dropdown__chevron {
  margin-top: 0.25rem;
  transform: rotate(225deg);
}

.filter-dropdown__content {
  position: absolute;
  top: calc(100% + var(--space-2));
  right: 0;
  z-index: 4;
  width: min(23rem, calc(100vw - 2rem));
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(18px);
}

.filter-field {
  display: grid;
  gap: 0.55rem;
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

.filter-label {
  padding: 0;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-text);
}

.filter-control {
  width: 100%;
  min-height: var(--tap-target-size);
  border: 1px solid rgba(17, 17, 17, 0.12);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
  color: var(--color-text);
  font-size: 1rem;
  line-height: 1.5;
  padding: 0.95rem 2.55rem 0.95rem 1rem;
}

.filter-control:focus {
  outline: none;
  border-color: rgba(17, 17, 17, 0.3);
  box-shadow:
    0 0 0 4px rgba(17, 17, 17, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  background: #ffffff;
}

.state-filter-options {
  display: grid;
  gap: var(--space-2);
}

.state-filter-option {
  display: flex;
  min-width: 0;
  min-height: var(--tap-target-size);
  align-items: center;
  gap: var(--space-2);
  padding: 0.75rem 0.9rem;
  border: 1px solid rgba(17, 17, 17, 0.1);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.76);
  color: var(--color-text-muted);
  font-weight: 800;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}

.state-filter-option.is-selected {
  border-color: rgba(17, 17, 17, 0.28);
  background: var(--color-primary-soft);
  color: var(--color-text);
}

.state-filter-option__input {
  flex: 0 0 auto;
  width: 1.05rem;
  height: 1.05rem;
  margin: 0;
  accent-color: var(--color-primary);
}

.price-range-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.catalog-toolbar {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: flex-start;
}

.catalog-results {
  display: grid;
  gap: var(--space-5);
  min-width: 0;
}

.product-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 15.5rem), 1fr));
  gap: var(--space-5);
  min-width: 0;
}

.product-card {
  display: grid;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background: var(--color-surface-strong);
  box-shadow: 0 18px 42px rgba(18, 18, 18, 0.08);
}

.product-card__image {
  aspect-ratio: 4 / 3;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: #e8ece7;
}

.product-card__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-card__placeholder {
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

.product-card__body {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
  padding: var(--space-4);
}

.product-card__detail-link {
  width: 100%;
}

.product-card__heading {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.product-card__title {
  color: var(--color-text);
  font-family: var(--font-body);
  font-size: 1.05rem;
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1.25;
}

.product-card__price {
  color: var(--color-text);
  font-size: 1.1rem;
  font-weight: 800;
  line-height: 1.2;
}

.product-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.state-label {
  display: inline-flex;
  align-items: center;
  min-height: 2rem;
  max-width: 100%;
  padding: 0.35rem 0.65rem;
  border-radius: 0.5rem;
  font-size: var(--font-size-xs);
  font-weight: 800;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.state-label {
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  background: rgba(255, 255, 255, 0.78);
}

.state-label--available {
  border-color: rgba(27, 92, 69, 0.18);
  background: var(--color-success-soft);
  color: var(--color-success);
}

.state-label--reserved {
  border-color: rgba(119, 89, 32, 0.2);
  background: #f7ead1;
  color: #775920;
}

.state-label--sold {
  border-color: rgba(125, 45, 36, 0.14);
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.pagination-pages {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.pagination-button,
.pagination-page {
  min-width: var(--tap-target-size);
  min-height: var(--tap-target-size);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background: var(--color-surface-strong);
  color: var(--color-text);
  font-weight: 800;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease,
    opacity 0.2s ease;
}

.pagination-button {
  padding: 0 var(--space-4);
}

.pagination-page {
  padding: 0 var(--space-3);
}

.pagination-button:hover:not(:disabled),
.pagination-page:hover,
.pagination-page.is-current {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #f9f8f4;
}

.pagination-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.product-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-4);
}

.product-item {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  align-items: center;
  padding: 1rem 1.05rem;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 1.35rem;
  background: rgba(255, 255, 255, 0.62);
}

.product-item:last-child {
  margin-bottom: 0;
}

.product-item__copy,
.product-item__meta {
  display: grid;
  gap: 0.35rem;
  min-width: 0;
}

.product-item__title {
  font-family: var(--font-heading);
  font-size: 1.6rem;
  font-weight: 600;
  line-height: 0.95;
  overflow-wrap: anywhere;
}

.product-item__description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.product-item__meta {
  justify-items: end;
  text-align: right;
  color: var(--color-text-muted);
}

.product-item__state {
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--color-text-muted);
}

.empty-state {
  display: grid;
  justify-items: start;
  gap: var(--space-3);
  padding: 1.15rem;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 1.35rem;
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

.product-item--skeleton {
  pointer-events: none;
}

.skeleton-line,
.skeleton-pill {
  display: block;
  overflow: hidden;
  border-radius: 999px;
  background: linear-gradient(90deg, #e7e3dc 0%, #f6f4f0 50%, #e7e3dc 100%);
  background-size: 220% 100%;
  animation: skeleton-shimmer 1.3s ease-in-out infinite;
}

.skeleton-line--title {
  width: min(14rem, 76%);
  height: 1.35rem;
}

.skeleton-line--meta {
  width: min(10rem, 54%);
  height: 0.9rem;
}

.skeleton-line--description {
  width: min(22rem, 90%);
  height: 0.9rem;
}

.skeleton-line--price {
  width: 5.75rem;
  height: 1rem;
}

.skeleton-pill {
  width: 4.75rem;
  height: 1.5rem;
}

@keyframes skeleton-shimmer {
  from {
    background-position: 100% 0;
  }

  to {
    background-position: -100% 0;
  }
}

@media (min-width: 768px) {
  .intro-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .primary-action-card :deep(.card-title) {
    max-width: 11ch;
    font-size: clamp(1.85rem, 9vw, 2.2rem);
    line-height: 0.98;
  }

  .catalog-toolbar,
  .product-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .filter-dropdown {
    width: 100%;
    justify-self: stretch;
  }

  .filter-dropdown__content {
    position: static;
    width: 100%;
    margin-top: var(--space-2);
  }

  .price-range-fields {
    grid-template-columns: minmax(0, 1fr);
  }

  .product-card__meta,
  .pagination {
    align-items: stretch;
  }

  .state-label {
    justify-content: center;
  }

  .pagination,
  .pagination-pages {
    width: 100%;
  }

  .pagination-button {
    flex: 1 1 9rem;
  }

  .product-item__meta {
    justify-items: start;
    text-align: left;
  }

  .product-item__title {
    font-size: 1.35rem;
  }
}
</style>
